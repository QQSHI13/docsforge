"""PDF export — renders the fully built site to clean, print-ready PDF.

During `docsforge build --pdf`, this:
1. Runs the full build (Mermaid, KaTeX, TikZ, all plugins)
2. Renders each page using Playwright with @media print CSS
   — Material theme hides nav bars, tabs, footers, collapsibles,
     search, and other UI chrome automatically in print mode.
3. Outputs A4 PDFs with proper margins and page breaks.

Requires:
    pip install playwright
    playwright install chromium
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

log = logging.getLogger(__name__)

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


def build_pdf(docs_dir: str, output_dir: str = "pdf") -> int:
    """Build the site and export as print-ready PDF.

    Steps:
    1. Full `docsforge build` (all plugins, extensions, diagrams, math)
    2. Render each page via Playwright Chromium in print mode

    Args:
        docs_dir: Path to the docs/ directory.
        output_dir: Output directory for PDF files.

    Returns:
        0 on success, 1 on failure.
    """
    if not HAS_PLAYWRIGHT:
        log.error("Playwright required. Install: pip install playwright && playwright install chromium")
        return 1

    project_dir = Path(docs_dir).parent if Path(docs_dir).name == "docs" else Path(docs_dir)

    # Step 1: Full build
    log.info("Building site (full pipeline)...")
    r = subprocess.run([sys.executable, "-m", "docsforge", "build"], cwd=str(project_dir))
    if r.returncode != 0:
        return 1

    # Find site_dir
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
        log.error(f"Site directory not found: {site_path}")
        return 1

    # Step 2: PDF render with print CSS
    log.info("Rendering PDFs (print mode)...")
    import asyncio
    try:
        asyncio.run(_render_print(site_path, Path(output_dir)))
    except Exception as e:
        log.error(f"PDF export failed: {e}")
        return 1
    return 0


async def _render_print(site_path: Path, output_path: Path) -> None:
    """Render HTML pages to PDF using @media print CSS (no UI chrome)."""
    html_files = sorted(site_path.rglob("*.html"))
    if not html_files:
        log.error("No HTML files found")
        return

    output_path.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        total = len(html_files)
        for i, html_file in enumerate(html_files, 1):
            rel = html_file.relative_to(site_path)
            pdf_path = output_path / rel.with_suffix(".pdf")
            pdf_path.parent.mkdir(parents=True, exist_ok=True)

            file_url = html_file.resolve().as_uri()
            log.info(f"[{i}/{total}] {pdf_path.name}")

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
