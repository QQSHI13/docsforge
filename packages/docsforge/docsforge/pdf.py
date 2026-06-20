"""PDF export — renders the fully built site to clean, print-ready PDF.

During `docsforge build --pdf`, this:
1. Runs the full build (Mermaid, KaTeX, TikZ, all plugins)
2. Renders each page using Playwright with @media print CSS
   — Material theme hides nav bars, tabs, footers in print mode.
3. Uses multiple browser tabs for parallel rendering.
4. Outputs A4 PDFs preserving the site directory structure.

Requires:
    pip install playwright
    # Then either: playwright install chromium
    # Or set PLAYWRIGHT_CHROMIUM_EXECUTABLE to your browser path
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


def build_pdf(docs_dir: str, output_dir: str = "pdf", *,
              browser_path: str | None = None, skip_build: bool = False) -> int:
    """Build the site and export as print-ready PDF."""
    if not HAS_PLAYWRIGHT:
        log.error("Playwright required. Install: pip install playwright && playwright install chromium")
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

    log.info("Rendering PDFs (print mode)...")
    try:
        asyncio.run(_render_print(site_path, Path(output_dir), browser_path))
    except Exception as e:
        log.error(f"PDF export failed: {e}")
        return 1
    return 0


async def _render_print(
    site_path: Path, output_path: Path, browser_path: str | None = None,
    concurrency: int = 4,
) -> None:
    """Render HTML pages to PDF using multiple browser tabs."""
    html_files = sorted(site_path.rglob("*.html"))
    if not html_files:
        log.error("No HTML files found")
        return

    output_path.mkdir(parents=True, exist_ok=True)
    total = len(html_files)

    browser_exe = browser_path or _find_browser()
    launch_opts = {}
    if browser_exe:
        log.info(f"Browser: {browser_exe}  Tabs: {concurrency}  Pages: {total}")
    else:
        log.info(f"Tabs: {concurrency}  Pages: {total}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(**launch_opts)

        # Create tab pool
        tabs = await asyncio.gather(*[browser.new_page() for _ in range(concurrency)])
        for tab in tabs:
            await tab.emulate_media(media="print")

        async def render_one(tab, html_file, idx):
            rel = html_file.relative_to(site_path)
            pdf_path = output_path / rel.with_suffix(".pdf")
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            url = html_file.resolve().as_uri()
            try:
                await tab.goto(url, wait_until="load", timeout=30000)
                # Wait for Mermaid diagrams to render (JS-rendered after page load)
                try:
                    await tab.wait_for_function(
                        "() => document.querySelectorAll('.mermaid svg').length === document.querySelectorAll('.mermaid').length",
                        timeout=10000
                    )
                except Exception:
                    pass  # No mermaid diagrams on this page, or timeout is fine
                await tab.pdf(
                    path=str(pdf_path), format="A4", print_background=True,
                    margin={"top": "15mm", "bottom": "15mm", "left": "15mm", "right": "15mm"},
                )
                log.info(f"  [{idx}/{total}] {rel.with_suffix('')}")
            except Exception as e:
                log.warning(f"  [{idx}/{total}] FAILED {rel.with_suffix('')} — {e}")

        # Round-robin: assign files to tabs, render in parallel batches
        for batch_start in range(0, total, concurrency):
            batch = html_files[batch_start:batch_start + concurrency]
            tasks = [
                render_one(tabs[i % concurrency], file, batch_start + i + 1)
                for i, file in enumerate(batch)
            ]
            await asyncio.gather(*tasks)

        for tab in tabs:
            await tab.close()
        await browser.close()

    log.info(f"\nPDF export complete: {output_path.resolve()} ({total} pages)")
