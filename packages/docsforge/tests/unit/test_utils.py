"""Unit tests for docsforge.utils — small helpers used everywhere."""
from __future__ import annotations

from docsforge import utils


class TestGetRelativeUrl:
    def test_same_dir_returns_dot(self):
        assert utils.get_relative_url("page/", ".") in ("./", "..", "../")

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
