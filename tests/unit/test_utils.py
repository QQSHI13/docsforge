"""Unit tests for docsforge.utils — small helpers used everywhere."""
from __future__ import annotations

import os
from importlib.metadata import EntryPoint

from docsforge import utils


class TestGetThemeDir:
    def test_builtin_material_returns_templates_dir(self):
        theme_dir = str(utils.get_theme_dir("material"))
        assert os.path.basename(theme_dir) == "templates"
        assert os.path.exists(os.path.join(theme_dir, "base.html"))

    def test_resolves_theme_by_entry_point(self, tmp_path, monkeypatch):
        pkg = tmp_path / "mytheme"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        monkeypatch.syspath_prepend(str(tmp_path))

        ep = EntryPoint(name="mytheme", value="mytheme", group="docsforge.themes")
        monkeypatch.setattr(utils, "entry_points", lambda group: [ep])
        utils.get_themes.cache_clear()
        try:
            assert utils.get_theme_dir("mytheme") == str(pkg)
        finally:
            utils.get_themes.cache_clear()

    def test_unknown_theme_falls_back_to_builtin(self):
        # Names without a registered entry point keep the historical
        # behavior of returning the built-in templates directory.
        theme_dir = str(utils.get_theme_dir("no-such-theme"))
        assert os.path.basename(theme_dir) == "templates"


class TestGetRelativeUrl:
    def test_same_dir_returns_dot(self):
        rel = utils.get_relative_url("page/", ".")
        assert rel == "../"

    def test_subdir_to_root(self):
        # page at a/b/ asking for root -> at least one level up
        url = utils.get_relative_url("a/b/", ".")
        assert url.startswith("..")

    def test_root_to_subdir(self):
        # root asking for a/b/ -> "a/b/"
        assert utils.get_relative_url(".", "a/b/") == "a/b/"


class TestSlugify:
    def test_ascii(self):
        assert utils.slugify("My Docs") == "my-docs"

    def test_strips_punctuation(self):
        assert utils.slugify("Hello, World!") == "hello-world"

    def test_collapses_dashes(self):
        assert utils.slugify("a   b") == "a-b"


class TestNormalizeUrl:
    def test_absolute_url_unchanged(self):
        assert utils.normalize_url("https://example.com/x", "") == "https://example.com/x"

    def test_relative_prefixed_with_base(self):
        out = utils.normalize_url("style.css", "../")
        assert out.endswith("style.css")


class TestWriteFile:
    def test_creates_parent_dirs(self, tmp_path):
        target = tmp_path / "a" / "b" / "c.html"
        utils.write_file(b"hello", str(target))
        assert target.read_bytes() == b"hello"

    def test_overwrites(self, tmp_path):
        target = tmp_path / "f.txt"
        utils.write_file(b"v1", str(target))
        utils.write_file(b"v2", str(target))
        assert target.read_bytes() == b"v2"


class TestGetMarkdownTitle:
    def test_first_h1(self):
        assert utils.get_markdown_title("# Title\n\nbody") == "Title"

    def test_no_title_returns_none(self):
        assert utils.get_markdown_title("just text") is None


class TestBuildDatetime:
    def test_defaults_to_now(self, monkeypatch):
        monkeypatch.delenv("SOURCE_DATE_EPOCH", raising=False)
        from datetime import timezone
        dt = utils.get_build_datetime()
        assert dt.tzinfo == timezone.utc

    def test_honors_source_date_epoch(self, monkeypatch):
        monkeypatch.setenv("SOURCE_DATE_EPOCH", "1700000000")
        dt = utils.get_build_datetime()
        assert int(dt.timestamp()) == 1700000000

    def test_invalid_source_date_epoch_falls_back_to_now(self, monkeypatch):
        monkeypatch.setenv("SOURCE_DATE_EPOCH", "not-a-number")
        from datetime import timezone
        dt = utils.get_build_datetime()
        assert dt.tzinfo == timezone.utc  # didn't crash, fell back


class TestNestPaths:
    def test_flat(self):
        result = utils.nest_paths(["a.md"])
        assert isinstance(result, (list, dict))

    def test_nested_dir(self):
        result = utils.nest_paths(["a/b.md"])
        assert isinstance(result, (list, dict))
