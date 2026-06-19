"""PDF export — renders built HTML to PDF using Playwright.

Usage:
    docsforge build --pdf

Requires playwright and chromium:
    pip install playwright
    playwright install chromium
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


def _find_html_files(site_dir: str) -> list[str]:
    """Find all HTML files in the site directory, sorted by path."""
    html_files: list[str] = []
    site_path = Path(site_dir)
    for path in sorted(site_path.rglob("*.html")):
        if path.is_file():
            # Convert to URL path relative to site root
            rel = path.relative_to(site_path).as_posix()
            html_files.append(rel)
    return html_files


def _get_page_title(site_dir: str, rel_path: str) -> str:
    """Extract the page title from HTML content."""
    filepath = Path(site_dir) / rel_path
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
        import re
        m = re.search(r"<title[^>]*>([^<]+)</title>", content)
        if m:
            return m.group(1).strip()
    except Exception:
        pass
    return rel_path


async def _render_pdf(site_dir: str, output_dir: str) -> None:
    """Render all HTML pages to PDF using Playwright."""
    html_files = _find_html_files(site_dir)
    if not html_files:
        log.error("No HTML files found in site directory")
        return

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        total = len(html_files)
        for i, rel_path in enumerate(html_files, 1):
            file_url = f"file://{Path(site_dir).resolve() / rel_path}"
            title = _get_page_title(site_dir, rel_path)
            pdf_name = rel_path.removesuffix(".html").removesuffix("/index") + ".pdf"
            if not pdf_name.endswith(".pdf"):
                pdf_name += ".pdf"
            # Replace / with -- for flat output, or preserve directory structure
            pdf_path = output_path / pdf_name.replace("/", "--")

            log.info(f"[{i}/{total}] Rendering: {title}")
            try:
                await page.goto(file_url, wait_until="networkidle")
                await page.pdf(
                    path=str(pdf_path),
                    format="A4",
                    print_background=True,
                    margin={"top": "15mm", "bottom": "15mm", "left": "15mm", "right": "15mm"},
                )
            except Exception as e:
                log.warning(f"  Failed: {e}")

        await browser.close()

    log.info(f"PDF export complete. Files in: {output_path.resolve()}")


def export_pdf(site_dir: str, output_dir: str = "pdf") -> int:
    """Build documentation and export to PDF.

    Args:
        site_dir: The built site directory.
        output_dir: Output directory for PDF files (default: pdf/).

    Returns:
        0 on success, 1 on failure.
    """
    if not HAS_PLAYWRIGHT:
        log.error(
            "Playwright is required for PDF export.\n"
            "Install with: pip install playwright && playwright install chromium"
        )
        return 1

    import asyncio
    try:
        asyncio.run(_render_pdf(site_dir, output_dir))
        return 0
    except Exception as e:
        log.error(f"PDF export failed: {e}")
        return 1
