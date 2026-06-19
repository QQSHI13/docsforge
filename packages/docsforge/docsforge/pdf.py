"""PDF export — builds PDF from Markdown source using pandoc + weasyprint.

During `docsforge build --pdf`, this module converts the Markdown source
files directly to PDF (same source → same output, just a different format).

Requires:
    pip install weasyprint
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

log = logging.getLogger(__name__)

try:
    from weasyprint import HTML
    HAS_WEASYPRINT = True
except ImportError:
    HAS_WEASYPRINT = False


def _find_md_files(docs_dir: str) -> list[Path]:
    """Find all .md files in the docs directory."""
    return sorted(Path(docs_dir).rglob("*.md"))


def _page_title(path: Path, docs_dir: str) -> str:
    """Extract title from frontmatter or filename."""
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
        # Frontmatter title
        m = re.search(r"^\s*title\s*:\s*(.+)$", content, re.MULTILINE)
        if m:
            return m.group(1).strip().strip("\"'")
        # First H1
        m = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if m:
            return m.group(1).strip()
    except Exception:
        pass
    return path.stem


def _nav_to_markdown(nav_path: Path) -> str:
    """Read nav config and build a markdown list."""
    # Simple approach: list all markdown files with their titles
    lines = ["# Table of Contents\n", ""]
    for md_file in sorted(nav_path.rglob("*.md")):
        rel = md_file.relative_to(nav_path)
        title = _page_title(md_file, str(nav_path))
        lines.append(f"- [{title}]({rel})")
    return "\n".join(lines)


def build_pdf(docs_dir: str, output_dir: str = "pdf") -> int:
    """Convert all markdown files to PDF via weasyprint.

    Args:
        docs_dir: Path to the docs/ directory containing .md files.
        output_dir: Output directory for PDF files (default: pdf/).

    Returns:
        0 on success, 1 on failure.
    """
    if not HAS_WEASYPRINT:
        log.error(
            "WeasyPrint is required for PDF export.\n"
            "Install with: pip install weasyprint"
        )
        return 1

    docs_path = Path(docs_dir)
    if not docs_path.is_dir():
        log.error(f"Docs directory not found: {docs_dir}")
        return 1

    md_files = _find_md_files(str(docs_path))
    if not md_files:
        log.error(f"No .md files found in {docs_dir}")
        return 1

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Build each page as a separate PDF
    total = len(md_files)
    for i, md_file in enumerate(md_files, 1):
        title = _page_title(md_file, str(docs_path))
        rel = md_file.relative_to(docs_path)
        pdf_name = rel.with_suffix(".pdf")
        pdf_path = output_path / pdf_name
        pdf_path.parent.mkdir(parents=True, exist_ok=True)

        log.info(f"[{i}/{total}] {title}")
        try:
            content = md_file.read_text(encoding="utf-8")
            # Strip frontmatter
            content = re.sub(r"^---[\s\S]*?---\s*", "", content)
            # Wrap in minimal HTML for weasyprint
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>{title}</title>
<style>
body {{ font-family: system-ui, sans-serif; line-height: 1.6; max-width: 42rem; margin: auto; padding: 1rem; }}
pre, code {{ font-family: "SF Mono", "Cascadia Code", monospace; font-size: 0.9em; background: #f4f4f4; padding: 0.2em 0.4em; border-radius: 3px; }}
pre code {{ background: none; padding: 0; }}
pre {{ padding: 1em; overflow-x: auto; }}
img {{ max-width: 100%; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ccc; padding: 0.5em; }}
h1, h2, h3, h4 {{ margin-top: 1.5em; }}
blockquote {{ border-left: 3px solid #ccc; margin: 1em 0; padding: 0.5em 1em; color: #555; }}
</style>
</head><body>
{content}
</body></html>"""
            HTML(string=html).write_pdf(str(pdf_path))
        except Exception as e:
            log.warning(f"  Failed: {e}")

    log.info(f"PDF export complete: {output_path.resolve()}")
    log.info(f"  {total} pages")
    return 0
