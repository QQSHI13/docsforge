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

        # Remember original nav titles so we can reset them for the default locale.
        self._store_default_titles(nav.items)
        return nav

    def _store_default_titles(self, items: list) -> None:
        for item in items:
            if not hasattr(item, "_i18n_default_title"):
                item._i18n_default_title = item.title  # type: ignore[attr-defined]
            if item.is_section:
                self._store_default_titles(item.children)

    def _translate_nav_titles(self, items: list, locale: str, lang_config: I18nLanguageConfig | None) -> None:
        """Translate nav titles for the current locale, or reset them for the default locale."""
        for item in items:
            if item.is_section:
                self._translate_nav_titles(item.children, locale, lang_config)

            default_title = getattr(item, "_i18n_default_title", item.title)

            if locale == self.default_locale or lang_config is None:
                item.title = default_title
                continue

            title = None
            if item.i18n_titles and locale in item.i18n_titles:
                title = item.i18n_titles[locale]
            elif lang_config.nav_translations and default_title in lang_config.nav_translations:
                title = lang_config.nav_translations[default_title]

            item.title = title if title is not None else default_title

    def on_page_context(self, context: dict, *, page: Page, config: DocsForgeConfig, nav: Navigation) -> dict:
        if not self._languages:
            return context

        locale = getattr(page.file, "i18n_locale", self.default_locale)
        config["extra"]["i18n_current_locale"] = locale

        lang_config = self._get_language_config(locale)
        self._translate_nav_titles(nav.items, locale, lang_config)

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
