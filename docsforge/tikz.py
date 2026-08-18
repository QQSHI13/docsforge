"""Optional TikZ diagram compilation to SVG.

Compiles .tex files containing TikZ diagrams to SVG during the build.
Requires a LaTeX toolchain (texlive). If not available, warns and skips.
"""

from __future__ import annotations

import concurrent.futures
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

log = logging.getLogger("docsforge.tikz")

# Default preamble for bare diagram sources (files without a \documentclass).
# Only the tikzpicture / tikzcd / axis body needs to be written; the math
# diagram toolchain (pgfplots, tikz-cd, tkz-euclide, amsmath/amssymb) is
# preloaded so it "just works" for a maths encyclopedia.
DEFAULT_TIKZ_PREAMBLE = (
    "\\documentclass[border=2pt]{standalone}\n"
    "\\usepackage{amsmath}\n"
    "\\usepackage{amssymb}\n"
    "\\usepackage{tikz}\n"
    "\\usepackage{pgfplots}\n"
    "\\pgfplotsset{compat=1.18}\n"
    "\\usepackage{tikz-cd}\n"
    "\\usepackage{tkz-euclide}\n"
)


def _wrap_with_preamble(tex_text: str, extra_preamble: list[str] | None = None) -> str:
    """Wrap bare diagram content in a standalone document.

    Files without a ``\\documentclass`` (just a ``\\begin{tikzpicture}`` or
    other picture body) get the default math preamble, so the source stays
    minimal. Full documents pass through unchanged. Extra preamble lines from
    the ``tikz_preamble`` config option are injected after the defaults, before
    ``\\begin{document}``.
    """
    if any(
        line.strip().startswith("\\documentclass") or "\\begin{document}" in line
        for line in tex_text.splitlines()
    ):
        return tex_text
    lines = [DEFAULT_TIKZ_PREAMBLE]
    if extra_preamble:
        lines.append("\n".join(line.strip() for line in extra_preamble))
    lines.append("\\begin{document}\n")
    lines.append(tex_text)
    lines.append("\n\\end{document}")
    return "\n".join(lines)


def _has_tool(name: str) -> bool:
    """Check if a command-line tool is available."""
    return shutil.which(name) is not None


def _run_dvisvgm(input_file: Path, output_path: Path, cwd: Path, name: str) -> bool:
    """Convert a DVI/PDF to SVG with dvisvgm.

    Fonts are embedded (text stays selectable/searchable in the SVG); if that
    fails (minimal TeX installs without the font sets), falls back to
    ``--no-fonts`` so the diagram still compiles with text drawn as paths.
    """
    for extra in ([], ["--no-fonts"]):
        result = subprocess.run(
            ["dvisvgm", *extra, "--output=" + str(output_path), str(input_file)],
            cwd=cwd,
            capture_output=True,
            text=True,
                    )
        if result.returncode == 0:
            if extra:
                log.warning(
                    f"dvisvgm font embedding failed for {name}; fell back to "
                    "--no-fonts (text rendered as paths). Install "
                    "texlive-fonts-recommended for selectable text."
                )
            return True
    log.warning(f"dvisvgm failed for {name}: {result.stderr[:200]}")
    return False


def _needs_rebuild(tex_path: Path, output_path: Path) -> bool:
    """Check if tex file needs recompilation (output missing or older)."""
    if not output_path.exists():
        return True
    return tex_path.stat().st_mtime > output_path.stat().st_mtime


def _compile_tex_to_svg(
    tex_path: Path, output_path: Path, preamble: list[str] | None = None
) -> bool:
    """Compile a single .tex file to SVG.

    Returns True on success, False on failure.
    """
    tex_path = tex_path.resolve()
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Only compile files that contain a TikZ picture or live under a tikz/ directory.
    try:
        tex_text = tex_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        tex_text = ""
    under_tikz_dir = any(part == "tikz" for part in tex_path.parent.parts)
    if "\\begin{tikzpicture}" not in tex_text and not under_tikz_dir:
        log.debug(f"Skipping {tex_path.name}: not a TikZ file")
        return False

    # Skip if output is up to date
    if not _needs_rebuild(tex_path, output_path):
        log.debug(f"Skipping {tex_path.name} (SVG up to date)")
        return True

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        temp_tex = tmpdir / tex_path.name
        temp_tex.write_text(_wrap_with_preamble(tex_text, preamble), encoding="utf-8")

        # Determine which tools to use
        has_latex = _has_tool("latex")
        has_pdflatex = _has_tool("pdflatex")
        has_dvisvgm = _has_tool("dvisvgm")
        has_pdf2svg = _has_tool("pdf2svg")

        if has_latex and has_dvisvgm:
            # Path: latex -> dvi -> dvisvgm -> svg
            result = subprocess.run(
                ["latex", "-no-shell-escape", "-interaction=nonstopmode", "-halt-on-error", temp_tex.name],
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

            if not _run_dvisvgm(dvi_file, output_path, tmpdir, tex_path.name):
                return False

        elif has_pdflatex and has_pdf2svg:
            # Path: pdflatex -> pdf -> pdf2svg -> svg
            result = subprocess.run(
                ["pdflatex", "-no-shell-escape", "-interaction=nonstopmode", "-halt-on-error", temp_tex.name],
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
                ["pdflatex", "-no-shell-escape", "-interaction=nonstopmode", "-halt-on-error", temp_tex.name],
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

            if not _run_dvisvgm(pdf_file, output_path, tmpdir, tex_path.name):
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
    DocsForge can discover them during markdown processing, and also copies to
    site_dir/assets/tikz/. Otherwise writes only to site_dir/assets/tikz/.

    Returns list of generated SVG paths.
    """
    docs_dir = Path(config.docs_dir)
    site_dir = Path(config.site_dir)
    # When output_to_docs is set, SVGs must be written into the docs tree so
    # they become documentation files: relative links like `assets/tikz/foo.svg`
    # in Markdown then resolve to a real file and get rewritten correctly for
    # the output page (and the build copies them into site_dir automatically).
    # Without the docs-tree write, links stay raw and 404 on the deployed site.
    if output_to_docs:
        output_dir = docs_dir / "assets" / "tikz"
    else:
        output_dir = site_dir / "assets" / "tikz"

    # Check if tikz config is enabled
    tikz_config = getattr(config, "tikz", None)
    if tikz_config is False:
        log.debug("TikZ compilation disabled in config")
        return []

    # Extra preamble lines injected into bare diagram sources (no \documentclass).
    tikz_preamble = getattr(config, "tikz_preamble", None) or []
    if not isinstance(tikz_preamble, list):
        tikz_preamble = []
    elif any(not isinstance(line, str) for line in tikz_preamble):
        log.warning("tikz_preamble must be a list of strings; ignoring non-string entries")
        tikz_preamble = [line for line in tikz_preamble if isinstance(line, str)]

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

    generated: list[Path] = []
    skipped = 0
    newly_compiled = 0

    def _compile_one(tex_file: Path) -> Path | None:
        """Compile a single TikZ file; returns output path or None."""
        svg_name = tex_file.with_suffix(".svg").name
        output_path = output_dir / svg_name

        if not _needs_rebuild(tex_file, output_path):
            nonlocal skipped
            skipped += 1
            log.debug(f"Skipping {tex_file.name} (SVG up to date)")
            if output_to_docs:
                site_output = site_dir / "assets" / "tikz" / svg_name
                if not site_output.exists():
                    site_output.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(output_path, site_output)
                    log.debug(f"Copied TikZ SVG to site: {site_output}")
            return output_path

        if _compile_tex_to_svg(tex_file, output_path, preamble=tikz_preamble):
            nonlocal newly_compiled
            newly_compiled += 1
            if output_to_docs:
                site_output = site_dir / "assets" / "tikz" / svg_name
                site_output.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(output_path, site_output)
                log.debug(f"Copied TikZ SVG to site: {site_output}")
            return output_path
        return None

    # Compile in parallel using thread pool (each LaTeX process is CPU-bound but I/O-waiting)
    max_workers = min(config.concurrency, len(tex_files)) if len(tex_files) > 1 else 1
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_compile_one, f): f for f in tex_files}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                generated.append(result)

    if skipped:
        log.info(
            f"TikZ: {newly_compiled} compiled, {skipped} skipped (up to date), "
            f"{len(generated)} total"
        )
    else:
        log.info(f"TikZ: {newly_compiled} diagrams compiled")

    return generated
