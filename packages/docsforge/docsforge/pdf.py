"""PDF export — renders the fully built site to PDF.

During `docsforge build --pdf`, this:
1. Runs the full build (Mermaid, KaTeX, TikZ, syntax highlighting, all plugins)
2. Converts every HTML page to A4 PDF using Playwright's Chromium

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
    """Build the site and export as PDF.

    This runs the real docsforge build pipeline (with all plugins, extensions,
    Mermaid, KaTeX, TikZ, etc.), then renders each page to PDF.

    Args:
        docs_dir: Path to the docs/ directory (used to find docsforge.yml).
        output_dir: Output directory for PDF files.

    Returns:
        0 on success, 1 on failure.
    """
    if not HAS_PLAYWRIGHT:
        log.error(
            "Playwright is required for PDF export.\n"
            "Install with: pip install playwright && playwright install chromium"
        )
        return 1

    # Step 1: Build the site with full pipeline
    project_dir = Path(docs_dir).parent if Path(docs_dir).name == "docs" else Path(docs_dir)
    log.info("Step 1: Building site (full pipeline)...")
    result = subprocess.run(
        [sys.executable, "-m", "docsforge", "build"],
        cwd=str(project_dir),
        capture_output=False,
    )
    if result.returncode != 0:
        log.error("Build failed — aborting PDF export")
        return 1

    # Determine site_dir from config
    config_path = project_dir / "docsforge.yml"
    site_dir = "site"
    if config_path.exists():
        try:
            import yaml
            with open(config_path) as f:
                cfg = yaml.safe_load(f) or {}
            site_dir = cfg.get("site_dir", "site")
        except Exception:
            pass

    site_path = project_dir / site_dir
    if not site_path.is_dir():
        log.error(f"Site directory not found: {site_path}")
        return 1

    # Step 2: Render each HTML page to PDF
    log.info("Step 2: Rendering to PDF...")
    import asyncio
    try:
        asyncio.run(_render_all(site_path, Path(output_dir)))
    except Exception as e:
        log.error(f"PDF rendering failed: {e}")
        return 1

    return 0


async def _render_all(site_path: Path, output_path: Path) -> None:
    """Render all HTML pages to PDF using Playwright."""
    html_files = sorted(site_path.rglob("*.html"))
    if not html_files:
        log.error("No HTML files found in site directory")
        return

    output_path.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        total = len(html_files)
        for i, html_file in enumerate(html_files, 1):
            rel = html_file.relative_to(site_path)
            title = html_file.stem.replace("-", " ").title()

            pdf_name = rel.with_suffix(".pdf")
            pdf_path = output_path / pdf_name
            pdf_path.parent.mkdir(parents=True, exist_ok=True)

            file_url = html_file.resolve().as_uri()
            log.info(f"[{i}/{total}] {pdf_name}")

            try:
                await page.goto(file_url, wait_until="networkidle", timeout=30000)
                await page.pdf(
                    path=str(pdf_path),
                    format="A4",
                    print_background=True,
                    margin={"top": "15mm", "bottom": "15mm", "left": "15mm", "right": "15mm"},
                )
            except Exception as e:
                log.warning(f"  Failed: {e}")

        await browser.close()

    log.info(f"\nPDF export complete: {output_path.resolve()}")
    log.info(f"  {total} pages")
