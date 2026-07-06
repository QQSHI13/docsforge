"""Unit tests for the i18n plugin (docsforge.core.i18n)."""
from __future__ import annotations

import re
from types import SimpleNamespace

import pytest

from docsforge.core.i18n import I18nPlugin


@pytest.fixture
def plugin():
    p = I18nPlugin()
    p.load_config(
        {
            "languages": [
                {"locale": "en", "name": "English", "default": True},
                {"locale": "zh", "name": "中文"},
            ]
        }
    )
    p.on_config({})
    return p


class TestParseFile:
    def test_default_locale_file_returns_unchanged(self, plugin):
        assert plugin._parse_file("index.md") == ("index.md", "en")
        assert plugin._parse_file("guide/intro.md") == ("guide/intro.md", "en")

    def test_suffixed_file_returns_locale_and_base_key(self, plugin):
        assert plugin._parse_file("index.zh.md") == ("index.md", "zh")
        assert plugin._parse_file("guide/intro.zh.md") == ("guide/intro.md", "zh")

    def test_unknown_suffix_treated_as_default(self, plugin):
        assert plugin._parse_file("index.fr.md") == ("index.fr.md", "en")


class TestRewriteLinks:
    def test_rewrites_internal_links_to_same_locale(self):
        p = I18nPlugin()
        p._locale_url_maps = {
            "zh": {
                "": "zh/",
                "second/": "zh/second/",
                "guide/intro/": "zh/guide/intro/",
            }
        }
        page = SimpleNamespace(url="zh/")
        html = '<p><a href="second/">Second</a> <a href="guide/intro/">Intro</a></p>'
        out = p._rewrite_links(html, page, "zh")
        assert 'href="second/"' in out
        assert 'href="guide/intro/"' in out

    def test_preserves_external_and_anchor_links(self):
        p = I18nPlugin()
        p._locale_url_maps = {"zh": {"second/": "zh/second/"}}
        page = SimpleNamespace(url="zh/")
        html = (
            '<p><a href="https://example.com">External</a> '
            '<a href="#anchor">Anchor</a> '
            '<a href="mailto:a@b.com">Mail</a></p>'
        )
        out = p._rewrite_links(html, page, "zh")
        assert 'href="https://example.com"' in out
        assert 'href="#anchor"' in out
        assert 'href="mailto:a@b.com"' in out

    def test_preserves_link_anchors_after_rewrite(self):
        p = I18nPlugin()
        p._locale_url_maps = {"zh": {"second/": "zh/second/"}}
        page = SimpleNamespace(url="zh/")
        html = '<p><a href="second/#section">Section</a></p>'
        out = p._rewrite_links(html, page, "zh")
        assert 'href="second/#section"' in out

    def test_rewrites_relative_links_from_nested_page(self):
        p = I18nPlugin()
        p._locale_url_maps = {
            "zh": {
                "": "zh/",
                "second/": "zh/second/",
            }
        }
        page = SimpleNamespace(url="zh/guide/intro/")
        html = '<p><a href="../../second/">Second</a> <a href="../../">Home</a></p>'
        out = p._rewrite_links(html, page, "zh")
        assert 'href="../../second/"' in out
        assert 'href="../../"' in out
