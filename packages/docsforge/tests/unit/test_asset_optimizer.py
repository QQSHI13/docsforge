"""Unit tests for docsforge.asset_optimizer helpers."""
from __future__ import annotations

import pytest

from docsforge.asset_optimizer import (
    _AssetReferenceParser,
    _find_referenced_assets,
    _normalize_asset_url,
)


class TestNormalizeAssetUrl:
    def test_external_urls_return_none(self):
        for url in (
            'https://example.com/x.css',
            'http://example.com/x.css',
            '//example.com/x.css',
            'data:image/png;base64,abc',
            'mailto:a@b.com',
            '#anchor',
        ):
            assert _normalize_asset_url(url, '') is None

    def test_absolute_path(self):
        assert _normalize_asset_url('/assets/style.css', 'any') == 'assets/style.css'

    def test_relative_path(self):
        assert _normalize_asset_url('style.css', 'assets/stylesheets') == 'assets/stylesheets/style.css'

    def test_query_and_fragment_stripped(self):
        assert _normalize_asset_url('icon.svg?v=1#x', '') == 'icon.svg'

    def test_parent_directory_escape_returns_none(self):
        assert _normalize_asset_url('../../../etc/passwd', 'assets/stylesheets') is None


class TestAssetReferenceParser:
    def test_quoted_href(self):
        p = _AssetReferenceParser()
        p.feed('<link rel="stylesheet" href="assets/style.css">')
        assert 'assets/style.css' in p.refs

    def test_unquoted_src(self):
        p = _AssetReferenceParser()
        p.feed('<script src=app.js></script>')
        assert 'app.js' in p.refs

    def test_img_src(self):
        p = _AssetReferenceParser()
        p.feed('<img src="images/logo.png" alt="logo">')
        assert 'images/logo.png' in p.refs

    def test_svg_image_href(self):
        p = _AssetReferenceParser()
        p.feed('<svg><image href="icons/a.svg"></image></svg>')
        assert 'icons/a.svg' in p.refs

    def test_data_attribute_with_asset(self):
        p = _AssetReferenceParser()
        p.feed('<div data-icon="icons/home.svg">x</div>')
        assert 'icons/home.svg' in p.refs

    def test_data_attribute_non_asset_ignored(self):
        p = _AssetReferenceParser()
        p.feed('<div data-id="123">x</div>')
        assert '123' not in p.refs


class TestFindReferencedAssets:
    def test_html_css_and_js_references(self, tmp_path):
        site = tmp_path / "site"
        site.mkdir()
        (site / "index.html").write_text(
            '<html><head><link rel="stylesheet" href="assets/style.css">'
            '</head><body><img src="images/logo.png"><script src="app.js"></script>'
            '</body></html>'
        )
        css_dir = site / "assets"
        css_dir.mkdir()
        (css_dir / "style.css").write_text(
            "@import url('fonts/font.woff2');\n"
            ".x { background: url(../images/bg.png); }"
        )
        js_dir = site / "assets" / "javascripts"
        js_dir.mkdir(parents=True)
        (js_dir / "app.js").write_text(
            'const url = "workers/search.js";'
        )
        img_dir = site / "images"
        img_dir.mkdir()
        (img_dir / "logo.png").write_text("png")
        (img_dir / "bg.png").write_text("png")

        refs = _find_referenced_assets(str(site))
        assert 'assets/style.css' in refs
        assert 'images/logo.png' in refs
        assert 'app.js' in refs
        assert 'assets/fonts/font.woff2' in refs
        assert 'images/bg.png' in refs
        assert 'assets/javascripts/workers/search.js' in refs

    def test_external_urls_ignored(self, tmp_path):
        site = tmp_path / "site"
        site.mkdir()
        (site / "index.html").write_text(
            '<script src="https://cdn.example.com/app.js"></script>'
        )
        refs = _find_referenced_assets(str(site))
        assert 'https://cdn.example.com/app.js' not in refs
