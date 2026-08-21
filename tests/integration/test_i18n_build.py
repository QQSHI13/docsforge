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
        "theme": {"name": "material", "font": False},
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
    def test_creates_default_and_locale_siblings(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        assert (site / "index.html").is_file()
        assert (site / "index.zh.html").is_file()
        assert (site / "second" / "index.html").is_file()
        assert (site / "second" / "index.zh.html").is_file()

    def test_creates_per_locale_search_index_and_single_sitemap(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        assert (site / "search" / "search_index.json").is_file()
        assert (site / "search" / "search_index.zh.json").is_file()
        assert (site / "sitemap.xml").is_file()
        assert (site / "sitemap.xml.gz").is_file()

    def test_content_links_are_locale_agnostic(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        zh_html = (site / "index.zh.html").read_text()
        # Links should stay on the same locale-agnostic URL, not jump to /zh/second/.
        assert re.search(r'<a[^>]+href="second/"[^>]*>第二页</a>', zh_html) or \
               re.search(r'<a[^>]+href=second/[^>]*>第二页</a>', zh_html)

    def test_no_alternate_head_links(self, tmp_path):
        """i18n alternates are deliberately not emitted: suffix-mode locales
        share one locale-agnostic URL, so duplicate <link rel=alternate> entries
        would be invalid HTML and make the bundle's alternate integration fetch
        a per-page sitemap.xml (404s)."""
        site = _build_i18n_site(tmp_path)
        zh_html = (site / "index.zh.html").read_text()
        en_html = (site / "index.html").read_text()
        assert re.search(r'rel=["\']?alternate["\']?', zh_html) is None
        assert re.search(r'rel=["\']?alternate["\']?', en_html) is None

    def test_emits_language_switcher(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        zh_html = (site / "index.zh.html").read_text()
        assert "English" in zh_html
        assert "中文" in zh_html

    def test_assets_not_copied_per_locale(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        assert (site / "assets" / "diagram.png").read_text() == "default-diagram"
        assert (site / "assets" / "diagram.zh.png").read_text() == "zh-diagram"
        assert (site / "assets" / "other.png").read_text() == "default-other"
        # No per-locale asset subtree should exist.
        assert not (site / "zh").is_dir()

    def test_asset_links_not_rewritten_to_locale_subtree(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        zh_html = (site / "index.zh.html").read_text()
        # Assets keep their locale-agnostic paths.
        assert re.search(r'<img[^>]+src=["\']?assets/diagram\.png["\'\s>]', zh_html)
        assert re.search(r'<img[^>]+src=["\']?assets/other\.png["\'\s>]', zh_html)

    def test_translated_pages_emitted_as_siblings(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        # Translations are siblings, not root-level pages under their own URL.
        assert (site / "index.zh.html").is_file()
        assert (site / "second" / "index.zh.html").is_file()
        assert not (site / "second.zh.html").exists()

    def test_no_nav_warning_for_translated_pages(self, tmp_path, caplog):
        import logging

        with caplog.at_level(logging.INFO):
            _build_i18n_site(tmp_path)
        assert "exist in the docs directory, but are not included" not in caplog.text

    def test_locale_pages_use_matching_ui_language(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        en_html = (site / "index.html").read_text()
        zh_html = (site / "index.zh.html").read_text()

        # <html lang> should follow the page locale.
        assert re.search(r'<html[^>]+lang=en[\s>]', en_html)
        assert re.search(r'<html[^>]+lang=zh[\s>]', zh_html)

        # Theme UI strings should be in the page language (minified HTML may drop quotes).
        assert re.search(r'aria-label=["\']?Select language[\s>"\']', en_html)
        assert re.search(r'aria-label=["\']?选择当前语言[\s>"\']', zh_html)

    def test_translated_page_overrides_default_nav_title(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        zh_html = (site / "index.zh.html").read_text()
        # second.zh.md has its own frontmatter title; it should override the
        # default-language nav title configured for second.md.
        assert "Custom Second Title" not in zh_html
        assert "第二页" in zh_html

    def test_locale_nav_uses_nav_translations_for_pages(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        zh_html = (site / "index.zh.html").read_text()
        # nav_translations should apply to Page nav items, not just Sections.
        assert "主页" in zh_html
        assert "回退页" in zh_html

    def test_locale_nav_uses_translated_frontmatter_title(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        zh_html = (site / "index.zh.html").read_text()
        # second.zh.md has title "第二页"; the nav should show it (no override).
        assert "第二页" in zh_html

    def test_locale_homepage_logo_is_locale_agnostic(self, tmp_path):
        site = _build_i18n_site(tmp_path)
        zh_html = (site / "second" / "index.zh.html").read_text()
        # The header/nav logo links should be locale-agnostic, not point into a zh/ subtree.
        logo_hrefs = re.findall(
            r'<a\b[^>]*?\sdata-md-component=["\']?logo["\']?[^>]*?\shref=([^\s>]+)',
            zh_html,
            flags=re.IGNORECASE,
        )
        logo_hrefs += re.findall(
            r'<a\b[^>]*?\shref=([^\s>]+)[^>]*?\sdata-md-component=["\']?logo["\']?',
            zh_html,
            flags=re.IGNORECASE,
        )
        assert logo_hrefs
        for href in logo_hrefs:
            href = href.strip('"').strip("'")
            assert "zh/" not in href

    def test_config_alternates_still_emitted(self, tmp_path):
        """config.extra.alternate (version alternates) are still emitted as
        <link rel=alternate>; only the per-locale i18n alternates were removed."""
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "index.md").write_text("---\ntitle: Home\nicon: material/home\n---\n# Home\n")
        (docs / "index.zh.md").write_text("---\ntitle: 首页\nicon: material/home\n---\n# 首页\n")
        config = {
            "site_name": "I18n Test",
            "docs_dir": "docs",
            "site_url": "https://example.com/",
            "theme": {"name": "material", "font": False},
            "nav": ["index.md"],
            "extra": {
                "i18n_languages": [
                    {"locale": "en", "name": "English", "default": True},
                    {"locale": "zh", "name": "中文"},
                ],
                "alternate": [{"link": "https://v1.example.com/", "lang": "en"}],
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

        html = (tmp_path / "site" / "index.html").read_text()
        assert 'href="https://v1.example.com/"' in html
        assert re.search(r'rel=["\']?alternate["\']?', html) is not None


class TestI18nNoFrontmatterTitles:
    def test_no_none_in_nav_titles(self, tmp_path):
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
            "theme": {"name": "material", "font": False},
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

        site = tmp_path / "site"
        for rel in ["index.zh.html", "second/index.zh.html"]:
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


class TestI18nNavIcons:
    """Regression: locale-suffixed pages (index.zh.md) must behave like their
    base page for navigation — tab icons (frontmatter `icon:`) and section
    indexes were silently dropped for translations because File.name keeps
    the locale suffix ('index.zh') and locale-nav sources were read lazily
    in render order."""

    def test_tab_icons_render_for_translated_section_indexes(self, tmp_path):
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "index.md").write_text("---\ntitle: Home\nicon: material/home\n---\n# Home\n")
        (docs / "index.zh.md").write_text("---\ntitle: 首页\nicon: material/home\n---\n# 首页\n")
        setup = docs / "setup"
        setup.mkdir()
        # Section index carries the tab icon; a sibling page renders first so
        # the icon page is NOT the first page rendered by the build.
        (setup / "guide.md").write_text("# Guide\n\nLong guide body.\n" * 40)
        (setup / "guide.zh.md").write_text("# 指南\n\n长指南正文。\n" * 40)
        (setup / "index.md").write_text("---\nicon: material/cog\n---\n# Setup\n")
        (setup / "index.zh.md").write_text("---\nicon: material/cog\n---\n# 设置\n")

        config = {
            "site_name": "I18n Icons",
            "docs_dir": "docs",
            "site_url": "https://example.com/",
            "theme": {
                "name": "material",
                "font": False,
                "features": ["navigation.tabs", "navigation.indexes"],
            },
            "nav": [
                "index.md",
                {"Setup": ["setup/index.md", "setup/guide.md"]},
            ],
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

        site = tmp_path / "site"
        for rel in ("index.html", "index.zh.html"):
            html = (site / rel).read_text()
            tabs = html[html.find("md-tabs__list") : html.find("</ul>", html.find("md-tabs__list"))]
            assert "<svg" in tabs, f"{rel}: no icon in top-bar tabs"
            # Both the Home and the Setup tab must carry an icon.
            assert tabs.count("<svg") >= 2, f"{rel}: expected icons on Home and Setup tabs"
