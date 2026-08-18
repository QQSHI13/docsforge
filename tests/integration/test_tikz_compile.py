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