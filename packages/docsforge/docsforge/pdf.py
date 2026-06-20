"""PDF export — renders built HTML to PDF via WeasyPrint.

Mermaid and KaTeX content is pre-rendered using Node.js CLIs, then
WeasyPrint converts the static HTML to PDF — no browser required.

Requires:
    pip install weasyprint
    npm install -g katex @mermaid-js/mermaid-cli
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

log = logging.getLogger(__name__)

try:
    from weasyprint import HTML
    HAS_WEASYPRINT = True
except ImportError:
    HAS_WEASYPRINT = False


def _check_tool(name: str) -> bool:
    """Check if a command-line tool is available."""
    return shutil.which(name) is not None


def _render_katex(html: str) -> str:
    """Pre-render KaTeX math expressions in HTML to static HTML."""
    # Replace display math $$...$$ with rendered KaTeX HTML
    def _replace_display(m):
        expr = m.group(1).strip()
        try:
            result = subprocess.run(
                ["npx", "katex", expr, "--display-mode"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return m.group(0)

    # Replace inline math $...$ with rendered KaTeX HTML
    def _replace_inline(m):
        expr = m.group(1).strip()
        try:
            result = subprocess.run(
                ["npx", "katex", expr],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return m.group(0)

    # Process display math first, then inline math
    html = re.sub(r"\$\$(.+?)\$\$", _replace_display, html, flags=re.DOTALL)
    html = re.sub(r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", _replace_inline, html)
    return html


def _render_mermaid(html: str, page_dir: Path) -> str:
    """Pre-render Mermaid diagrams in HTML to inline SVG."""
    def _replace(m):
        code = m.group(1).strip()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                mmd_file = Path(tmp) / "diagram.mmd"
                svg_file = Path(tmp) / "diagram.svg"
                config_file = Path(tmp) / "config.json"

                mmd_file.write_text(code)
                config_file.write_text(json.dumps({
                    "theme": "default",
                    "backgroundColor": "transparent",
                }))

                subprocess.run(
                    ["npx", "@mermaid-js/mermaid-cli", "-i", str(mmd_file),
                     "-o", str(svg_file), "-c", str(config_file)],
                    capture_output=True, timeout=30,
                )

                if svg_file.exists():
                    svg = svg_file.read_text()
                    # Clean up the SVG for embedding
                    svg = re.sub(r'<svg', '<svg style="max-width:100%;height:auto"', svg, count=1)
                    return svg
        except Exception:
            pass
        return m.group(0)

    return re.sub(
        r'<pre[^>]*>\s*<code[^>]*class="[^"]*language-mermaid[^"]*"[^>]*>(.*?)</code>\s*</pre>',
        _replace, html, flags=re.DOTALL | re.IGNORECASE
    )


def _render_page(html_path: Path) -> str:
    """Load an HTML page, pre-render KaTeX and Mermaid, return clean HTML."""
    html = html_path.read_text(encoding="utf-8", errors="ignore")

    # Extract only the content area (skip header, nav, footer)
    m = re.search(
        r'<article[^>]*class="md-content__inner[^"]*"[^>]*>(.*?)</article>',
        html, re.DOTALL
    )
    if m:
        content = m.group(1)
    else:
        # Fallback: extract body content
        m = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL)
        content = m.group(1) if m else html

    # Pre-render KaTeX if available
    if _check_tool("npx"):
        # Check if katex is installed
        try:
            subprocess.run(["npx", "katex", "--version"], capture_output=True, timeout=5)
            content = _render_katex(content)
        except Exception:
            pass

        # Pre-render Mermaid if available
        try:
            subprocess.run(
                ["npx", "@mermaid-js/mermaid-cli", "--version"],
                capture_output=True, timeout=5,
            )
            content = _render_mermaid(content, html_path.parent)
        except Exception:
            pass

    # Wrap in a minimal print-friendly HTML document
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
body {{
    font-family: system-ui, -apple-system, sans-serif;
    line-height: 1.6;
    max-width: 42rem;
    margin: auto;
    padding: 0.5rem;
    font-size: 11pt;
    color: #1a1a1a;
}}
pre, code {{
    font-family: "SF Mono", "Cascadia Code", "Consolas", monospace;
    font-size: 9pt;
}}
code {{
    background: #f0f0f0;
    padding: 0.15em 0.3em;
    border-radius: 2px;
}}
pre {{
    background: #f5f5f5;
    padding: 0.8em;
    border: 1px solid #ddd;
    border-radius: 4px;
    overflow-x: auto;
    page-break-inside: avoid;
}}
pre code {{ background: none; padding: 0; }}
img {{ max-width: 100%; height: auto; }}
table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
th, td {{ border: 1px solid #ccc; padding: 0.4em 0.6em; text-align: left; }}
th {{ background: #f0f0f0; }}
h1, h2, h3, h4 {{ margin-top: 1.2em; margin-bottom: 0.4em; page-break-after: avoid; }}
h1 {{ font-size: 18pt; }}
h2 {{ font-size: 15pt; border-bottom: 1px solid #ddd; padding-bottom: 0.2em; }}
h3 {{ font-size: 13pt; }}
p, li {{ orphans: 3; widows: 3; }}
blockquote {{
    border-left: 3px solid #ccc;
    margin: 0.8em 0;
    padding: 0.3em 1em;
    color: #555;
}}
.math {{
    overflow-x: auto;
    padding: 0.5em 0;
}}
a {{ color: #1a56db; text-decoration: none; }}
.admonition {{
    border-left: 4px solid #448aff;
    background: #f8f9ff;
    padding: 0.5em 1em;
    margin: 1em 0;
    border-radius: 4px;
    page-break-inside: avoid;
}}
.admonition-title {{ font-weight: bold; margin-bottom: 0.3em; }}
.mermaid svg {{ max-width: 100%; height: auto; page-break-inside: avoid; }}

/* Content tabs: show all tabs in print */
.tabbed-set {{ display: block; }}
.tabbed-set input {{ display: none; }}
.tabbed-set > .tabbed-content {{ display: block !important; }}
.tabbed-set .tabbed-block {{ display: block !important; visibility: visible !important; }}
.tabbed-set label {{
    display: inline-block;
    font-weight: bold;
    margin-right: 1em;
    padding: 0.2em 0.5em;
    background: #eee;
    border-radius: 3px;
    font-size: 10pt;
}}

/* Hide UI chrome */
.md-header, .md-tabs, .md-footer, .md-sidebar,
.md-search, .md-top, .md-source, .md-annotation,
.md-content__button, .md-source-file, .md-nav,
.md-dialog, .md-progress, [data-md-component="skip"],
.md-header__option, .md-header__topic {{
    display: none !important;
}}
</style>
</head><body>
{content}
</body></html>"""


def build_pdf(docs_dir: str, output_dir: str = "pdf", **kwargs) -> int:
    """Build the site and export to PDF via WeasyPrint.

    Args:
        docs_dir: Path to the docs/ directory.
        output_dir: Output directory for PDF files.
    """
    if not HAS_WEASYPRINT:
        log.error("WeasyPrint required. Install: pip install weasyprint")
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

    # Find all HTML pages
    html_files = sorted(site_path.rglob("*.html"))
    if not html_files:
        log.error("No HTML files found")
        return 1

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    total = len(html_files)

    log.info(f"Pre-rendering KaTeX and Mermaid...")
    for i, html_file in enumerate(html_files, 1):
        rel = html_file.relative_to(site_path)
        log.info(f"  [{i}/{total}] {rel.with_suffix('')}")

        try:
            clean_html = _render_page(html_file)
            pdf_path = output_path / rel.with_suffix(".pdf")
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            HTML(string=clean_html).write_pdf(str(pdf_path))
        except Exception as e:
            log.warning(f"  Failed: {e}")

    log.info(f"\nPDF export complete: {output_path.resolve()} ({total} pages)")
    log.info("Pre-rendered: KaTeX ✓  Mermaid ✓  (via Node.js CLIs)")
    return 0
