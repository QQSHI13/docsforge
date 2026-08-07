"""Unit tests for the File model and Files collection (docsforge/files.py).

The File -> dest_uri/url mapping is the foundation of the build; getting it
wrong breaks every link in the site, so it deserves direct coverage.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from docsforge.files import File, Files, InclusionLevel


def _file(src_uri: str, docs_dir: str, site_dir: str, dir_urls: bool = True) -> File:
    return File(src_uri, docs_dir, site_dir, dir_urls)


class TestInclusionLevel:
    def test_included_is_in_nav(self):
        assert InclusionLevel.INCLUDED.is_in_nav()
        assert InclusionLevel.INCLUDED.is_included()
        assert not InclusionLevel.INCLUDED.is_excluded()

    def test_excluded_is_not_in_serve(self):
        assert InclusionLevel.EXCLUDED.is_excluded()
        assert not InclusionLevel.EXCLUDED.is_in_serve()
        assert not InclusionLevel.EXCLUDED.is_in_nav()

    def test_draft_is_in_serve_but_not_included(self):
        # draft pages are served (preview) but excluded from the final build
        assert InclusionLevel.DRAFT.is_in_serve()
        assert not InclusionLevel.DRAFT.is_included()
        assert InclusionLevel.DRAFT.is_excluded()

    def test_not_in_nav_is_in_serve(self):
        assert InclusionLevel.NOT_IN_NAV.is_in_serve()
        assert InclusionLevel.NOT_IN_NAV.is_not_in_nav()


class TestFileDestUri:
    """Mapping docs/foo.md -> site/foo/index.html (dir URLs) etc."""

    def test_md_dir_url_becomes_subdir_index(self, tmp_path):
        f = _file("foo.md", str(tmp_path), str(tmp_path / "site"))
        assert f.dest_uri == "foo/index.html"

    def test_index_md_stays_root_index(self, tmp_path):
        f = _file("index.md", str(tmp_path), str(tmp_path / "site"))
        assert f.dest_uri == "index.html"

    def test_nested_md_dir_url(self, tmp_path):
        f = _file("a/b.md", str(tmp_path), str(tmp_path / "site"))
        assert f.dest_uri == "a/b/index.html"

    def test_dir_urls_off_produces_flat_html(self, tmp_path):
        f = _file("foo.md", str(tmp_path), str(tmp_path / "site"), dir_urls=False)
        assert f.dest_uri == "foo.html"

    def test_static_file_keeps_src_uri(self, tmp_path):
        f = _file("assets/logo.png", str(tmp_path), str(tmp_path / "site"))
        assert f.dest_uri == "assets/logo.png"

    def test_readme_md_maps_to_index(self, tmp_path):
        # README.md is treated like index.md
        f = _file("README.md", str(tmp_path), str(tmp_path / "site"))
        assert f.dest_uri == "index.html"


class TestFileUrl:
    def test_dir_url_page_is_dir_slash(self, tmp_path):
        f = _file("foo.md", str(tmp_path), str(tmp_path / "site"))
        assert f.url == "foo/"

    def test_root_index_url_is_dot_slash(self, tmp_path):
        f = _file("index.md", str(tmp_path), str(tmp_path / "site"))
        assert f.url == "./"

    def test_dir_urls_off_url_is_html(self, tmp_path):
        f = _file("foo.md", str(tmp_path), str(tmp_path / "site"), dir_urls=False)
        assert f.url == "foo.html"

    def test_nested_url_preserves_slashes(self, tmp_path):
        f = _file("a/b.md", str(tmp_path), str(tmp_path / "site"))
        assert f.url == "a/b/"

    def test_url_encodes_special_chars_but_preserves_slashes(self, tmp_path):
        f = _file("a b/c d.md", str(tmp_path), str(tmp_path / "site"))
        assert f.url == "a%20b/c%20d/"


class TestFilePaths:
    def test_abs_src_path_joins_src_dir_and_uri(self, tmp_path):
        f = _file("foo.md", str(tmp_path), str(tmp_path / "site"))
        assert f.abs_src_path == os.path.normpath(str(tmp_path / "foo.md"))

    def test_abs_dest_path_joins_dest_dir_and_dest_uri(self, tmp_path):
        f = _file("foo.md", str(tmp_path), str(tmp_path / "site"))
        assert f.abs_dest_path == os.path.normpath(str(tmp_path / "site" / "foo" / "index.html"))

    def test_abs_src_path_none_for_generated_file(self, tmp_path):
        f = File("gen.md", None, str(tmp_path / "site"), True)
        assert f.abs_src_path is None


class TestFileTypePredicates:
    def test_is_documentation_page_md(self, tmp_path):
        assert _file("a.md", *["", ""]).is_documentation_page()
        assert _file("a.markdown", *["", ""]).is_documentation_page()

    def test_is_static_page(self, tmp_path):
        for ext in (".html", ".htm", ".xml", ".json"):
            assert _file("a" + ext, *["", ""]).is_static_page()

    def test_is_media_file(self, tmp_path):
        assert _file("logo.png", *["", ""]).is_media_file()
        assert not _file("page.md", *["", ""]).is_media_file()

    def test_is_javascript(self, tmp_path):
        assert _file("app.js", *["", ""]).is_javascript()
        assert _file("app.mjs", *["", ""]).is_javascript()
        assert not _file("style.css", *["", ""]).is_javascript()


class TestFilesCollection:
    def test_documentation_pages_filters_md(self, tmp_path):
        files = Files([
            _file("a.md", str(tmp_path), str(tmp_path)),
            _file("b.png", str(tmp_path), str(tmp_path)),
        ])
        for f in files:
            f.inclusion = InclusionLevel.INCLUDED
        docs = list(files.documentation_pages())
        assert len(docs) == 1
        assert docs[0].src_uri == "a.md"

    def test_get_file_from_path(self, tmp_path):
        f = _file("a.md", str(tmp_path), str(tmp_path))
        files = Files([f])
        assert files.get_file_from_path("a.md") is f
        assert files.get_file_from_path("missing.md") is None


class TestGetFiles:
    """End-to-end walk of a docs directory."""

    def _config(self, tmp_path, **overrides):
        from docsforge.config_base import load_config

        (tmp_path / "docsforge.yml").write_text(
            "site_name: T\ndocs_dir: docs\nsite_dir: site\nprivacy: false\n"
            "theme:\n  name: material\n  palette:\n    - {scheme: default, primary: teal, accent: teal}\n"
        )
        return load_config(config_file=str(tmp_path / "docsforge.yml"))

    def test_walks_docs_dir_and_returns_all_files(self, tmp_path, monkeypatch):
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "index.md").write_text("# H")
        (docs / "page.md").write_text("# P")
        (docs / "assets").mkdir()
        (docs / "assets" / "logo.png").write_text("png")
        monkeypatch.chdir(tmp_path)
        from docsforge.files import get_files

        files = get_files(self._config(tmp_path))
        uris = {f.src_uri for f in files}
        assert "index.md" in uris
        assert "page.md" in uris
        assert "assets/logo.png" in uris

    def test_readme_skipped_when_index_exists(self, tmp_path, monkeypatch):
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "index.md").write_text("# H")
        (docs / "README.md").write_text("# R")
        monkeypatch.chdir(tmp_path)
        from docsforge.files import get_files

        files = get_files(self._config(tmp_path))
        uris = {f.src_uri for f in files}
        assert "index.md" in uris
        assert "README.md" not in uris



class TestFileGenerated:
    """File.generated must use the public PluginCollection.current_plugin API."""

    def test_generated_uses_public_current_plugin(self):
        """generated_by should come from config.plugins.current_plugin, not the private attr."""
        config = type(
            "Config",
            (),
            {
                "site_dir": "/site",
                "use_directory_urls": True,
                "plugins": type("Plugins", (), {"current_plugin": "my-plugin"})(),
            },
        )()
        f = File.generated(config, "foo.md", content="# Foo")
        assert f.generated_by == "my-plugin"

    def test_generated_falls_back_to_unknown_when_no_current_plugin(self):
        config = type(
            "Config",
            (),
            {
                "site_dir": "/site",
                "use_directory_urls": True,
                "plugins": type("Plugins", (), {"current_plugin": None})(),
            },
        )()
        f = File.generated(config, "foo.md", content="# Foo")
        assert f.generated_by == "<unknown>"


class TestFileRepr:
    """__repr__ must avoid expensive computed properties such as dest_uri and url."""

    def test_repr_does_not_include_dest_uri(self, tmp_path):
        f = _file("foo.md", str(tmp_path), str(tmp_path / "site"))
        r = repr(f)
        assert "dest_uri" not in r
        assert "foo.md" in r

    def test_repr_does_not_compute_dest_uri(self, tmp_path):
        f = _file("foo.md", str(tmp_path), str(tmp_path / "site"))
        repr(f)
        # dest_uri is a cached_property; repr should not populate its cache.
        assert "dest_uri" not in f.__dict__


class TestDeprecatedHelpers:
    def test_sort_files_emits_deprecation_warning(self):
        from docsforge.files import _sort_files

        with pytest.warns(DeprecationWarning, match="_sort_files is soft-deprecated"):
            _sort_files(["b.md", "a.md", "index.md"])
