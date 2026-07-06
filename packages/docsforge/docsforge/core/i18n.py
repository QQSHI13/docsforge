"""I18n plugin - multi-language documentation support.

Provides mkdocs-static-i18n-style static i18n: add translated files next to
your default-language files (e.g. index.zh.md beside index.md) and DocsForge
builds a default site at root plus one sub-site per language at /<lang>/.
"""

from __future__ import annotations

import gzip
import logging
import os
import posixpath
import re
from copy import copy
from typing import TYPE_CHECKING

from docsforge import templates, utils
from docsforge.config_options import Choice, ListOfItems, Optional, SubConfig, Type
from docsforge.config_base import Config
from docsforge.core.plugin_base import BasePlugin
from docsforge.files import File, Files, InclusionLevel
from docsforge.nav import Link, Navigation, Section
from docsforge.pages import Page

if TYPE_CHECKING:
    from docsforge.config_defaults import DocsForgeConfig


log = logging.getLogger("docsforge.i18n")


class I18nLanguageConfig(Config):
    locale = Type(str)
    """Language code, e.g. 'zh' or 'en'."""

    name = Type(str)
    """Human-readable language name, e.g. '中文'."""

    default = Type(bool, default=False)
    """Whether this is the default language, built at the site root."""

    build = Type(bool, default=True)
    """Whether to build this language."""

    site_name = Optional(Type(str))
    """Optional override for site_name in this language."""

    site_description = Optional(Type(str))
    """Optional override for site_description in this language."""

    nav_translations = Type(dict, default={})
    """Mapping of default nav titles to translated titles for this language."""


class I18nConfig(Config):
    languages = ListOfItems(SubConfig(I18nLanguageConfig), default=[])
    """List of configured languages. When empty, the plugin does nothing."""

    docs_structure = Choice(("suffix", "folder"), default="suffix")
    """How translated files are organized: 'suffix' (page.zh.md) or 'folder' (zh/page.md)."""

    fallback_to_default = Type(bool, default=True)
    """When a translation is missing, use the default-language page."""


class I18nPlugin(BasePlugin[I18nConfig]):
    """Static i18n plugin for DocsForge."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_locale: str | None = None
        self.locales: list[str] = []
        self._file_lookup: dict[tuple[str, str], File] = {}
        self._base_key_lookup: dict[str, str] = {}
        self._locale_navs: dict[str, Navigation] = {}
        self._locale_url_maps: dict[str, dict[str, str]] = {}

    def on_config(self, config: DocsForgeConfig) -> DocsForgeConfig:
        if not self.config.languages:
            return config

        defaults = [lang for lang in self.config.languages if lang.default]
        if len(defaults) != 1:
            raise ValueError("plugins.i18n.languages must contain exactly one default language")

        self.default_locale = defaults[0].locale
        self.locales = [lang.locale for lang in self.config.languages if lang.build]

        # Expose language metadata to templates.
        config.setdefault("extra", {})
        config["extra"]["i18n_languages"] = [
            {"locale": lang.locale, "name": lang.name, "default": lang.default, "build": lang.build}
            for lang in self.config.languages
        ]
        config["extra"]["i18n_default_locale"] = self.default_locale
        config["extra"]["i18n_current_locale"] = self.default_locale
        return config

    def on_files(self, files: Files, *, config: DocsForgeConfig) -> Files:
        if not self.config.languages:
            return files

        assert self.default_locale is not None
        non_default = [locale for locale in self.locales if locale != self.default_locale]
        if not non_default:
            return files

        new_files: list[File] = []
        # Group default files by their page key.
        default_files_by_key: dict[str, File] = {}
        translation_files: dict[str, dict[str, File]] = {}

        for file in list(files):
            if not file.is_documentation_page():
                continue
            base_key, locale = self._parse_file(file.src_uri)
            self._base_key_lookup[file.src_uri] = base_key
            if locale == self.default_locale:
                default_files_by_key[base_key] = file
            else:
                translation_files.setdefault(base_key, {})[locale] = file

        # For each non-default locale, ensure every default page has a file.
        for base_key, default_file in default_files_by_key.items():
            for locale in non_default:
                translated = translation_files.get(base_key, {}).get(locale)
                if translated is not None:
                    lang_file = self._make_language_file(config, translated, locale, default_file)
                elif self.config.fallback_to_default:
                    lang_file = self._make_fallback_file(config, default_file, locale)
                else:
                    continue

                self._file_lookup[(base_key, locale)] = lang_file
                new_files.append(lang_file)

        for f in new_files:
            files.append(f)

        return files

    def _parse_file(self, src_uri: str) -> tuple[str, str | None]:
        """Return (base_key, locale) for a source file.

        Examples (suffix mode):
            index.md -> ("index", default_locale)
            index.zh.md -> ("index", "zh")
            guide/intro.md -> ("guide/intro", default_locale)
            guide/intro.zh.md -> ("guide/intro", "zh")
        """
        parent, filename = posixpath.split(src_uri)
        stem, ext = posixpath.splitext(filename)

        if self.config.docs_structure == "suffix":
            match = re.fullmatch(r"(.+)\.([a-zA-Z0-9_-]+)", stem)
            if match:
                maybe_locale = match.group(2)
                if maybe_locale in self.locales and maybe_locale != self.default_locale:
                    base_name = match.group(1)
                    base_key = posixpath.join(parent, base_name + ext) if parent else base_name + ext
                    return base_key, maybe_locale

        locale = self.default_locale
        return src_uri, locale

    def _make_language_file(self, config, translated: File, locale: str, default_file: File) -> File:
        """Create a File that outputs under <locale>/ from a translated source."""
        new_file = File(
            translated.src_uri,
            translated.src_dir,
            translated.dest_dir,
            translated.use_directory_urls,
            dest_uri=f"{locale}/{default_file.dest_uri}",
            inclusion=translated.inclusion,
        )
        new_file.i18n_locale = locale  # type: ignore[attr-defined]
        new_file.i18n_base_file = default_file  # type: ignore[attr-defined]
        return new_file

    def _make_fallback_file(self, config, default_file: File, locale: str) -> File:
        """Create a File that outputs under <locale>/ but reads default source."""
        src_uri = default_file.src_uri
        parent, filename = posixpath.split(src_uri)
        stem, ext = posixpath.splitext(filename)
        fallback_src_uri = posixpath.join(parent, f"{stem}.{locale}{ext}") if parent else f"{stem}.{locale}{ext}"

        new_file = File.generated(
            config,
            fallback_src_uri,
            abs_src_path=default_file.abs_src_path,
            inclusion=default_file.inclusion,
        )
        new_file.dest_uri = f"{locale}/{default_file.dest_uri}"
        new_file.i18n_locale = locale  # type: ignore[attr-defined]
        new_file.i18n_base_file = default_file  # type: ignore[attr-defined]
        new_file.i18n_fallback = True  # type: ignore[attr-defined]
        return new_file

    def on_nav(self, nav: Navigation, *, config: DocsForgeConfig, files: Files) -> Navigation:
        if not self.config.languages:
            return nav

        assert self.default_locale is not None
        non_default = [locale for locale in self.locales if locale != self.default_locale]

        # Ensure default pages know they are default locale.
        for page in nav.pages:
            page.file.i18n_locale = self.default_locale  # type: ignore[attr-defined]
            page.file.i18n_base_file = page.file  # type: ignore[attr-defined]

        # Build a per-language nav by cloning the default nav and replacing pages.
        for locale in non_default:
            lang_config = self._get_language_config(locale)
            lang_items = self._clone_nav_items(nav, locale, lang_config)
            lang_pages = self._collect_pages(lang_items)
            self._locale_navs[locale] = Navigation(lang_items, lang_pages)
            self._locale_url_maps[locale] = self._build_url_map(nav, locale)

        # Attach nav lookup to config for templates.
        config["extra"]["i18n_navs"] = self._locale_navs
        return nav

    def _clone_nav_items(self, items: list, locale: str, lang_config: I18nLanguageConfig | None) -> list:
        """Recursively clone nav items, replacing pages with locale-specific pages."""
        result = []
        for item in items:
            if isinstance(item, Section):
                title = item.title
                if lang_config and lang_config.nav_translations and title in lang_config.nav_translations:
                    title = lang_config.nav_translations[title]
                new_section = Section(title, self._clone_nav_items(item.children, locale, lang_config))
                new_section.active = item.active
                result.append(new_section)
            elif isinstance(item, Link):
                result.append(Link(item.title, item.url))
            elif isinstance(item, Page):
                lang_page = self._get_language_page(item, locale)
                if lang_page is not None:
                    result.append(lang_page)
                else:
                    result.append(item)
            else:
                result.append(item)
        return result

    def _get_language_page(self, page: Page, locale: str) -> Page | None:
        """Return the Page for the given locale corresponding to the default page."""
        base_key = self._base_key_lookup.get(page.file.src_uri)
        if base_key is None:
            return None
        lang_file = self._file_lookup.get((base_key, locale))
        if lang_file is None:
            return None
        if lang_file.page is None:
            # Page hasn't been created yet; create it now.
            Page(None, lang_file, page.config)
        return lang_file.page

    def _collect_pages(self, items: list) -> list[Page]:
        pages = []
        for item in items:
            if isinstance(item, Page):
                pages.append(item)
            elif isinstance(item, Section):
                pages.extend(self._collect_pages(item.children))
        return pages

    def _build_url_map(self, default_nav: Navigation, locale: str) -> dict[str, str]:
        """Map default-language page URLs to their counterparts in `locale`."""
        mapping: dict[str, str] = {}
        for page in default_nav.pages:
            base_key = self._base_key_lookup.get(page.file.src_uri)
            if base_key is None:
                continue
            lang_file = self._file_lookup.get((base_key, locale))
            if lang_file is None or lang_file.page is None:
                continue
            mapping[page.url] = lang_file.page.url
        return mapping

    def on_page_context(self, context: templates.TemplateContext, *, page: Page, config: DocsForgeConfig, nav: Navigation) -> templates.TemplateContext:
        if not self.config.languages:
            return context

        locale = getattr(page.file, "i18n_locale", self.default_locale)
        config["extra"]["i18n_current_locale"] = locale

        if locale and locale != self.default_locale:
            locale_nav = self._locale_navs.get(locale)
            if locale_nav is not None:
                context["nav"] = locale_nav

        return context

    def on_page_content(self, html: str, *, page: Page, config: DocsForgeConfig, files: Files) -> str:
        if not self.config.languages:
            return html

        locale = getattr(page.file, "i18n_locale", self.default_locale)
        page.i18n_locale = locale  # type: ignore[attr-defined]
        page.i18n_alternates = self._get_alternates(page, files)  # type: ignore[attr-defined]

        # Override site_name/site_description for non-default languages if configured.
        lang_config = self._get_language_config(locale)
        if lang_config:
            if lang_config.site_name:
                page.title_prefix = lang_config.site_name  # type: ignore[attr-defined]
            if lang_config.site_description:
                page.meta["description"] = lang_config.site_description

        # Apply nav title translations.
        if lang_config and lang_config.nav_translations:
            if page.title in lang_config.nav_translations:
                page.title = lang_config.nav_translations[page.title]

        # Rewrite internal links so a translated page points to other translated pages.
        if locale and locale != self.default_locale:
            html = self._rewrite_links(html, page, locale)

        return html

    def _get_alternates(self, page: Page, files: Files) -> list[dict]:
        """Return alternate language URLs for the current page."""
        base_key = self._base_key_lookup.get(page.file.src_uri)
        if base_key is None:
            return []

        alternates = []
        for locale in self.locales:
            if locale == self.default_locale:
                file = page.file.i18n_base_file if hasattr(page.file, "i18n_base_file") else page.file
            else:
                file = self._file_lookup.get((base_key, locale))
            if file is not None and file.page is not None:
                alternates.append({"locale": locale, "url": file.page.url})
        return alternates

    def _get_language_config(self, locale: str | None) -> I18nLanguageConfig | None:
        if locale is None:
            return None
        for lang in self.config.languages:
            if lang.locale == locale:
                return lang
        return None

    def _rewrite_links(self, html: str, page: Page, locale: str) -> str:
        """Rewrite internal page links in `html` to point to the same locale."""
        url_map = self._locale_url_maps.get(locale)
        if not url_map:
            return html

        current_dir = page.url if page.url.endswith("/") else posixpath.dirname(page.url)

        def replace(match: re.Match) -> str:
            href = match.group(1)
            new_href = self._rewrite_href(href, current_dir, url_map)
            return match.group(0).replace(href, new_href, 1)

        return re.sub(r'<a\s+[^>]*href="([^"]*)"', replace, html, flags=re.IGNORECASE)

    def _rewrite_href(self, href: str, current_dir: str, url_map: dict[str, str]) -> str:
        """Return the locale-aware replacement for a single href, or the original if not applicable."""
        if not href or href.startswith(("#", "mailto:", "tel:")):
            return href
        if "://" in href or href.startswith("//"):
            return href

        anchor = ""
        if "#" in href:
            href, anchor = href.split("#", 1)

        if href.startswith("/"):
            target = href[1:]
        else:
            target = self._resolve_relative_url(href, current_dir)

        locale_target = url_map.get(target)
        if locale_target is None:
            return href + (f"#{anchor}" if anchor else "")

        if anchor:
            locale_target += f"#{anchor}"
        return utils.get_relative_url(current_dir, locale_target)

    def _resolve_relative_url(self, href: str, current_dir: str) -> str:
        """Resolve a relative href to a site-root-relative path."""
        if current_dir and not current_dir.endswith("/"):
            current_dir += "/"
        path = posixpath.join(current_dir, href)
        trailing = "/" if href.endswith("/") else ""
        normalized = posixpath.normpath(path)
        if normalized == ".":
            return ""
        return normalized + trailing

    def on_post_build(self, *, config: DocsForgeConfig) -> None:
        if not self.config.languages:
            return

        env = config.theme.get_env()
        try:
            template = env.get_template("sitemap.xml")
        except Exception:
            log.debug("sitemap.xml template not found; skipping per-language sitemaps")
            return

        for locale, nav in self._locale_navs.items():
            if locale == self.default_locale:
                continue

            files = [f for f in self._language_files(locale) if f.page is not None]
            context = self._sitemap_context(config, nav, files, locale)
            output = template.render(context)
            if not output.strip():
                continue

            output_path = os.path.join(config.site_dir, locale, "sitemap.xml")
            utils.write_file(output.encode("utf-8"), output_path)

            gz_path = f"{output_path}.gz"
            timestamp = utils.get_build_timestamp(pages=[f.page for f in files])
            with open(gz_path, "wb") as f:
                with gzip.GzipFile(fileobj=f, filename=gz_path, mode="wb", mtime=timestamp) as gz_buf:
                    gz_buf.write(output.encode("utf-8"))

    def _language_files(self, locale: str) -> list[File]:
        """Return all files belonging to the given locale."""
        files = []
        for (base_key, file_locale), file in self._file_lookup.items():
            if file_locale == locale:
                files.append(file)
        return files

    def _sitemap_context(self, config, nav, files, locale):
        """Build a context for the sitemap.xml template for a language subtree."""
        version = __import__("docsforge").__version__

        # sitemap.xml lives under <locale>/, so base_url points to <locale>/.
        base_url = f"{locale}/"

        return templates.TemplateContext(
            nav=nav,
            pages=files,
            base_url=base_url,
            extra_css=[],
            extra_javascript=[],
            docsforge_version=version,
            build_date_utc=utils.get_build_datetime(),
            config=config,
            page=None,
        )
