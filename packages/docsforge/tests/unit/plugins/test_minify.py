"""Unit tests for the minify plugin (docsforge.core.minify)."""
from __future__ import annotations

from pathlib import Path

import pytest

from docsforge.core.minify import MinifyPlugin, MINIFIERS


class TestMinifyPlugin:
    def test_has_minifiers_for_js_and_css(self):
        # HTML is minified via minify_html directly, not via MINIFIERS.
        assert "js" in MINIFIERS
        assert "css" in MINIFIERS

    def test_minify_js_removes_comments(self):
        plugin = MinifyPlugin()
        out = plugin._minify_file_data_with_func(
            "// a comment\nvar x = 1; // trailing\n", MINIFIERS["js"]
        )
        assert "comment" not in out
        assert "var x=1" in out

    def test_minify_css_strips_comments_and_whitespace(self):
        plugin = MinifyPlugin()
        out = plugin._minify_file_data_with_func(
            "/* a */ body { color : red ; }", MINIFIERS["css"]
        )
        assert "/* a */" not in out
        assert "red" in out

    def test_minify_html_page_strips_comments(self):
        # _minify_html_page uses the minify_html library directly.
        plugin = MinifyPlugin()
        out = plugin._minify_html_page("<div>\n  <p>hi</p>  <!-- c -->\n</div>")
        assert out is not None
        assert "hi" in out
        assert "<!-- c -->" not in out


class TestExtraPathValidation:
    """Extra CSS/JS paths must stay inside docs_dir and site_dir."""

    @pytest.fixture()
    def plugin(self):
        return MinifyPlugin()

    def test_traversal_outside_docs_dir_is_skipped(self, plugin: MinifyPlugin, tmp_path: Path):
        docs = tmp_path / "docs"
        site = tmp_path / "site"
        docs.mkdir()
        site.mkdir()
        # A valid-looking file placed outside docs_dir must not be read.
        outside = tmp_path / "secret.js"
        outside.write_text("var secret = 1;")

        class Cfg:
            def __init__(self):
                self.docs_dir = str(docs)
                self.site_dir = str(site)
                self.extra_javascript = ["../secret.js"]
                self.extra_css = []

            def get(self, key, default=None):
                return getattr(self, key, default)

            def __getitem__(self, key):
                return getattr(self, key)

        plugin._process_extras("js", Cfg())
        assert "../secret.js" not in plugin._pending_minified

    def test_traversal_outside_site_dir_is_not_written(self, plugin: MinifyPlugin, tmp_path: Path):
        docs = tmp_path / "docs"
        site = tmp_path / "site"
        docs.mkdir()
        site.mkdir()
        (docs / "app.js").write_text("var x = 1;")

        plugin._pending_minified["../escape.js"] = "var x = 1;"
        plugin.on_post_build(config={"site_dir": str(site)})
        assert not (tmp_path / "escape.js").exists()
