"""PDF export — renders built HTML pages to PDF via Playwright.

Uses the full build output (Mermaid, KaTeX, TikZ, all rendered), opens
each page in a headless Chromium tab with @media print CSS, and exports
to A4 PDF. Multiple tabs for parallel rendering.

Requires:
    pip install playwright
    # Browser: playwright install chromium, or set PLAYWRIGHT_CHROMIUM_EXECUTABLE
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import sys
import urllib.parse
from pathlib import Path

log = logging.getLogger(__name__)

# PDF cache schema version — bump to invalidate all cached PDFs.
PDF_CACHE_VERSION = 1

_DEFAULT_BROWSER_PATHS = [
    # Linux
    "/usr/bin/thorium-browser", "/usr/bin/thorium",
    "/usr/bin/chromium-browser", "/usr/bin/chromium",
    "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
    "/usr/bin/brave-browser",
    # macOS
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    # Windows
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Chromium\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
]

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


def _find_browser() -> str | None:
    env = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
    if env and os.path.isfile(env):
        return env
    for path in _DEFAULT_BROWSER_PATHS:
        if os.path.isfile(path):
            return path
    return None


def _is_within(local: Path, base: Path) -> bool:
    """Return True if *local* resolves to a path inside *base*."""
    try:
        local.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# PDF cache — mirrors the site build's incremental cache. Stored in the same
# directory as the build cache (<project>/.docsforge/cache/pdf.json), it maps
# each output PDF to the content hash of its built HTML file. A PDF is
# re-rendered only when that HTML hash changed — exactly the pages the
# incremental build itself re-rendered — or when the cache schema / docsforge
# version changed (which can alter the renderer output).
# ---------------------------------------------------------------------------


def _read_json(path: Path) -> dict:
    """Read a JSON file, returning {} when missing or corrupted."""
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        log.warning(f"Corrupted PDF cache: {path}, rebuilding from scratch")
        return {}


def _write_json(path: Path, data: dict) -> None:
    """Write a JSON file atomically (tmp + rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    tmp.replace(path)


class PdfCache:
    """Content-hash cache for PDF exports, keyed per page like the site cache.

    Uses the built HTML file's hash — the same signal the incremental build
    uses to decide whether a page was re-rendered (unchanged pages are not
    rewritten, so their file hash is stable).
    """

    def __init__(self, project_dir: Path):
        self.path = Path(project_dir) / ".docsforge" / "cache" / "pdf.json"
        self.data = _read_json(self.path)

    def is_fresh(self, pkg_version: str | None) -> bool:
        """True when schema + docsforge versions match, so per-page hashes apply."""
        return (
            self.data.get("version") == PDF_CACHE_VERSION
            and self.data.get("pkg_version") == pkg_version
        )

    def should_render(self, pdf_rel: str, html_hash: str) -> bool:
        """True when the page must be (re)rendered — no cached hash or changed."""
        return self.data.get("files", {}).get(pdf_rel) != html_hash

    def save(self, pkg_version: str | None, files: dict[str, str]) -> None:
        """Persist the per-page hashes atomically."""
        self.data = {
            "version": PDF_CACHE_VERSION,
            "pkg_version": pkg_version,
            "files": files,
        }
        _write_json(self.path, self.data)


def build_pdf(docs_dir: str, output_dir: str = "pdf", **kwargs) -> int:
    """Build the site and export to PDF via Playwright."""
    if not HAS_PLAYWRIGHT:
        log.error("Playwright required. Install: pip install playwright")
        return 1

    project_dir = Path(docs_dir).parent if Path(docs_dir).name == "docs" else Path(docs_dir)

    config_path = project_dir / "docsforge.yml"
    site_dir = "site"
    if config_path.exists():
        try:
            import yaml
            cfg = yaml.safe_load(config_path.read_text()) or {}
            site_dir = cfg.get("site_dir", "site")
        except Exception:
            pass
    site_path = project_dir / site_dir

    if not site_path.is_dir():
        log.error(f"Site directory not found: {site_path}. Run 'docsforge build' first.")
        return 1

    log.info("Rendering PDFs via Playwright...")
    try:
        concurrency = kwargs.get("concurrency", 4)
        cache = PdfCache(project_dir)
        asyncio.run(_render(site_path, Path(output_dir), concurrency, cache))
    except Exception as e:
        log.error(f"PDF export failed: {e}")
        return 1
    return 0


async def _render(site_path: Path, output_path: Path, concurrency: int = 4, cache: PdfCache | None = None) -> None:
    """Render HTML pages to A4 PDF using Playwright with @media print.

    Incremental like the site build: a page is re-rendered only when its
    built HTML changed (or was never exported), and unchanged pages are
    skipped. Per-page hashes are persisted by *cache*.
    """
    from docsforge.cache import FileHasher

    html_files = sorted(site_path.rglob("*.html"))
    if not html_files:
        log.error("No HTML files found")
        return

    import docsforge
    pkg_version = getattr(docsforge, "__version__", None)

    # Global invalidation (schema/docsforge version) forces a full re-render;
    # otherwise compare each page's built HTML hash against the cache.
    fresh = cache is not None and cache.is_fresh(pkg_version)

    output_path.mkdir(parents=True, exist_ok=True)
    total = len(html_files)

    # Orphan cleanup: remove PDFs whose source page no longer exists.
    keep: set[str] = set()
    for html_file in html_files:
        rel = html_file.relative_to(site_path).as_posix()
        keep.add(rel[: -len(".html")] + ".pdf")
    for pdf_file in output_path.rglob("*.pdf"):
        rel = pdf_file.relative_to(output_path).as_posix()
        if rel not in keep:
            log.info(f"  Removing orphan PDF: {rel}")
            pdf_file.unlink(missing_ok=True)

    # Build the work list: only stale pages. Skip hashing entirely on a full
    # re-render (everything is stale anyway).
    todo: list[tuple[Path, str]] = []
    for html_file in html_files:
        rel = html_file.relative_to(site_path).as_posix()
        pdf_rel = rel[: -len(".html")] + ".pdf"
        if fresh and not cache.should_render(pdf_rel, FileHasher.hash_file(html_file)):
            continue
        todo.append((html_file, pdf_rel))

    if not todo:
        log.info(f"Pages: {total} ({total} up to date, 0 to render)")
        if cache is not None:
            files = {k: v for k, v in cache.data.get("files", {}).items() if k in keep}
            cache.save(pkg_version, files)
    else:
        if len(todo) < total:
            log.info(f"Pages: {total} ({total - len(todo)} up to date, {len(todo)} to render)")
        else:
            log.info(f"Pages: {total}")

        browser_exe = _find_browser()
        launch_opts = {"args": ["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage", "--allow-file-access-from-files"]}
        if browser_exe:
            launch_opts["executable_path"] = browser_exe
            log.info(f"Browser: {browser_exe}")
        log.info(f"Tabs: {concurrency}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(**launch_opts)
            tabs = []

            async def _route(route):
                try:
                    url = route.request.url
                    parsed = urllib.parse.urlparse(url)
                    if parsed.scheme == "file":
                        return await route.continue_()
                    if parsed.scheme in ("http", "https"):
                        if ".." in parsed.path:
                            return await route.abort()
                        rel = parsed.path.lstrip("/")
                        local = (site_path / rel).resolve()
                        if local.exists() and _is_within(local, site_path):
                            return await route.fulfill(path=str(local))
                except Exception:
                    log.debug("Route handling failed", exc_info=True)
                await route.abort()

            async def render_one(tab, html_file, pdf_rel, idx):
                pdf_path = output_path / pdf_rel
                pdf_path.parent.mkdir(parents=True, exist_ok=True)
                url = html_file.resolve().as_uri()
                try:
                    # "load" is enough — external requests are blocked, local assets
                    # load instantly from the file system.
                    await tab.goto(url, wait_until="networkidle")
                    # Force Mermaid to render (doesn't auto-init from file://)
                    try:
                        await tab.evaluate("""() => {
                            const els = document.querySelectorAll('.mermaid');
                            if (els.length > 0 && typeof mermaid !== 'undefined') {
                                mermaid.run({ nodes: Array.from(els) }).catch(() => {});
                            }
                        }""")
                        await tab.wait_for_function(
                            "() => document.querySelectorAll('.mermaid').length === 0",
                        )
                    except Exception:
                        log.debug("Mermaid rendering failed", exc_info=True)
                    # Expand tooltips for PDF (show hover content inline)
                    await tab.evaluate("""() => {
                        document.querySelectorAll("[data-md-tooltip], [title]").forEach(el => {
                            const tip = el.getAttribute("data-md-tooltip") || el.getAttribute("title") || "";
                            if (tip) {
                                const s = document.createElement("span");
                                s.textContent = " (" + tip + ")";
                                s.style.cssText = "display:inline;font-size:inherit;color:inherit;";
                                el.appendChild(s);
                                el.removeAttribute("title");
                            }
                        });
                        document.querySelectorAll('.md-tooltip__content, [class*="tooltip"]').forEach(el => {
                            el.style.cssText = "display:inline !important;visibility:visible !important;position:static !important;";
                        });
                    }""")
                    await tab.pdf(
                        path=str(pdf_path), format="A4", print_background=True,
                        margin={"top": "15mm", "bottom": "15mm", "left": "15mm", "right": "15mm"},
                    )
                    log.info(f"  [{idx}/{len(todo)}] {Path(pdf_rel).with_suffix('')}")
                    return True
                except Exception as e:
                    log.warning(f"  [{idx}/{len(todo)}] FAILED {pdf_rel} — {e}")
                    log.debug(f"PDF render failed for {pdf_rel}", exc_info=True)
                    return False

            # Work queue: each tab picks the next file as soon as it finishes
            idx = 0
            rendered_ok: list[str] = []
            async def worker(tab):
                nonlocal idx
                while idx < len(todo):
                    file_idx = idx
                    idx += 1
                    html_file, pdf_rel = todo[file_idx]
                    if await render_one(tab, html_file, pdf_rel, file_idx + 1):
                        rendered_ok.append(pdf_rel)

            try:
                tabs = await asyncio.gather(*[browser.new_page() for _ in range(concurrency)])

                for tab in tabs:
                    await tab.emulate_media(media="print")
                    await tab.route("**/*", _route)

                await asyncio.gather(*[worker(tabs[i % concurrency]) for i in range(concurrency)])
            finally:
                for tab in tabs:
                    await tab.close()
                await browser.close()

        # Persist hashes only for pages that rendered successfully; pages
        # skipped as up-to-date keep their old entries from the previous cache.
        if cache is not None:
            files = {k: v for k, v in cache.data.get("files", {}).items() if k in keep}
            for pdf_rel in rendered_ok:
                html_file = site_path / (pdf_rel[: -len(".pdf")] + ".html")
                files[pdf_rel] = FileHasher.hash_file(html_file)
            cache.save(pkg_version, files)

    log.info(f"\nPDF export complete: {output_path.resolve()} ({total} pages)")
