"""Targeted tests for the docsforge/templates/base.html fixes.

These tests inspect the template source and the asset manifest helpers so they
would fail before the fixes (hard-coded hashes, document-wide MutationObserver,
undebounced prefetch) and pass after.
"""
from __future__ import annotations

from pathlib import Path

import pytest

import docsforge
from docsforge.templates import asset_url, build_asset_manifest
from docsforge.theme import Theme


BASE_HTML = Path(docsforge.__file__).parent / "templates" / "base.html"


@pytest.fixture()
def base_html() -> str:
    return BASE_HTML.read_text(encoding="utf-8")


class TestAssetUrl:
    def test_fallback_returns_assets_prefix(self):
        assert asset_url("stylesheets/main.min.css") == "assets/stylesheets/main.min.css"

    def test_manifest_lookup_returns_concrete_path(self):
        manifest = {"stylesheets/main.min.css": "assets/stylesheets/main.12345678.min.css"}
        assert asset_url("stylesheets/main.min.css", manifest) == "assets/stylesheets/main.12345678.min.css"

    def test_missing_logical_name_returns_fallback(self):
        manifest: dict[str, str] = {}
        assert asset_url("stylesheets/main.min.css", manifest) == "assets/stylesheets/main.min.css"


class TestBuildAssetManifest:
    def test_strips_content_hash_from_minified_files(self, tmp_path: Path):
        stylesheets = tmp_path / "assets" / "stylesheets"
        stylesheets.mkdir(parents=True)
        (stylesheets / "main.484c7ddc.min.css").write_text("/* css */")
        (stylesheets / "palette.ab4e12ef.min.css").write_text("/* css */")
        (stylesheets / "pygments.css").write_text("/* css */")

        manifest = build_asset_manifest(tmp_path)

        assert manifest["stylesheets/main.min.css"] == "assets/stylesheets/main.484c7ddc.min.css"
        assert manifest["stylesheets/palette.min.css"] == "assets/stylesheets/palette.ab4e12ef.min.css"
        assert manifest["stylesheets/pygments.css"] == "assets/stylesheets/pygments.css"

    def test_maps_bundle_and_search_worker(self, tmp_path: Path):
        js = tmp_path / "assets" / "javascripts"
        workers = js / "workers"
        workers.mkdir(parents=True)
        (js / "bundle.79ae519e.min.js").write_text("// bundle")
        (workers / "search.2c215733.min.js").write_text("// worker")

        manifest = build_asset_manifest(tmp_path)

        assert manifest["javascripts/bundle.min.js"] == "assets/javascripts/bundle.79ae519e.min.js"
        assert manifest["javascripts/workers/search.min.js"] == "assets/javascripts/workers/search.2c215733.min.js"

    def test_missing_assets_dir_returns_empty_manifest(self, tmp_path: Path):
        assert build_asset_manifest(tmp_path) == {}


class TestBaseHtmlAssets:
    def test_no_hardcoded_hashed_asset_names(self, base_html: str):
        assert "main.484c7ddc.min.css" not in base_html
        assert "palette.ab4e12ef.min.css" not in base_html
        assert "bundle.79ae519e.min.js" not in base_html
        assert "search.2c215733.min.js" not in base_html

    def test_uses_asset_url_for_core_assets(self, base_html: str):
        assert "asset_url('stylesheets/main.min.css')" in base_html
        assert "asset_url('stylesheets/palette.min.css')" in base_html
        assert "asset_url('javascripts/bundle.min.js')" in base_html
        assert "asset_url('javascripts/workers/search.min.js')" in base_html

    def test_asset_url_is_registered_in_theme_environment(self):
        env = Theme(name="material").get_env()
        assert "asset_url" in env.globals
        assert env.globals["asset_url"]("stylesheets/main.min.css") == "assets/stylesheets/main.min.css"


class TestBaseHtmlMutationObserver:
    def test_observer_scoped_to_content_container(self, base_html: str):
        assert "document.documentElement" not in base_html
        assert "document.querySelector('.md-content__inner')" in base_html


class TestBaseHtmlPrefetch:
    def test_prefetch_is_debounced(self, base_html: str):
        assert "var timers = new Map();" in base_html
        assert "setTimeout" in base_html
        assert "clearTimeout" in base_html
        assert "document.addEventListener('mouseout'" in base_html
        assert "document.addEventListener('focusout'" in base_html
