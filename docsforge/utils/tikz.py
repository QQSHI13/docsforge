"""Optional TikZ diagram compilation to SVG.

Compiles .tex files containing TikZ diagrams to SVG during the build.
Requires a LaTeX toolchain (texlive). If not available, warns and skips.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

log = logging.getLogger("docsforge.tikz")


def _has_tool(name: str) -> bool:
    """Check if a command-line tool is available."""
    return shutil.which(name) is not None


def _compile_tex_to_svg(tex_path: Path, output_path: Path) -> bool:
    """Compile a single .tex file to SVG.

    Returns True on success, False on failure.
    """
    tex_path = tex_path.resolve()
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        temp_tex = tmpdir / tex_path.name
        shutil.copy2(tex_path, temp_tex)

        # Determine which tools to use
        has_latex = _has_tool("latex")
        has_pdflatex = _has_tool("pdflatex")
        has_dvisvgm = _has_tool("dvisvgm")
        has_pdf2svg = _has_tool("pdf2svg")

        if has_latex and has_dvisvgm:
            # Path: latex -> dvi -> dvisvgm -> svg
            result = subprocess.run(
                ["latex", "-interaction=nonstopmode", "-halt-on-error", temp_tex.name],
                cwd=tmpdir,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                err = result.stderr[:500] if result.stderr else result.stdout[:500]
                log.warning(f"latex failed for {tex_path.name}: {err}")
                return False

            dvi_file = tmpdir / temp_tex.with_suffix(".dvi").name
            if not dvi_file.exists():
                log.warning(f"No DVI produced for {tex_path.name}")
                return False

            result = subprocess.run(
                ["dvisvgm", "--no-fonts", "--output=" + str(output_path), str(dvi_file)],
                cwd=tmpdir,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                log.warning(f"dvisvgm failed for {tex_path.name}: {result.stderr[:200]}")
                return False

        elif has_pdflatex and has_pdf2svg:
            # Path: pdflatex -> pdf -> pdf2svg -> svg
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", temp_tex.name],
                cwd=tmpdir,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                log.warning(f"pdflatex failed for {tex_path.name}: {result.stderr[:200]}")
                return False

            pdf_file = tmpdir / temp_tex.with_suffix(".pdf").name
            if not pdf_file.exists():
                log.warning(f"No PDF produced for {tex_path.name}")
                return False

            result = subprocess.run(
                ["pdf2svg", str(pdf_file), str(output_path)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                log.warning(f"pdf2svg failed for {tex_path.name}: {result.stderr[:200]}")
                return False

        elif has_pdflatex and has_dvisvgm:
            # Path: pdflatex -> pdf -> dvisvgm -> svg (dvisvgm 2.0+ supports PDF)
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", temp_tex.name],
                cwd=tmpdir,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                log.warning(f"pdflatex failed for {tex_path.name}: {result.stderr[:200]}")
                return False

            pdf_file = tmpdir / temp_tex.with_suffix(".pdf").name
            if not pdf_file.exists():
                log.warning(f"No PDF produced for {tex_path.name}")
                return False

            result = subprocess.run(
                ["dvisvgm", "--no-fonts", "--output=" + str(output_path), str(pdf_file)],
                cwd=tmpdir,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                log.warning(f"dvisvgm failed for {tex_path.name}: {result.stderr[:200]}")
                return False

        else:
            log.warning(
                f"Cannot compile {tex_path.name}: no LaTeX toolchain found. "
                "Install texlive (e.g., 'apt install texlive texlive-pictures dvisvgm')."
            )
            return False

    if output_path.exists():
        log.info(f"Compiled TikZ: {tex_path.name} -> {output_path}")
        return True
    return False


def compile_tikz_files(config, *, output_to_docs: bool = False) -> list[Path]:
    """Find and compile all .tex files in docs_dir to SVGs.

    If output_to_docs is True, writes SVGs to docs_dir/assets/tikz/ so that
    MkDocs can discover them during markdown processing, and also copies to
    site_dir/assets/tikz/. Otherwise writes only to site_dir/assets/tikz/.

    Returns list of generated SVG paths.
    """
    docs_dir = Path(config.docs_dir)
    site_dir = Path(config.site_dir)
    if output_to_docs:
        output_dir = docs_dir / "assets" / "tikz"
    else:
        output_dir = site_dir / "assets" / "tikz"

    # Check if tikz config is enabled
    tikz_config = getattr(config, "tikz", None)
    if tikz_config is False:
        log.debug("TikZ compilation disabled in config")
        return []

    tex_files = list(docs_dir.rglob("*.tex"))
    if not tex_files:
        return []

    # Check for any LaTeX tool
    has_any_latex = _has_tool("latex") or _has_tool("pdflatex")
    has_dvisvgm = _has_tool("dvisvgm")
    has_pdf2svg = _has_tool("pdf2svg")

    if not has_any_latex:
        if tikz_config is True:
            log.error(
                "TikZ is enabled but no LaTeX toolchain found. "
                "Install texlive (e.g., 'apt install texlive texlive-pictures dvisvgm')."
            )
        else:
            log.info(
                "TikZ .tex files found but no LaTeX toolchain. Skipping. "
                "Install texlive to enable TikZ compilation."
            )
        return []

    if not (has_dvisvgm or has_pdf2svg):
        if tikz_config is True:
            log.error(
                "TikZ is enabled but no SVG converter found. "
                "Install dvisvgm or pdf2svg."
            )
        else:
            log.info(
                "TikZ .tex files found but no SVG converter (dvisvgm/pdf2svg). Skipping."
            )
        return []

    generated = []
    for tex_file in tex_files:
        # Compute output path (flatten: all SVGs go directly into output_dir)
        svg_name = tex_file.with_suffix(".svg").name
        output_path = output_dir / svg_name

        if _compile_tex_to_svg(tex_file, output_path):
            generated.append(output_path)
            # If outputting to docs, also copy to site for serving
            if output_to_docs:
                site_output = site_dir / "assets" / "tikz" / svg_name
                site_output.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(output_path, site_output)
                log.debug(f"Copied TikZ SVG to site: {site_output}")

    return generated
