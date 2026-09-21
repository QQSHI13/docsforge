"""Unit tests for the privacy plugin's pure helpers (docsforge.core.privacy).

The network-touching download path is covered via mocked requests; the rest
of the plugin's link-replacement and path-normalization logic is pure string
work and is tested directly.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
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


class _FakeResponse:
    """Minimal stand-in for requests.Response."""

    def __init__(self, status_code=200, headers=None, content=b"", url=""):
        self.status_code = status_code
        self.headers = headers or {}
        self._content = content
        self.url = url
        self.is_redirect = status_code in (301, 302, 303, 307, 308)
        self.is_permanent_redirect = status_code == 301

    def raise_for_status(self):
        import requests

        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}", response=self)

    def iter_content(self, chunk_size=8192):
        yield self._content

    def close(self):
        pass


class TestFetchRedirectValidation:
    """`_fetch` must validate redirects: no scheme downgrade, bounded hops."""

    def _make_file(self, tmp_path: Path, url: str) -> privacy_mod.File:
        cache = tmp_path / "cache"
        target = cache / "example.com" / "app.js"
        target.parent.mkdir(parents=True, exist_ok=True)
        file = privacy_mod.File(
            "example.com/app.js", str(cache), str(tmp_path / "site"), True
        )
        file.url = url
        file.abs_src_path = str(target)
        return file

    def test_https_redirect_downgrade_blocked(self, tmp_path, monkeypatch, caplog):
        plugin = PrivacyPlugin()
        plugin.load_config({"cache_dir": str(tmp_path / "cache")})

        responses = {
            "https://example.com/app.js": _FakeResponse(
                302, {"location": "http://evil.example/app.js"}, url="https://example.com/app.js"
            ),
            "http://evil.example/app.js": _FakeResponse(
                200, {"content-type": "application/javascript"}, b"bad()", url="http://evil.example/app.js"
            ),
        }
        calls = []

        def fake_get(url, **kwargs):
            calls.append(url)
            assert kwargs.get("allow_redirects") is False
            return responses[url]

        monkeypatch.setattr(privacy_mod.requests, "get", fake_get)
        file = self._make_file(tmp_path, "https://example.com/app.js")

        with caplog.at_level("WARNING", logger="docsforge.core.privacy"):
            assert plugin._fetch(file, config=SimpleNamespace()) is False

        # We must never have followed the downgrade to the http:// host.
        assert calls == ["https://example.com/app.js"]

    def test_https_redirect_to_https_allowed(self, tmp_path, monkeypatch):
        plugin = PrivacyPlugin()
        plugin.load_config({"cache_dir": str(tmp_path / "cache")})
        plugin.on_config(SimpleNamespace(site_url="https://example.com/", concurrency=4))

        responses = {
            "https://example.com/app.js": _FakeResponse(
                302, {"location": "https://cdn.example/app.js"}, url="https://example.com/app.js"
            ),
            "https://cdn.example/app.js": _FakeResponse(
                200,
                {"content-type": "application/javascript"},
                b"console.log(1)",
                url="https://cdn.example/app.js",
            ),
        }

        def fake_get(url, **kwargs):
            return responses[url]

        monkeypatch.setattr(privacy_mod.requests, "get", fake_get)
        file = self._make_file(tmp_path, "https://example.com/app.js")
        assert plugin._fetch(file, config=SimpleNamespace()) is True


class TestExcludePatterns:
    """assets_include/exclude match host/path and bare host (fnmatch)."""

    @pytest.fixture()
    def plugin(self, tmp_path):
        from types import SimpleNamespace

        p = PrivacyPlugin()
        p.load_config({"cache_dir": str(tmp_path / "cache")})
        p.on_config(SimpleNamespace(site_url="https://ctf-wiki.org/", concurrency=1))
        return p

    def test_exclude_by_host_glob(self, plugin):
        plugin.config["assets_exclude"] = ["*.clouddn.com"]
        dead = urlparse("http://oayoilchh.bkt.clouddn.com/18-5-3/14928461.jpg")
        assert plugin._is_excluded(dead) is True

    def test_exclude_by_exact_host(self, plugin):
        plugin.config["assets_exclude"] = ["oayoilchh.bkt.clouddn.com"]
        dead = urlparse("http://oayoilchh.bkt.clouddn.com/18-5-3/14928461.jpg")
        assert plugin._is_excluded(dead) is True

    def test_path_patterns_still_work(self, plugin):
        plugin.config["assets_exclude"] = ["*/mathjax/*"]
        url = urlparse("https://cdnjs.loli.net/ajax/libs/mathjax/2.7.2/MathJax.js")
        assert plugin._is_excluded(url) is True

    def test_unmatched_host_is_fetched(self, plugin):
        plugin.config["assets_exclude"] = ["*.clouddn.com"]
        url = urlparse("https://cdnjs.loli.net/ajax/libs/pangu/3.3.0/pangu.min.js")
        assert plugin._is_excluded(url) is False

    def test_include_allowlist_matches_host(self, plugin):
        plugin.config["assets_include"] = ["cdnjs.loli.net"]
        good = urlparse("https://cdnjs.loli.net/ajax/libs/pangu/3.3.0/pangu.min.js")
        bad = urlparse("https://unpkg.com/mermaid@12/dist/mermaid.min.js")
        assert plugin._is_excluded(good) is False
        assert plugin._is_excluded(bad) is True

    def test_same_path_prefix_different_host_not_excluded(self, plugin):
        # A host glob must not match a mere path substring on another host.
        plugin.config["assets_exclude"] = ["oayoilchh.bkt.clouddn.com"]
        url = urlparse("https://example.com/oayoilchh.bkt.clouddn.com/x.jpg")
        assert plugin._is_excluded(url) is False
