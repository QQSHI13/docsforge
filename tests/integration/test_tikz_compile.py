"""Integration test: compile TikZ diagrams with the default math preamble.

Skipped when no LaTeX toolchain (latex + dvisvgm) is installed.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from docsforge.tikz import _compile_tex_to_svg

pytestmark = pytest.mark.skipif(
    not all(shutil.which(t) for t in ("latex", "dvisvgm")),
    reason="LaTeX toolchain (latex + dvisvgm) not installed",
)


def test_compiles_bare_source_with_default_preamble(tmp_path: Path):
    tikz_dir = tmp_path / "tikz"
    tikz_dir.mkdir()
    tex = tikz_dir / "math-kit.tex"
    tex.write_text(
        "\\begin{tikzcd}\n"
        '  \\mathbb{R}^2 \\ar[r, "f"] & \\mathbb{R} \\\\\n'
        "\\end{tikzcd}\n"
        "\\begin{tikzpicture}\n"
        "  \\begin{axis}[width=5cm, height=3cm]\n"
        "    \\addplot[domain=-1:1] {x^2};\n"
        "  \\end{axis}\n"
        "\\end{tikzpicture}\n"
        "\\begin{tikzpicture}\n"
        "  \\tkzDefPoint(0,0){A}\n"
        "  \\tkzDefPoint(2,0){B}\n"
        "  \\tkzDefPoint(0,2){C}\n"
        "  \\tkzDrawSegments(A,B B,C C,A)\n"
        "\\end{tikzpicture}\n"
    )
    output = tmp_path / "math-kit.svg"

    assert _compile_tex_to_svg(tex, output, preamble=["\\usetikzlibrary{calc}"]) is True
    assert output.exists()

    svg = output.read_bytes()
    # Embedded fonts keep diagram text as real text elements (not outlined paths).
    assert b"<text" in svg


def test_content_hash_cache_skips_unchanged_and_recompiles_changed(tmp_path: Path):
    """The hash-based cache must skip unchanged diagrams (even with bumped
    mtimes) and recompile when the effective source (tex + preamble) changes."""
    from docsforge.cache import FileHasher
    from docsforge.tikz import _wrap_with_preamble

    tikz_dir = tmp_path / "tikz"
    tikz_dir.mkdir()
    tex = tikz_dir / "square.tex"
    tex.write_text("\\begin{tikzpicture}\n  \\draw (0,0) -- (1,0) -- (1,1) -- (0,1) -- cycle;\n\\end{tikzpicture}\n")
    output = tmp_path / "square.svg"
    preamble = ["\\usetikzlibrary{calc}"]

    assert _compile_tex_to_svg(tex, output, preamble=preamble) is True
    assert output.exists()
    first_mtime = output.stat().st_mtime_ns
    first_svg = output.read_bytes()

    expected = FileHasher.hash_string(_wrap_with_preamble(tex.read_text(), preamble))
    assert _compile_tex_to_svg(tex, output, preamble=preamble, cached_hash=expected) is True
    assert output.stat().st_mtime_ns == first_mtime, "unchanged diagram was recompiled"
    assert output.read_bytes() == first_svg

    tex.write_text("\\begin{tikzpicture}\n  \\draw (0,0) circle (1);\n\\end{tikzpicture}\n")
    assert _compile_tex_to_svg(tex, output, preamble=preamble, cached_hash=expected) is True
    assert output.stat().st_mtime_ns != first_mtime, "changed diagram was not recompiled"
    assert output.read_bytes() != first_svg
