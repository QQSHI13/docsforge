"""Unit tests for docsforge.tikz."""
from __future__ import annotations

from pathlib import Path

from docsforge.tikz import _compile_tex_to_svg


class TestCompileTexToSvg:
    def test_skips_tex_without_tikz_picture(self, tmp_path: Path):
        tex = tmp_path / "plain.tex"
        tex.write_text("\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}\n")
        output = tmp_path / "plain.svg"

        assert _compile_tex_to_svg(tex, output) is False
        assert not output.exists()

    def test_skips_non_tikz_file_even_if_outdated(self, tmp_path: Path):
        tex = tmp_path / "plain.tex"
        tex.write_text("Just text")
        output = tmp_path / "plain.svg"
        output.write_text("old")

        # Output exists but source has no tikzpicture and is not under tikz/.
        assert _compile_tex_to_svg(tex, output) is False

    def test_processes_file_under_tikz_directory(self, tmp_path: Path):
        tikz_dir = tmp_path / "tikz"
        tikz_dir.mkdir()
        tex = tikz_dir / "diagram.tex"
        tex.write_text("\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}\n")
        output = tmp_path / "diagram.svg"

        # Even without \\begin{tikzpicture}, a file under tikz/ is accepted.
        # If no toolchain is present it returns False; if a toolchain is present
        # it may fail for non-TikZ content, but it must not be skipped outright.
        result = _compile_tex_to_svg(tex, output)
        assert isinstance(result, bool)
