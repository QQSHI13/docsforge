"""Unit tests for the i18n plugin (docsforge.core.i18n)."""
from __future__ import annotations

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


class TestLocaleSiblingDestUri:
    def test_directory_url_homepage(self, plugin):
        f = SimpleNamespace(dest_uri="index.html", use_directory_urls=True)
        assert plugin._locale_sibling_dest_uri(f, "zh") == "index.zh.html"

    def test_directory_url_nested_page(self, plugin):
        f = SimpleNamespace(dest_uri="page/index.html", use_directory_urls=True)
        assert plugin._locale_sibling_dest_uri(f, "zh") == "page/index.zh.html"

    def test_file_url_homepage(self, plugin):
        f = SimpleNamespace(dest_uri="index.html", use_directory_urls=False)
        assert plugin._locale_sibling_dest_uri(f, "zh") == "index.zh.html"

    def test_file_url_nested_page(self, plugin):
        f = SimpleNamespace(dest_uri="page.html", use_directory_urls=False)
        assert plugin._locale_sibling_dest_uri(f, "zh") == "page.zh.html"


class TestGetAlternates:
    def test_alternates_share_locale_agnostic_url(self, plugin):
        page = SimpleNamespace(url="page/")
        alts = plugin._get_alternates(page)
        locales = {a["locale"] for a in alts}
        urls = {a["url"] for a in alts}
        assert locales == {"en", "zh"}
        assert urls == {"page/"}

    def test_alternates_handle_homepage_url(self, plugin):
        page = SimpleNamespace(url="./")
        alts = plugin._get_alternates(page)
        assert all(a["url"] == "./" for a in alts)


class TestMakeLanguageFile:
    def test_sibling_shares_default_url(self, plugin):
        default = SimpleNamespace(
            src_uri="index.md",
            src_dir="docs",
            dest_dir="site",
            use_directory_urls=True,
            dest_uri="index.html",
            url="./",
            inclusion=SimpleNamespace(is_included=lambda: True),
        )
        translated = SimpleNamespace(
            src_uri="index.zh.md",
            src_dir="docs",
            dest_dir="site",
            use_directory_urls=True,
            inclusion=SimpleNamespace(is_included=lambda: True),
        )

        lang_file = plugin._make_language_file({}, translated, "zh", default)
        assert lang_file.url == "./"
        assert lang_file.dest_uri == "index.zh.html"
        assert lang_file.i18n_locale == "zh"

    def test_sibling_shares_default_stem(self, plugin):
        from docsforge.files import File
        from docsforge.pages import Page

        default = File(
            path="setup/index.md",
            src_dir="docs",
            dest_dir="site",
            use_directory_urls=True,
        )
        translated = File(
            path="setup/index.zh.md",
            src_dir="docs",
            dest_dir="site",
            use_directory_urls=True,
        )
        lang_file = plugin._make_language_file({}, translated, "zh", default)
        # Translated index pages keep the base file's stem identity so they
        # are treated as index pages (tab icons, section indexes, sorting).
        assert lang_file.name == "index"
        page = Page(None, lang_file, {})
        assert page.is_index

    def test_self_referential_base_file_does_not_recurse(self, plugin):
        from docsforge.files import File

        f = File(
            path="index.md",
            src_dir="docs",
            dest_dir="site",
            use_directory_urls=True,
        )
        f.i18n_base_file = f
        assert f.name == "index"


class TestOnFiles:
    def test_translation_emitted_as_sibling(self, plugin):
        from docsforge.files import File, Files, InclusionLevel

        files = Files([])
        default = File(
            path="index.md",
            src_dir="docs",
            dest_dir="site",
            use_directory_urls=True,
        )
        default.dest_uri = "index.html"
        default.url = "./"
        default.inclusion = InclusionLevel.INCLUDED
        zh = File(
            path="index.zh.md",
            src_dir="docs",
            dest_dir="site",
            use_directory_urls=True,
        )
        zh.dest_uri = "index.zh.html"
        zh.url = "./"
        zh.inclusion = InclusionLevel.INCLUDED
        files.append(default)
        files.append(zh)

        out = plugin.on_files(files, config={})
        by_dest = {f.dest_uri: f for f in out.documentation_pages()}
        assert "index.html" in by_dest
        assert "index.zh.html" in by_dest
        # Sibling translations share the locale-agnostic public URL.
        assert by_dest["index.html"].url == "./"
        assert by_dest["index.zh.html"].url == "./"


class TestOnPageContext:
    def test_sets_locale_nav_and_base_url(self, plugin):
        from docsforge.files import File
        from docsforge.nav import Navigation, Page

        default = File(
            path="index.md",
            src_dir="docs",
            dest_dir="site",
            use_directory_urls=True,
        )
        default.dest_uri = "index.html"
        default.url = "./"
        default.i18n_locale = "zh"
        default.i18n_base_file = default
        page = Page("Home", default, {"site_url": "https://example.com/docs/"})
        nav = Navigation([], [page])
        plugin.on_nav(nav, config={"site_url": "https://example.com/docs/"}, files=[])

        context = {"nav": nav}
        config = {"site_url": "https://example.com/docs/", "extra": {}}
        plugin.on_page_context(context, page=page, config=config, nav=nav)
        assert context["i18n_base_url"] == "/docs/"


class TestOnPageContent:
    def test_sets_page_locale_and_alternates(self, plugin):
        from docsforge.files import File
        from docsforge.pages import Page

        default = File(
            path="index.md",
            src_dir="docs",
            dest_dir="site",
            use_directory_urls=True,
        )
        default.dest_uri = "index.html"
        default.url = "./"
        default.i18n_locale = "zh"
        default.i18n_base_file = default
        page = Page("Home", default, {})
        plugin.on_page_content("<p>hello</p>", page=page, config={}, files=[])
        assert page.i18n_locale == "zh"
        assert {a["locale"] for a in page.i18n_alternates} == {"en", "zh"}
