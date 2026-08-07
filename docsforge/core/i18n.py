"""I18n plugin - multi-language documentation support.

Provides locale-agnostic static i18n: add translated files next to your
default-language files (e.g. index.zh.md beside index.md) and DocsForge
builds sibling output files (e.g. index.zh.html) that share the same
locale-agnostic URL as the default page.
"""

from __future__ import annotations

import logging
import posixpath
import re
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from docsforge.config_options import ListOfItems, Optional, SubConfig, Type, ValidationError
from docsforge.config_base import Config
from docsforge.core.plugin_base import BasePlugin
from docsforge.files import File, Files, InclusionLevel
from docsforge.nav import Navigation
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

    fallback_to_default = Type(bool, default=True)
    """Legacy option; the new locale-agnostic architecture never creates fallback pages."""


class I18nPlugin(BasePlugin[I18nConfig]):
    """Static i18n plugin for DocsForge."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_locale: str | None = None
        self.locales: list[str] = []
        self._languages: list[I18nLanguageConfig] = []
        self._file_lookup: dict[tuple[str, str], File] = {}
        self._base_key_lookup: dict[str, str] = {}
        self._default_files_by_key: dict[str, File] = {}
        self._locale_navs: dict[str, Navigation] = {}

    def _get_languages(self, config: DocsForgeConfig) -> list[I18nLanguageConfig]:
        """Return configured languages from plugin config or extra.i18n_languages."""
        if self.config.languages:
            return self.config.languages
        extra = config.get("extra", {})
        raw = extra.get("i18n_languages", []) or []
        if not raw:
            return []

        validator = SubConfig(I18nLanguageConfig)
        validated: list[I18nLanguageConfig] = []
        for idx, item in enumerate(raw):
            if not isinstance(item, dict):
                raise ValidationError(
                    f"extra.i18n_languages[{idx}] must be a mapping, got {type(item).__name__}"
                )
            cfg = I18nLanguageConfig()
            cfg.load_dict(dict(item))
            errors, warnings = cfg.validate()
            if errors:
                raise ValidationError(
                    f"extra.i18n_languages[{idx}]: "
                    + "; ".join(f"{k}: {v}" for k, v in errors)
                )
            validated.append(cfg)
        return validated

    def on_config(self, config: DocsForgeConfig) -> DocsForgeConfig:
        self._languages = self._get_languages(config)
        if not self._languages:
            return config

        defaults = [lang for lang in self._languages if lang.default]
        if len(defaults) != 1:
            raise ValueError("i18n.languages must contain exactly one default language")

        self.default_locale = defaults[0].locale
        self.locales = [lang.locale for lang in self._languages if lang.build]

        # Expose language metadata to templates.
        config.setdefault("extra", {})
        config["extra"]["i18n_languages"] = [
            {"locale": lang.locale, "name": lang.name, "default": lang.default, "build": lang.build}
            for lang in self._languages
        ]
        config["extra"]["i18n_default_locale"] = self.default_locale
        config["extra"]["i18n_current_locale"] = self.default_locale
        return config

    def on_files(self, files: Files, *, config: DocsForgeConfig) -> Files:
        if not self._languages:
            return files

        assert self.default_locale is not None
        non_default = [locale for locale in self.locales if locale != self.default_locale]
        if not non_default:
            return files

        new_files: list[File] = []
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

        self._default_files_by_key = default_files_by_key

        # Only create language files for translations that actually exist.
        for base_key, default_file in default_files_by_key.items():
            for locale in non_default:
                translated = translation_files.get(base_key, {}).get(locale)
                if translated is None:
                    continue
                lang_file = self._make_language_file(config, translated, locale, default_file)
                self._file_lookup[(base_key, locale)] = lang_file
                new_files.append(lang_file)

        # Remove translated source files from the root site; they are emitted as siblings.
        for locale_files in translation_files.values():
            for translated in locale_files.values():
                files.remove(translated)

        for f in new_files:
            files.append(f)

        # Docs assets are no longer copied per locale.
        return files

    def _process_assets(self, files: Files, non_default: list[str], config: DocsForgeConfig) -> None:
        """Legacy hook; per-locale asset copies are no longer created."""
        pass

    def _parse_file(self, src_uri: str) -> tuple[str, str | None]:
        """Return (base_key, locale) for a source file.

        Translated files are recognized by the locale suffix:
            index.md -> ("index", default_locale)
            index.zh.md -> ("index", "zh")
            guide/intro.md -> ("guide/intro", default_locale)
            guide/intro.zh.md -> ("guide/intro", "zh")
        """
        parent, filename = posixpath.split(src_uri)
        stem, ext = posixpath.splitext(filename)

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
        """Create a sibling File that shares the default file's locale-agnostic URL."""
        dest_uri = self._locale_sibling_dest_uri(default_file, locale)
        new_file = File(
            translated.src_uri,
            translated.src_dir,
            translated.dest_dir,
            translated.use_directory_urls,
            dest_uri=dest_uri,
            inclusion=translated.inclusion,
        )
        # Share the default file's URL so all locales are locale-agnostic.
        new_file.url = default_file.url
        new_file.i18n_locale = locale  # type: ignore[attr-defined]
        new_file.i18n_base_file = default_file  # type: ignore[attr-defined]
        new_file.inclusion = (
            InclusionLevel.NOT_IN_NAV if default_file.inclusion.is_included() else default_file.inclusion
        )
        return new_file

    def _locale_sibling_dest_uri(self, default_file: File, locale: str) -> str:
        """Return the sibling destination path for a translation.

        Examples with directory URLs:
            index.md -> index.zh.html
            page.md -> page/index.zh.html

        Examples without directory URLs:
            index.md -> index.zh.html
            page.md -> page.zh.html
        """
        dest_uri = default_file.dest_uri
        if default_file.use_directory_urls:
            if dest_uri.endswith("/index.html"):
                return dest_uri[: -len("index.html")] + f"index.{locale}.html"
            if dest_uri == "index.html":
                return f"index.{locale}.html"
        else:
            if dest_uri.endswith(".html"):
                return dest_uri[: -len(".html")] + f".{locale}.html"
        return dest_uri

    def _make_fallback_file(self, config, default_file: File, locale: str) -> File:
        """Legacy method; fallback pages are no longer emitted."""
        raise NotImplementedError("fallback files are not supported in the locale-agnostic i18n rewrite")

    def on_nav(self, nav: Navigation, *, config: DocsForgeConfig, files: Files) -> Navigation:
        if not self._languages:
            return nav

        assert self.default_locale is not None

        # Ensure default pages know they are the default locale.
        for page in nav.pages:
            page.file.i18n_locale = self.default_locale  # type: ignore[attr-defined]
            page.file.i18n_base_file = page.file  # type: ignore[attr-defined]

        # Build a per-locale copy of the nav with translated titles but the same
        # locale-agnostic URLs. This avoids mutating shared nav items during
        # parallel page rendering.
        from docsforge.nav import _add_parent_links

        self._locale_navs[self.default_locale] = nav
        for locale in self.locales:
            if locale == self.default_locale:
                continue
            lang_config = self._get_language_config(locale)
            lang_items = self._clone_nav_items(nav.items, locale, lang_config, config)
            lang_pages = self._collect_pages(lang_items)
            locale_nav = Navigation(lang_items, lang_pages)
            locale_nav.homepage = nav.homepage
            _add_parent_links(locale_nav.items)
            self._locale_navs[locale] = locale_nav

        return nav

    def _clone_nav_items(
        self,
        items: list,
        locale: str,
        lang_config: I18nLanguageConfig | None,
        config: DocsForgeConfig,
    ) -> list:
        """Recursively clone nav items, translating titles and swapping Pages to their locale counterparts."""
        from docsforge.nav import Link, Section

        result = []
        for item in items:
            if item.is_section:
                title = self._resolve_locale_title(item, locale, lang_config)
                new_section = Section(title, self._clone_nav_items(item.children, locale, lang_config, config))
                new_section.active = item.active
                new_section.i18n_titles = dict(item.i18n_titles)
                result.append(new_section)
            elif item.is_link:
                title = self._resolve_locale_title(item, locale, lang_config)
                new_link = Link(title, item.url)
                new_link.i18n_titles = dict(item.i18n_titles)
                result.append(new_link)
            elif item.is_page:
                lang_page = self._get_language_page(item, locale, lang_config, config)
                result.append(lang_page if lang_page is not None else item)
            else:
                result.append(item)
        return result

    def _collect_pages(self, items: list) -> list[Page]:
        pages = []
        for item in items:
            if item.is_page:
                pages.append(item)
            elif item.is_section:
                pages.extend(self._collect_pages(item.children))
        return pages

    def _get_language_page(
        self,
        page: Page,
        locale: str,
        lang_config: I18nLanguageConfig | None,
        config: DocsForgeConfig,
    ) -> Page | None:
        """Return the locale-specific Page for a default nav Page, or None if no translation exists."""
        base_key = self._base_key_lookup.get(page.file.src_uri)
        if base_key is None:
            return None
        lang_file = self._file_lookup.get((base_key, locale))

        # Explicit translations (per-item or nav config) win. Otherwise leave
        # title as None so the translated file's frontmatter title is used.
        title = None
        if page.i18n_titles and locale in page.i18n_titles:
            title = page.i18n_titles[locale]
        elif lang_config and lang_config.nav_translations and page.title in lang_config.nav_translations:
            title = lang_config.nav_translations[page.title]

        if lang_file is not None:
            if lang_file.page is None:
                Page(title, lang_file, config)
            elif title is not None:
                lang_file.page.title = title
            # Remember the default-language file so nav titles can be resolved
            # after Markdown sources (and frontmatter titles) have been read.
            lang_file.page.i18n_base_file = page.file  # type: ignore[attr-defined]
            return lang_file.page

        # No translation exists: still produce a nav entry pointing at the
        # default page, but with a translated nav title if one is configured.
        # Do not overwrite the original file.page.
        original_page = page.file.page
        nav_title = title if title is not None else page.title
        nav_page = Page(nav_title, page.file, config)
        nav_page.i18n_base_file = page.file  # type: ignore[attr-defined]
        page.file.page = original_page
        return nav_page

    def _resolve_locale_title(
        self,
        item,
        locale: str,
        lang_config: I18nLanguageConfig | None,
    ) -> str:
        """Pick the best nav title for a locale item (Section, Link, or Page)."""
        if locale == self.default_locale or lang_config is None:
            return item.title
        if item.i18n_titles and locale in item.i18n_titles:
            return item.i18n_titles[locale]
        if lang_config.nav_translations and item.title in lang_config.nav_translations:
            return lang_config.nav_translations[item.title]
        return item.title

    def on_page_context(self, context: dict, *, page: Page, config: DocsForgeConfig, nav: Navigation) -> dict:
        if not self._languages:
            return context

        locale = getattr(page.file, "i18n_locale", self.default_locale)
        config["extra"]["i18n_current_locale"] = locale

        locale_nav = self._locale_navs.get(locale)
        if locale_nav is not None:
            context["nav"] = locale_nav
            # By the time pages are rendered all Markdown sources have been read,
            # so translated frontmatter titles are available. Ensure nav titles
            # use explicit translations when configured, and that fallback nav
            # entries copied from the default page carry the correct title.
            self._fix_locale_nav_titles(locale_nav, locale)
            # Activate the current page in the locale nav so the sidebar/top bar
            # highlight the right item.
            for nav_page in locale_nav.pages:
                if nav_page.file is page.file:
                    nav_page.active = True
                    break

        # Expose the site base URL so the language switcher can rewrite its
        # links client-side after instant navigation.
        site_url = config.get("site_url", "")
        base_url = "/"
        if site_url:
            parsed = urlparse(site_url)
            base_url = parsed.path
            if base_url and not base_url.endswith("/"):
                base_url += "/"
        context["i18n_base_url"] = base_url

        return context

    def _fix_locale_nav_titles(self, locale_nav: Navigation, locale: str) -> None:
        """Update nav titles after Markdown sources have been read.

        Explicit nav translations win over frontmatter. Fallback entries that
        point to the default-language file are synced from the original page.
        """
        if getattr(locale_nav, "_i18n_titles_fixed", False):
            return
        locale_nav._i18n_titles_fixed = True  # type: ignore[attr-defined]

        lang_config = self._get_language_config(locale)
        for nav_page in locale_nav.pages:
            # Use the canonical page stored on the file. For translated files
            # this is the translated page itself; for fallback entries it is
            # the original default-language page.
            source_page = nav_page.file.page
            if source_page is None:
                continue

            title = None
            base_file = getattr(nav_page, "i18n_base_file", nav_page.file)
            default_page = base_file.page if base_file else None
            default_title = default_page.title if default_page else source_page.title
            if nav_page.i18n_titles and locale in nav_page.i18n_titles:
                title = nav_page.i18n_titles[locale]
            elif lang_config and lang_config.nav_translations and default_title in lang_config.nav_translations:
                title = lang_config.nav_translations[default_title]

            if title is not None:
                nav_page.title = title
            elif nav_page.file.page is not nav_page and source_page.title is not None:
                # Fallback nav-only copy: mirror the original page title.
                nav_page.title = source_page.title

    def on_page_content(self, html: str, *, page: Page, config: DocsForgeConfig, files: Files) -> str:
        if not self._languages:
            return html

        locale = getattr(page.file, "i18n_locale", self.default_locale)
        page.i18n_locale = locale  # type: ignore[attr-defined]
        page.i18n_alternates = self._get_alternates(page)  # type: ignore[attr-defined]

        # Override site_name/site_description for non-default languages if configured.
        lang_config = self._get_language_config(locale)
        if lang_config:
            if lang_config.site_name:
                page.title_prefix = lang_config.site_name  # type: ignore[attr-defined]
            if lang_config.site_description:
                page.meta["description"] = lang_config.site_description

        # Apply nav title translations to the page title as well.
        if lang_config and lang_config.nav_translations:
            if page.title in lang_config.nav_translations:
                page.title = lang_config.nav_translations[page.title]

        return html

    def _get_alternates(self, page: Page) -> list[dict]:
        """Return alternate language URLs for the current page.

        All locales share the same locale-agnostic canonical URL.
        """
        url = page.url
        if url in ("", ".", "./"):
            url = "./"
        return [{"locale": locale, "url": url} for locale in self.locales]

    def _get_language_config(self, locale: str | None) -> I18nLanguageConfig | None:
        if locale is None:
            return None
        for lang in self._languages:
            if lang.locale == locale:
                return lang
        return None

    def on_post_build(self, *, config: DocsForgeConfig) -> None:
        """Per-locale sitemaps are no longer generated; the theme emits a single root sitemap."""
        return
