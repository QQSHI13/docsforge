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
from urllib.parse import quote as urlquote, urlparse

from docsforge import meta, templates, utils
from docsforge.config_options import ListOfItems, Optional, SubConfig, Type, ValidationError
from docsforge.config_base import Config
from docsforge.core.plugin_base import BasePlugin
from docsforge.files import File, Files, InclusionLevel
from docsforge.nav import Link, Navigation, Section, _add_parent_links
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
    """When a translation is missing, use the default-language page."""


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
        self._locale_url_maps: dict[str, dict[str, str]] = {}
        self._locale_asset_files: dict[tuple[str, str], File] = {}
        self._locale_asset_url_maps: dict[str, dict[str, str]] = {}

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

        self._default_files_by_key = default_files_by_key

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

        # Remove translated source files from the root site; they are emitted under the locale.
        for locale_files in translation_files.values():
            for translated in locale_files.values():
                files.remove(translated)

        for f in new_files:
            files.append(f)

        self._process_assets(files, non_default, config)

        return files

    def _process_assets(self, files: Files, non_default: list[str], config: DocsForgeConfig) -> None:
        """Create per-locale copies of docs assets, with fallback to the default asset."""
        default_assets: dict[str, File] = {}
        translation_assets: dict[str, dict[str, File]] = {}
        translated_to_remove: list[File] = []

        for file in list(files):
            if file.is_documentation_page() or file.is_static_page():
                continue
            base_key, locale = self._parse_file(file.src_uri)
            if locale == self.default_locale:
                default_assets[base_key] = file
            else:
                translation_assets.setdefault(base_key, {})[locale] = file
                translated_to_remove.append(file)

        new_assets: list[File] = []
        for base_key, default_file in default_assets.items():
            for locale in non_default:
                translated = translation_assets.get(base_key, {}).get(locale)
                if translated is not None:
                    lang_file = File(
                        translated.src_uri,
                        translated.src_dir,
                        translated.dest_dir,
                        translated.use_directory_urls,
                        dest_uri=f"{locale}/{default_file.dest_uri}",
                        inclusion=translated.inclusion,
                    )
                elif self.config.fallback_to_default:
                    lang_file = File.generated(
                        config,
                        f"{locale}/{base_key}",
                        abs_src_path=default_file.abs_src_path,
                        inclusion=default_file.inclusion,
                    )
                else:
                    continue

                lang_file.i18n_locale = locale  # type: ignore[attr-defined]
                lang_file.i18n_base_file = default_file  # type: ignore[attr-defined]
                self._locale_asset_files[(base_key, locale)] = lang_file
                new_assets.append(lang_file)

        for file in translated_to_remove:
            files.remove(file)

        for file in new_assets:
            files.append(file)

        for locale in non_default:
            mapping: dict[str, str] = {}
            for base_key, default_file in default_assets.items():
                lang_file = self._locale_asset_files.get((base_key, locale))
                if lang_file is None:
                    continue
                mapping[default_file.url] = lang_file.url
            self._locale_asset_url_maps[locale] = mapping

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
        new_file.inclusion = (
            InclusionLevel.NOT_IN_NAV if default_file.inclusion.is_included() else default_file.inclusion
        )
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
        new_file.inclusion = (
            InclusionLevel.NOT_IN_NAV if default_file.inclusion.is_included() else default_file.inclusion
        )
        return new_file

    def on_nav(self, nav: Navigation, *, config: DocsForgeConfig, files: Files) -> Navigation:
        if not self._languages:
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
            lang_items = self._clone_nav_items(nav, locale, lang_config, config)
            lang_pages = self._collect_pages(lang_items)
            locale_nav = Navigation(lang_items, lang_pages)
            # Rebuild parent links for the cloned nav so active-state propagation
            # works when rendering locale pages.
            _add_parent_links(locale_nav.items)
            # The locale index page is the homepage for its subtree. Setting this
            # keeps header/nav logo links inside the locale instead of escaping
            # to the default-language site root.
            for page in lang_pages:
                if page.file.url == f"{locale}/":
                    locale_nav.homepage = page
                    break
            self._locale_navs[locale] = locale_nav
            self._locale_url_maps[locale] = self._build_url_map(locale)

        # Attach nav lookup to config for templates.
        config["extra"]["i18n_navs"] = self._locale_navs
        return nav

    def _clone_nav_items(
        self,
        items: list,
        locale: str,
        lang_config: I18nLanguageConfig | None,
        config: DocsForgeConfig,
    ) -> list:
        """Recursively clone nav items, replacing pages with locale-specific pages."""
        result = []
        for item in items:
            if isinstance(item, Section):
                title = item.i18n_titles.get(locale) if item.i18n_titles else None
                if title is None and lang_config and lang_config.nav_translations and item.title in lang_config.nav_translations:
                    title = lang_config.nav_translations[item.title]
                if title is None:
                    title = item.title
                new_section = Section(
                    title, self._clone_nav_items(item.children, locale, lang_config, config)
                )
                new_section.active = item.active
                result.append(new_section)
            elif isinstance(item, Link):
                title = item.i18n_titles.get(locale) if item.i18n_titles else None
                if title is None and lang_config and lang_config.nav_translations and item.title in lang_config.nav_translations:
                    title = lang_config.nav_translations[item.title]
                if title is None:
                    title = item.title
                result.append(Link(title, item.url))
            elif isinstance(item, Page):
                lang_page = self._get_language_page(item, locale, lang_config, config)
                if lang_page is not None:
                    result.append(lang_page)
                else:
                    result.append(item)
            else:
                result.append(item)
        return result

    def _get_language_page(
        self,
        page: Page,
        locale: str,
        lang_config: I18nLanguageConfig | None,
        config: DocsForgeConfig,
    ) -> Page | None:
        """Return the Page for the given locale corresponding to the default page."""
        base_key = self._base_key_lookup.get(page.file.src_uri)
        if base_key is None:
            return None
        lang_file = self._file_lookup.get((base_key, locale))
        if lang_file is None:
            return None

        title = self._resolve_locale_title(page, lang_file, lang_config, locale)
        if lang_file.page is None:
            Page(title, lang_file, config)
        elif title is not None and not lang_file.page.title:
            # Fallback/translation pages created by get_navigation may have no title yet.
            lang_file.page.title = title
        return lang_file.page

    def _resolve_locale_title(
        self,
        page: Page,
        lang_file: File,
        lang_config: I18nLanguageConfig | None,
        locale: str | None = None,
    ) -> str | None:
        """Pick the best nav title for a locale page.

        Precedence:
        1. An explicit i18n title on the nav entry for the target locale.
        2. An explicit nav_translations entry for the default page's title.
        3. The translated file's own title (frontmatter or first H1).
        4. The default page's configured/nav title.
        """
        if locale and page.i18n_titles and locale in page.i18n_titles:
            return page.i18n_titles[locale]

        default_title = self._default_page_title(page)
        if lang_config and lang_config.nav_translations and default_title in lang_config.nav_translations:
            return lang_config.nav_translations[default_title]

        lang_title = self._read_title(lang_file)
        if lang_title is not None:
            return lang_title

        return page.title

    def _default_page_title(self, page: Page) -> str | None:
        """Best-effort default-language title for nav_translations lookups."""
        if page.title is not None:
            return page.title
        if page.is_homepage:
            return "Home"
        return self._read_title(page.file)

    def _read_title(self, file: File) -> str | None:
        """Read the title from a file's YAML frontmatter or first H1 heading."""
        try:
            content = file.content_string
            _, data = meta.get_data(content)
        except Exception:
            return None
        title = data.get("title")
        if title is not None:
            return str(title)
        title = utils.get_markdown_title(content)
        if title:
            return title
        return None

    def _collect_pages(self, items: list) -> list[Page]:
        pages = []
        for item in items:
            if isinstance(item, Page):
                pages.append(item)
            elif isinstance(item, Section):
                pages.extend(self._collect_pages(item.children))
        return pages

    def _find_page_in_nav(self, items: list, target_file: File) -> Page | None:
        """Return the Page in the locale nav whose file matches target_file."""
        for item in items:
            if isinstance(item, Page) and item.file is target_file:
                return item
            if isinstance(item, Section):
                found = self._find_page_in_nav(item.children, target_file)
                if found is not None:
                    return found
        return None

    def _build_url_map(self, locale: str) -> dict[str, str]:
        """Map default-language page URLs to their counterparts in `locale`."""
        mapping: dict[str, str] = {}
        for base_key, default_file in self._default_files_by_key.items():
            lang_file = self._file_lookup.get((base_key, locale))
            if lang_file is None or lang_file.page is None or default_file.page is None:
                continue
            mapping[default_file.page.url] = lang_file.page.url
        return mapping

    def on_page_context(self, context: templates.TemplateContext, *, page: Page, config: DocsForgeConfig, nav: Navigation) -> templates.TemplateContext:
        if not self._languages:
            return context

        locale = getattr(page.file, "i18n_locale", self.default_locale)
        config["extra"]["i18n_current_locale"] = locale

        if locale and locale != self.default_locale:
            locale_nav = self._locale_navs.get(locale)
            if locale_nav is not None:
                context["nav"] = locale_nav
                # Re-wire parent links to the locale nav (the default-language
                # nav may have overwritten them) and activate the current page
                # so the top bar highlights and the left sidebar expands.
                _add_parent_links(locale_nav.items)
                locale_page = self._find_page_in_nav(locale_nav.items, page.file)
                if locale_page is not None:
                    locale_page.active = True

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
            html = self._rewrite_asset_links(html, page, locale)

        return html

    def _get_alternates(self, page: Page, files: Files) -> list[dict]:
        """Return alternate language URLs for the current page."""
        base_key = self._base_key_lookup.get(page.file.src_uri)
        if base_key is None:
            # Generated fallback files are not present in _base_key_lookup, but
            # they always reference their default-language source file.
            base_file = getattr(page.file, "i18n_base_file", None)
            if base_file is not None:
                base_key = self._base_key_lookup.get(base_file.src_uri)
        if base_key is None:
            return []

        alternates = []
        for locale in self.locales:
            if locale == self.default_locale:
                file = page.file.i18n_base_file if hasattr(page.file, "i18n_base_file") else page.file
            else:
                file = self._file_lookup.get((base_key, locale))
            if file is not None and file.page is not None:
                url = file.page.url
                # The homepage Page.url is normalized to "" for the default
                # language, but the empty string loses its trailing slash when
                # passed through the `url` template filter from a locale page.
                # Return "./" so the locale stays a directory-style URL.
                if url in ("", ".", "./"):
                    url = "./"
                alternates.append({"locale": locale, "url": url})
        return alternates

    def _get_language_config(self, locale: str | None) -> I18nLanguageConfig | None:
        if locale is None:
            return None
        for lang in self._languages:
            if lang.locale == locale:
                return lang
        return None

    _LINK_HREF_RE = re.compile(
        r'<a[^>]*?\shref=(?:"([^"]*)"|\'([^\']*)\'|([^\s>"\']+))',
        re.IGNORECASE,
    )

    def _rewrite_links(self, html: str, page: Page, locale: str) -> str:
        """Rewrite internal page links in `html` to point to the same locale."""
        url_map = self._locale_url_maps.get(locale)
        if not url_map:
            return html

        current_dir = page.url if page.url.endswith("/") else posixpath.dirname(page.url)

        def replace(match: re.Match) -> str:
            href = match.group(1) or match.group(2) or match.group(3)
            new_href = self._rewrite_href(href, current_dir, url_map)
            return match.group(0).replace(href, new_href, 1)

        return self._LINK_HREF_RE.sub(replace, html)

    _ASSET_ATTR_RE = re.compile(
        r'<([A-Za-z][A-Za-z0-9]*)[^>]*?\s(?:src|href|data|poster)=(?:"([^"]*)"|\'([^\']*)\'|([^\s>"\']+))',
        re.IGNORECASE,
    )

    def _rewrite_asset_links(self, html: str, page: Page, locale: str) -> str:
        """Rewrite asset references on locale pages to point to the locale copy."""
        url_map = self._locale_asset_url_maps.get(locale)
        if not url_map:
            return html

        current_dir = page.url if page.url.endswith("/") else posixpath.dirname(page.url)

        def replace(match: re.Match) -> str:
            tag = match.group(1).lower()
            if tag == "a":
                return match.group(0)
            attr_val = match.group(2) or match.group(3) or match.group(4)
            new_val = self._rewrite_href(attr_val, current_dir, url_map)
            return match.group(0).replace(attr_val, new_val, 1)

        return self._ASSET_ATTR_RE.sub(replace, html)

    def _rewrite_href(self, href: str, current_dir: str, url_map: dict[str, str]) -> str:
        """Return the locale-aware replacement for a single href, or the original if not applicable."""
        if not href or href.startswith(("#", "mailto:", "tel:", "data:")):
            return href
        if "://" in href or href.startswith("//"):
            return href

        # Preserve query string and anchor; only the path part is mapped.
        anchor = ""
        if "#" in href:
            href, anchor = href.split("#", 1)
        query = ""
        if "?" in href:
            href, query = href.split("?", 1)

        if href.startswith("/"):
            target = href[1:]
        else:
            target = self._resolve_relative_url(href, current_dir)

        locale_target = url_map.get(target)
        if locale_target is None:
            locale_target = url_map.get(urlquote(target))
        if locale_target is None:
            return href + (f"?{query}" if query else "") + (f"#{anchor}" if anchor else "")

        relative = utils.get_relative_url(current_dir, locale_target)
        return relative + (f"?{query}" if query else "") + (f"#{anchor}" if anchor else "")

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
        if not self._languages:
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
                with gzip.GzipFile(fileobj=f, filename="sitemap.xml", mode="wb", mtime=timestamp) as gz_buf:
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
