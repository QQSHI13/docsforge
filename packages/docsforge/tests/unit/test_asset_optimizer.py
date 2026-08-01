"""Unit tests for docsforge.asset_optimizer helpers."""
from __future__ import annotations

import pytest

from docsforge.asset_optimizer import (
    _AssetReferenceParser,
    _find_referenced_assets,
    _normalize_asset_url,
    remove_source_maps,
    remove_unused_font_formats,
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

    def test_img_srcset_with_density_descriptors(self):
        p = _AssetReferenceParser()
        p.feed('<img srcset="images/logo-1x.png 1x, images/logo-2x.png 2x" alt="logo">')
        assert 'images/logo-1x.png' in p.refs
        assert 'images/logo-2x.png' in p.refs

    def test_source_srcset_with_width_descriptors(self):
        p = _AssetReferenceParser()
        p.feed('<source srcset="images/banner-100.jpg 100w, images/banner-200.jpg 200w">')
        assert 'images/banner-100.jpg' in p.refs
        assert 'images/banner-200.jpg' in p.refs

    def test_inline_style_url(self):
        p = _AssetReferenceParser()
        p.feed('<style>.x { background: url(images/bg.png); }</style>')
        assert 'images/bg.png' in p.refs

    def test_inline_style_import(self):
        p = _AssetReferenceParser()
        p.feed("<style>@import url('fonts/font.woff2');</style>")
        assert 'fonts/font.woff2' in p.refs


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


class TestRemoveUnusedFontFormats:
    def test_referenced_legacy_font_is_kept(self, tmp_path):
        site = tmp_path / "site"
        fonts = site / "assets" / "fonts"
        fonts.mkdir(parents=True)
        (fonts / "icons.ttf").write_bytes(b"ttf")
        (fonts / "icons.woff2").write_bytes(b"woff2")
        (site / "index.html").write_text(
            "<style>@font-face { src: url('assets/fonts/icons.ttf'); }</style>"
        )

        remove_unused_font_formats(str(site))

        assert (fonts / "icons.ttf").exists()
        assert (fonts / "icons.woff2").exists()

    def test_unreferenced_legacy_font_is_removed(self, tmp_path):
        site = tmp_path / "site"
        fonts = site / "assets" / "fonts"
        fonts.mkdir(parents=True)
        (fonts / "icons.ttf").write_bytes(b"ttf")
        (fonts / "icons.woff2").write_bytes(b"woff2")
        (site / "index.html").write_text("<html><body>no fonts here</body></html>")

        remove_unused_font_formats(str(site))

        assert not (fonts / "icons.ttf").exists()
        assert (fonts / "icons.woff2").exists()


class TestRemoveSourceMaps:
    def test_strips_source_mapping_url_comment(self, tmp_path):
        site = tmp_path / "site"
        js = site / "assets" / "bundle.js"
        js.parent.mkdir(parents=True)
        js.write_text("console.log(1);\n//# sourceMappingURL=bundle.js.map\n")

        remove_source_maps(str(site))

        assert "sourceMappingURL" not in js.read_text()

    def test_removes_map_files(self, tmp_path):
        site = tmp_path / "site"
        js = site / "assets" / "bundle.js"
        js.parent.mkdir(parents=True)
        js.write_text("console.log(1);\n")
        map_file = site / "assets" / "bundle.js.map"
        map_file.write_text("{}")

        remove_source_maps(str(site))

        assert not map_file.exists()

    def test_skips_unchanged_js_files_on_second_run(self, tmp_path):
        site = tmp_path / "site"
        js = site / "assets" / "bundle.js"
        js.parent.mkdir(parents=True)
        js.write_text("console.log(1);\n//# sourceMappingURL=bundle.js.map\n")
        cache_dir = tmp_path / ".docsforge" / "cache"

        remove_source_maps(str(site), cache_dir=cache_dir)
        stripped = js.read_text()
        assert "sourceMappingURL" not in stripped
        cached_mtime = js.stat().st_mtime

        # Re-run without touching the file: it should be skipped.
        remove_source_maps(str(site), cache_dir=cache_dir)

        assert js.stat().st_mtime == cached_mtime
        assert js.read_text() == stripped

    def test_reprocesses_js_file_when_it_changes(self, tmp_path):
        site = tmp_path / "site"
        js = site / "assets" / "bundle.js"
        js.parent.mkdir(parents=True)
        js.write_text("console.log(1);\n//# sourceMappingURL=bundle.js.map\n")
        cache_dir = tmp_path / ".docsforge" / "cache"

        remove_source_maps(str(site), cache_dir=cache_dir)
        assert "sourceMappingURL" not in js.read_text()

        # File changes (new content / different size).
        js.write_text("console.log(2);\n//# sourceMappingURL=bundle.js.map\n")

        remove_source_maps(str(site), cache_dir=cache_dir)
        assert "sourceMappingURL" not in js.read_text()
