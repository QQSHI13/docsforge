"""PDF export — renders the fully built site to clean, print-ready PDF.

During `docsforge build --pdf`, this:
1. Runs the full build (Mermaid, KaTeX, TikZ, all plugins)
2. Renders each page using Playwright with @media print CSS
   — Material theme hides nav bars, tabs, footers, collapsibles,
     search, and other UI chrome automatically in print mode.
3. Outputs A4 PDFs with proper margins and page breaks.

Requires:
    pip install playwright
    # Then either: playwright install chromium
    # Or set PLAYWRIGHT_CHROMIUM_EXECUTABLE to your browser path
    # (e.g. /usr/bin/thorium-browser, /usr/bin/chromium-browser)
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

log = logging.getLogger(__name__)

# Common system browser paths checked when Playwright's bundled browser
# is not available and PLAYWRIGHT_CHROMIUM_EXECUTABLE is not set.
_DEFAULT_BROWSER_PATHS = [
    "/usr/bin/thorium-browser",
    "/usr/bin/thorium",
    "/usr/bin/chromium-browser",
    "/usr/bin/chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/brave-browser",
]

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


def _find_browser() -> str | None:
    """Find a Chromium-based browser executable."""
    env = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
    if env and os.path.isfile(env):
        return env
    for path in _DEFAULT_BROWSER_PATHS:
        if os.path.isfile(path):
            return path
    return None


def build_pdf(docs_dir: str, output_dir: str = "pdf", browser_path: str | None = None, *, skip_build: bool = False) -> int:
    """Build the site and export as print-ready PDF.

    When called from `docsforge build --pdf`, the build already ran —
    pass skip_build=True to avoid rebuilding.
    """
    if not HAS_PLAYWRIGHT:
        log.error("Playwright required. Install: pip install playwright && playwright install chromium")
        return 1

    project_dir = Path(docs_dir).parent if Path(docs_dir).name == "docs" else Path(docs_dir)

    # Find site_dir from config
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

    # Step 1: Build site (skip if already built by CLI)
    if not skip_build:
        log.info("Building site (full pipeline)...")
        r = subprocess.run([sys.executable, "-m", "docsforge", "build"], cwd=str(project_dir))
        if r.returncode != 0:
            return 1
    else:
        log.info(f"Using existing build at {site_path}")

    if not site_path.is_dir():
        log.error(f"Site directory not found: {site_path}. Run 'docsforge build' first.")
        return 1

    # Step 2: PDF render with print CSS
    log.info("Rendering PDFs (print mode)...")
    import asyncio
    try:
        asyncio.run(_render_print(site_path, Path(output_dir), browser_path))
    except Exception as e:
        log.error(f"PDF export failed: {e}")
        return 1
    return 0


async def _render_print(
    site_path: Path, output_path: Path, browser_path: str | None = None
) -> None:
    """Render HTML pages to PDF using @media print CSS (no UI chrome)."""
    html_files = sorted(site_path.rglob("*.html"))
    if not html_files:
        log.error("No HTML files found")
        return

    output_path.mkdir(parents=True, exist_ok=True)

    browser_exe = browser_path or _find_browser()
    launch_opts = {}
    if browser_exe:
        log.info(f"Using browser: {browser_exe}")
        launch_opts["executable_path"] = browser_exe

    async with async_playwright() as p:
        browser = await p.chromium.launch(**launch_opts)
        page = await browser.new_page()

        total = len(html_files)
        for i, html_file in enumerate(html_files, 1):
            rel = html_file.relative_to(site_path)
            pdf_path = output_path / rel.with_suffix(".pdf")
            pdf_path.parent.mkdir(parents=True, exist_ok=True)

            file_url = html_file.resolve().as_uri()
            # Show the full page path, not just the filename
            log.info(f"[{i}/{total}] {rel.with_suffix('')}")

            try:
                await page.goto(file_url, wait_until="networkidle", timeout=30000)
                await page.emulate_media(media="print")
                await page.pdf(
                    path=str(pdf_path),
                    format="A4",
                    print_background=True,
                    margin={"top": "15mm", "bottom": "15mm", "left": "15mm", "right": "15mm"},
                )
            except Exception as e:
                log.warning(f"  Failed: {e}")

        await browser.close()

    log.info(f"\nPDF export complete: {output_path.resolve()} ({total} pages)")
