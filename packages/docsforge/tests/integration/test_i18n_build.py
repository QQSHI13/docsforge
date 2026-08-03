"""Integration tests for the i18n plugin end-to-end build."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from docsforge.config_base import load_config
from docsforge.build import build

pytestmark = pytest.mark.slow


def _build_i18n_site(tmp_path: Path) -> Path:
    docs = tmp_path / "docs"
    docs.mkdir()
    assets = docs / "assets"
    assets.mkdir()
    (docs / "index.md").write_text(
        "---\ntitle: Home\n---\n# Home\n\n[Second](second.md)\n\n"
        "[Fallback](fallback.md)\n\n"
        "![Diagram](assets/diagram.png)\n\n![Other](assets/other.png)\n"
    )
    (docs / "index.zh.md").write_text(
        "---\ntitle: 首页\n---\n# 首页\n\n[第二页](second.md)\n\n"
        "[Fallback](fallback.md)\n\n"
        "![Diagram](assets/diagram.png)\n\n![Other](assets/other.png)\n"
    )
    (docs / "second.md").write_text("---\ntitle: Second\n---\n# Second\n")
    (docs / "second.zh.md").write_text("---\ntitle: 第二页\n---\n# 第二页\n")
    (docs / "fallback.md").write_text("---\ntitle: Fallback\n---\n# Fallback\n")
    (assets / "diagram.png").write_text("default-diagram")
    (assets / "diagram.zh.png").write_text("zh-diagram")
    (assets / "other.png").write_text("default-other")

    config = {
        "site_name": "I18n Test",
        "docs_dir": "docs",
        "site_url": "https://example.com/",
        "theme": {"name": "material"},
        "nav": ["index.md", {"Custom Second Title": "second.md"}, "fallback.md"],
        "extra": {
            "i18n_languages": [
                {"locale": "en", "name": "English", "default": True},
                {
                    "locale": "zh",
                    "name": "中文",
                    "nav_translations": {"Home": "主页", "Fallback": "回退页"},
                },
            ]
        },
    }
    import yaml

    (tmp_path / "docsforge.yml").write_text(yaml.safe_dump(config))

    cfg = load_config(config_file=str(tmp_path / "docsforge.yml"))
    cfg.plugins.on_startup(command="build", dirty=True)
    try:
        build(cfg, dirty=True)
    finally:
        cfg.plugins.on_shutdown()
    return tmp_path / "site"


class TestI18nBuild:
    def test_creates_default_and_locale_pages(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        assert (site / "index.html").is_file()
        assert (site / "second" / "index.html").is_file()
        assert (site / "zh" / "index.html").is_file()
        assert (site / "zh" / "second" / "index.html").is_file()

    def test_creates_locale_search_index_and_sitemap(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        assert (site / "search" / "search_index.json").is_file()
        assert (site / "zh" / "search" / "search_index.json").is_file()
        assert (site / "zh" / "sitemap.xml").is_file()
        assert (site / "zh" / "sitemap.xml.gz").is_file()

    def test_content_links_point_to_locale_pages(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        html = (site / "zh" / "index.html").read_text()
        # The link should stay inside the zh subtree, not climb out to /second/.
        assert re.search(r'<a[^>]+href="second/"[^>]*>第二页</a>', html) or \
               re.search(r'<a[^>]+href=second/[^>]*>第二页</a>', html)

    def test_emits_alternate_head_links(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        html = (site / "zh" / "index.html").read_text()
        assert 'hreflang=en' in html
        assert 'hreflang=zh' in html

    def test_emits_language_switcher(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        html = (site / "zh" / "index.html").read_text()
        assert "English" in html
        assert "中文" in html

    def test_translated_asset_copied_to_locale(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        assert (site / "assets" / "diagram.png").read_text() == "default-diagram"
        assert (site / "zh" / "assets" / "diagram.png").read_text() == "zh-diagram"
        # The suffixed source file should not be emitted at the site root.
        assert not (site / "assets" / "diagram.zh.png").exists()

    def test_fallback_asset_copied_to_locale(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        assert (site / "assets" / "other.png").read_text() == "default-other"
        assert (site / "zh" / "assets" / "other.png").read_text() == "default-other"

    def test_locale_asset_links_rewritten(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        html = (site / "zh" / "index.html").read_text()
        # Both images should reference the locale copy, not climb out to the root.
        assert re.search(r'<img[^>]+src=["\']?assets/diagram\.png["\'\s>]', html)
        assert re.search(r'<img[^>]+src=["\']?assets/other\.png["\'\s>]', html)

    def test_translated_pages_not_emitted_at_root(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        # Translated source files must not produce root-level pages or assets.
        assert not (site / "index.zh.html").exists()
        assert not (site / "second.zh.html").exists()
        assert not (site / "assets" / "diagram.zh.png").exists()

    def test_no_nav_warning_for_translated_pages(self, tmp_path, caplog):
        import logging

        with caplog.at_level(logging.INFO):
            _build_i18n_site(tmp_path)
        assert "exist in the docs directory, but are not included" not in caplog.text

    def test_locale_pages_use_matching_ui_language(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        en_html = (site / "index.html").read_text()
        zh_html = (site / "zh" / "index.html").read_text()

        # <html lang> should follow the page locale.
        assert re.search(r'<html[^>]+lang=en[\s>]', en_html)
        assert re.search(r'<html[^>]+lang=zh[\s>]', zh_html)

        # Theme UI strings should be in the page language (minified HTML may drop quotes).
        assert re.search(r'aria-label=["\']?Select language[\s>"\']', en_html)
        assert re.search(r'aria-label=["\']?选择当前语言[\s>"\']', zh_html)

    def test_translated_page_overrides_default_nav_title(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        zh_html = (site / "zh" / "index.html").read_text()
        # second.zh.md has its own frontmatter title; it should override the
        # default-language nav title configured for second.md.
        assert "Custom Second Title" not in zh_html
        assert "第二页" in zh_html

    def test_fallback_page_links_use_locale_path(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        zh_html = (site / "zh" / "index.html").read_text()
        # Link to the fallback page should stay inside the zh subtree.
        assert re.search(r'<a[^>]+href=["\']?fallback/["\'\s>]', zh_html)

    def test_locale_nav_uses_nav_translations_for_pages(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        zh_html = (site / "zh" / "index.html").read_text()
        # nav_translations should apply to Page nav items, not just Sections.
        assert "主页" in zh_html
        assert "回退页" in zh_html

    def test_locale_nav_uses_translated_frontmatter_title(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        zh_html = (site / "zh" / "index.html").read_text()
        # second.zh.md has title "第二页"; the nav should show it (no override).
        assert "第二页" in zh_html

    def test_locale_homepage_logo_stays_in_locale(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        html = (site / "zh" / "second" / "index.html").read_text()
        # The header/nav logo links should point into the zh subtree, not to the root.
        logo_hrefs = re.findall(
            r'<a\b[^>]*?\sdata-md-component=["\']?logo["\']?[^>]*?\shref=([^\s>]+)',
            html,
            flags=re.IGNORECASE,
        )
        logo_hrefs += re.findall(
            r'<a\b[^>]*?\shref=([^\s>]+)[^>]*?\sdata-md-component=["\']?logo["\']?',
            html,
            flags=re.IGNORECASE,
        )
        assert logo_hrefs
        for href in logo_hrefs:
            href = href.strip('"').strip("'")
            # Must stay inside the locale (contains zh/) or be a self-link.
            assert "zh/" in href or href in (".", "./")
            assert not href.startswith("../../assets")

    def test_locale_alternate_links_keep_trailing_slash(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        html = (site / "zh" / "index.html").read_text()
        # The default-language alternate from a locale page should be a directory URL.
        assert re.search(r'<link[^>]+rel=["\']?alternate["\']?[^>]*href=["\']?\.\./["\'\s>]', html) or \
               re.search(r'<link[^>]+href=["\']?\.\./["\'\s>][^>]*rel=["\']?alternate["\']?', html)

    def test_language_switcher_on_fallback_page(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        html = (site / "zh" / "fallback" / "index.html").read_text()
        # Fallback pages must still expose alternates so the switcher is rendered.
        assert "English" in html
        assert "中文" in html


def _build_i18n_site_without_frontmatter_titles(tmp_path: Path) -> Path:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.md").write_text("# Home\n\nWelcome.\n")
    (docs / "index.zh.md").write_text("# 首页\n\n欢迎.\n")
    (docs / "second.md").write_text("# Second Page\n\nPage 2.\n")
    (docs / "second.zh.md").write_text("# 第二页\n\n第二页.\n")

    config = {
        "site_name": "I18n Test",
        "docs_dir": "docs",
        "site_url": "https://example.com/",
        "theme": {"name": "material"},
        "nav": ["index.md", "second.md"],
        "extra": {
            "i18n_languages": [
                {"locale": "en", "name": "English", "default": True},
                {"locale": "zh", "name": "中文"},
            ]
        },
    }
    import yaml

    (tmp_path / "docsforge.yml").write_text(yaml.safe_dump(config))

    cfg = load_config(config_file=str(tmp_path / "docsforge.yml"))
    cfg.plugins.on_startup(command="build", dirty=True)
    try:
        build(cfg, dirty=True)
    finally:
        cfg.plugins.on_shutdown()
    return tmp_path / "site"


class TestI18nNoFrontmatterTitles:
    def test_no_none_in_nav_titles(self, tmp_path):
        site = _build_i18n_site_without_frontmatter_titles(tmp_path)
        for rel in ["zh/index.html", "zh/second/index.html"]:
            html = (site / rel).read_text()
            assert "None" not in html
            nav_match = re.search(
                r'<nav\b[^>]*?class=["\']?md-nav[^>]*?>.*?</nav>',
                html,
                re.S | re.IGNORECASE,
            )
            assert nav_match
            nav_html = nav_match.group(0)
            # Both the English and Chinese H1-derived titles should appear in nav.
            assert "Home" in nav_html or "首页" in nav_html
            assert "Second Page" in nav_html or "第二页" in nav_html
