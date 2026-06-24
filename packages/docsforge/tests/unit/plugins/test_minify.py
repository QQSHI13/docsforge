"""Unit tests for the minify plugin (docsforge.core.minify)."""
from __future__ import annotations

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
        assert "var x=1" in out or "x" in out

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
