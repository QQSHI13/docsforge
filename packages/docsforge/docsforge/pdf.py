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
import logging
import os
import subprocess
import sys
from pathlib import Path

log = logging.getLogger(__name__)

_DEFAULT_BROWSER_PATHS = [
    "/usr/bin/thorium-browser", "/usr/bin/thorium",
    "/usr/bin/chromium-browser", "/usr/bin/chromium",
    "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
    "/usr/bin/brave-browser",
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
        asyncio.run(_render(site_path, Path(output_dir), concurrency))
    except Exception as e:
        log.error(f"PDF export failed: {e}")
        return 1
    return 0


async def _render(site_path: Path, output_path: Path, concurrency: int = 4) -> None:
    """Render HTML pages to A4 PDF using Playwright with @media print."""
    html_files = sorted(site_path.rglob("*.html"))
    if not html_files:
        log.error("No HTML files found")
        return

    output_path.mkdir(parents=True, exist_ok=True)
    total = len(html_files)

    browser_exe = _find_browser()
    launch_opts = {"args": ["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"]}
    if browser_exe:
        launch_opts["executable_path"] = browser_exe
        log.info(f"Browser: {browser_exe}")
    log.info(f"Pages: {total}  Tabs: {concurrency}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(**launch_opts)
        tabs = await asyncio.gather(*[browser.new_page() for _ in range(concurrency)])
        for tab in tabs:
            await tab.emulate_media(media="print")

        async def render_one(tab, html_file, idx):
            rel = html_file.relative_to(site_path)
            pdf_path = output_path / rel.with_suffix(".pdf")
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            url = html_file.resolve().as_uri()
            try:
                # "load" is enough — external requests are blocked, local assets
                # load instantly from the file system.
                await tab.goto(url, wait_until="networkidle")
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
                log.info(f"  [{idx}/{total}] {rel.with_suffix('')}")
            except Exception as e:
                log.warning(f"  [{idx}/{total}] FAILED {rel} — {e}")

        # Work queue: each tab picks the next file as soon as it finishes
        idx = 0
        async def worker(tab):
            nonlocal idx
            while idx < total:
                file_idx = idx
                idx += 1
                await render_one(tab, html_files[file_idx], file_idx + 1)

        await asyncio.gather(*[worker(tabs[i % concurrency]) for i in range(concurrency)])

        for tab in tabs:
            await tab.close()
        await browser.close()

    log.info(f"\nPDF export complete: {output_path.resolve()} ({total} pages)")
