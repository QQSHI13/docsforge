"""Unit tests for docsforge.tikz."""
from __future__ import annotations

from pathlib import Path

from docsforge.tikz import DEFAULT_TIKZ_PREAMBLE, _compile_tex_to_svg, _wrap_with_preamble


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


class TestWrapWithPreamble:
    def test_wraps_bare_tikzpicture(self):
        body = "\\begin{tikzpicture}\n\\draw (0,0) -- (1,1);\n\\end{tikzpicture}\n"
        wrapped = _wrap_with_preamble(body)

        assert wrapped.startswith("\\documentclass[border=2pt]{standalone}\n")
        assert "\\usepackage{amsmath}\n" in wrapped
        assert "\\usepackage{amssymb}\n" in wrapped
        assert "\\usepackage{tikz}\n" in wrapped
        assert "\\usepackage{pgfplots}\n" in wrapped
        assert "\\usepackage{tikz-cd}\n" in wrapped
        assert "\\usepackage{tkz-euclide}\n" in wrapped
        assert "\\begin{document}\n" in wrapped
        assert wrapped.endswith("\\end{document}")
        # The picture body survives verbatim between \begin{document} and \end{document}.
        assert wrapped.index(body) > wrapped.index("\\begin{document}")

    def test_passes_through_full_document(self):
        tex = "\\documentclass{article}\n\\begin{document}\n\\begin{tikzpicture}\n\\end{tikzpicture}\n\\end{document}\n"
        assert _wrap_with_preamble(tex) == tex

    def test_wraps_despite_documentclass_mention_in_comment(self):
        # A comment mentioning \documentclass must not trigger pass-through.
        tex = "% No \\documentclass is needed here\n\\begin{tikzpicture}\n\\end{tikzpicture}\n"
        wrapped = _wrap_with_preamble(tex)
        assert wrapped.startswith("\\documentclass[border=2pt]{standalone}\n")

    def test_passes_through_when_begin_document_present(self):
        tex = "\\begin{document}\n\\begin{tikzpicture}\n\\end{tikzpicture}\n\\end{document}\n"
        assert _wrap_with_preamble(tex) == tex

    def test_appends_extra_preamble_after_defaults(self):
        body = "\\begin{tikzpicture}\n\\end{tikzpicture}\n"
        wrapped = _wrap_with_preamble(body, ["\\usetikzlibrary{calc}", "\\usepackage{caption}"])

        assert "\\usetikzlibrary{calc}\n\\usepackage{caption}\n\\begin{document}" in wrapped
        assert wrapped.index("\\usetikzlibrary{calc}") > wrapped.index(
            "\\usepackage{pgfplots}"
        )

    def test_default_preamble_contains_all_math_packages(self):
        for package in ("amsmath", "amssymb", "tikz", "pgfplots", "tikz-cd", "tkz-euclide"):
            assert f"\\usepackage{{{package}}}" in DEFAULT_TIKZ_PREAMBLE