"""Unit tests for the privacy plugin's pure helpers (docsforge.core.privacy).

The network-touching download path is covered via mocked requests; the rest
of the plugin's link-replacement and path-normalization logic is pure string
work and is tested directly.
"""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import pytest

from docsforge.core import privacy as privacy_mod
from docsforge.core.privacy import PrivacyPlugin
from docsforge.exceptions import PluginError


class TestFragmentParser:
    """The streaming HTML fragment parser (replaces lxml to save image size)."""

    def test_parses_simple_tag_with_attrs(self):
        from docsforge.core.privacy import FragmentParser

        p = FragmentParser()
        p.feed('<link href="style.css" rel="stylesheet">')
        el = p.result
        assert el is not None
        assert el.tag == "link"
        assert el.get("href") == "style.css"
        assert el.get("rel") == "stylesheet"

    def test_self_closing_img(self):
        from docsforge.core.privacy import FragmentParser

        p = FragmentParser()
        p.feed('<img src="x.png" alt="x">')
        assert p.result.tag == "img"
        assert p.result.get("src") == "x.png"

    def test_handles_unquoted_attrs(self):
        # Material theme emits unquoted attributes; parser must tolerate them
        from docsforge.core.privacy import FragmentParser

        p = FragmentParser()
        p.feed("<script src=app.js></script>")
        assert p.result.tag == "script"
        assert p.result.get("src") == "app.js"


class TestExtensions:
    def test_known_mime_types_mapped(self):
        assert privacy_mod.extensions["text/css"] == ".css"
        assert privacy_mod.extensions["application/javascript"] == ".js"
        assert privacy_mod.extensions["image/svg+xml"] == ".svg"
        assert privacy_mod.extensions["image/png"] == ".png"

    def test_all_extensions_start_with_dot(self):
        for ext in privacy_mod.extensions.values():
            assert ext.startswith(".")


class TestPrivacyConfig:
    def test_defaults(self):
        from docsforge.config_defaults import DEFAULT_CONCURRENCY
        from docsforge.core.privacy import PrivacyConfig

        cfg = PrivacyConfig()
        cfg.load_dict({})
        cfg.validate()
        assert cfg["enabled"] is True
        # concurrency is now a global setting, not a plugin option.
        assert "concurrency" not in cfg
        assert DEFAULT_CONCURRENCY >= 1


class TestPathSanitization:
    """External URL paths must not traverse the local cache directory."""

    @pytest.fixture()
    def plugin(self, tmp_path: Path):
        p = PrivacyPlugin()
        p.load_config({"cache_dir": str(tmp_path / "cache")})
        return p

    def test_path_from_url_strips_leading_slash(self, plugin: PrivacyPlugin):
        url = urlparse("https://example.com/assets/style.css")
        assert plugin._path_from_url(url) == "example.com/assets/style.css"

    def test_path_from_url_rejects_traversal(self, plugin: PrivacyPlugin):
        url = urlparse("https://example.com/../../etc/passwd")
        with pytest.raises(PluginError):
            plugin._path_from_url(url)

    def test_path_from_url_preserves_leading_dot_dir(self, plugin: PrivacyPlugin):
        """Leading dot segments like .icons must not be rewritten to _icons."""
        url = urlparse("https://example.com/.icons/foo.svg")
        assert ".icons" in plugin._path_from_url(url)

    def test_path_to_file_rejects_escaping_cache_dir(self, plugin: PrivacyPlugin):
        with pytest.raises(PluginError):
            plugin._path_to_file("../../../etc/passwd", None)  # type: ignore[arg-type]
