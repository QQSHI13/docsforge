"""Unit tests for docsforge.theme."""
from __future__ import annotations

from types import SimpleNamespace

from docsforge.theme import Theme


class TestRedirectTemplate:
    def _render(self, location: str):
        theme = Theme(name="material")
        env = theme.get_env()
        page = SimpleNamespace(meta={"location": location})
        config = SimpleNamespace(site_name="Test")
        return env.get_template("redirect.html").render(page=page, config=config)

    def test_allows_https_url(self):
        out = self._render("https://example.com/page")
        assert 'url=https://example.com/page' in out
        assert "window.location.replace" in out

    def test_allows_site_relative_path(self):
        out = self._render("/new-location/")
        assert 'url=/new-location/' in out
        assert "window.location.replace" in out

    def test_blocks_javascript_scheme(self):
        out = self._render("javascript:alert(1)")
        assert "http-equiv=\"refresh\"" not in out
        assert "window.location.replace" not in out

    def test_blocks_protocol_relative_url(self):
        out = self._render("//evil.com/")
        assert "http-equiv=\"refresh\"" not in out
        assert "window.location.replace" not in out
