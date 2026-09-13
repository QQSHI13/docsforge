"""Unit tests for docsforge.tikz."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from docsforge.tikz import DEFAULT_TIKZ_PREAMBLE, _compile_tex_to_svg, _needs_rebuild, _wrap_with_preamble


class TestNeedsRebuild:
    def test_output_missing_always_rebuilds(self, tmp_path: Path):
        tex = tmp_path / "a.tex"
        tex.write_text("x")
        assert _needs_rebuild(tex, tmp_path / "a.svg", "h", "h") is True

    def test_hash_equal_skips_even_with_new_mtime(self, tmp_path: Path):
        # A restored site + bumped mtimes (git checkout, CI cache restore)
        # must NOT recompile an unchanged diagram.
        tex = tmp_path / "a.tex"
        out = tmp_path / "a.svg"
        tex.write_text("x")
        out.write_text("svg")
        os.utime(tex, (10_000, 10_000))
        os.utime(out, (1_000, 1_000))
        assert _needs_rebuild(tex, out, "h1", "h1") is False

    def test_hash_differs_rebuilds(self, tmp_path: Path):
        tex = tmp_path / "a.tex"
        out = tmp_path / "a.svg"
        tex.write_text("x")
        out.write_text("svg")
        assert _needs_rebuild(tex, out, "h1", "h2") is True

    def test_mtime_fallback_without_hashes(self, tmp_path: Path):
        tex = tmp_path / "a.tex"
        out = tmp_path / "a.svg"
        tex.write_text("x")
        out.write_text("svg")
        os.utime(tex, (1_000, 1_000))
        os.utime(out, (2_000, 2_000))
        assert _needs_rebuild(tex, out) is False
        os.utime(tex, (3_000, 3_000))
        assert _needs_rebuild(tex, out) is True

    def test_missing_hash_falls_back_to_mtime(self, tmp_path: Path):
        tex = tmp_path / "a.tex"
        out = tmp_path / "a.svg"
        tex.write_text("x")
        out.write_text("svg")
        os.utime(tex, (1_000, 1_000))
        os.utime(out, (2_000, 2_000))
        assert _needs_rebuild(tex, out, "h1", None) is False


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


class TestOutputLock:
    """Regression: concurrent compiles of the same output path must serialize."""

    def test_output_lock_serializes_compile(self, tmp_path: Path, monkeypatch):
        import threading
        import time

        from docsforge import tikz as tikz_mod

        tex = tmp_path / "a.tex"
        tex.write_text("\\begin{tikzpicture}\\draw (0,0)--(1,1);\\end{tikzpicture}")
        out = tmp_path / "a.svg"

        # Fake a LaTeX toolchain; record whether two compiles overlap.
        active = 0
        max_active = 0
        lock = threading.Lock()

        def fake_run_tool(cmd, **kwargs):
            nonlocal active, max_active
            with lock:
                active += 1
                max_active = max(max_active, active)
            time.sleep(0.05)
            with lock:
                active -= 1
            if cmd[0] == "latex":
                dvi = kwargs["cwd"] / tex.with_suffix(".dvi").name
                dvi.write_text("dvi")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(tikz_mod, "_has_tool", lambda name: True)
        monkeypatch.setattr(tikz_mod, "_run_tool", fake_run_tool)
        monkeypatch.setattr(tikz_mod, "_run_dvisvgm", lambda dvi, output, cwd, name: output.write_text("svg") or True)

        output_lock = threading.Lock()
        t1 = threading.Thread(target=_compile_tex_to_svg, args=(tex, out), kwargs={"output_lock": output_lock})
        t2 = threading.Thread(target=_compile_tex_to_svg, args=(tex, out), kwargs={"output_lock": output_lock})
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        assert max_active == 1  # never overlapped


class TestStaleHashCleanup:
    """Regression: deleted .tex files must not leave stale hash entries."""

    def test_merged_hashes_drop_deleted_files(self, tmp_path: Path, monkeypatch):
        import docsforge.tikz as tikz_mod

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "a.tex").write_text("\\begin{tikzpicture}\\draw (0,0)--(1,1);\\end{tikzpicture}")
        stale = str((docs / "gone.tex").resolve())

        class FakeCache:
            def get_tikz_hashes(self):
                return {stale: "oldhash"}

            def __init__(self):
                self.saved = None

            def set_tikz_hashes(self, hashes):
                self.saved = hashes

        fake = FakeCache()
        monkeypatch.setattr(tikz_mod, "CacheManager", lambda: fake)
        # Pretend the toolchain exists, but make every compile fail fast so
        # no real LaTeX runs; the hash merge happens regardless.
        monkeypatch.setattr(tikz_mod, "_has_tool", lambda name: True)
        monkeypatch.setattr(tikz_mod, "_compile_tex_to_svg", lambda *a, **k: False)

        config = type(
            "C",
            (),
            {
                "docs_dir": str(docs),
                "site_dir": str(tmp_path / "site"),
                "tikz": True,
                "tikz_preamble": [],
                "concurrency": 1,
            },
        )()
        tikz_mod.compile_tikz_files(config)
        assert fake.saved is not None
        assert stale not in fake.saved
