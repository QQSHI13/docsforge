"""Search plugin - full-text search with Marz backend.

Always enabled. Supports multiple languages; CJK is handled natively by
Marz overlapping-bigram indexing, so no word segmentation is needed.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
from html import escape
from html.parser import HTMLParser
from pathlib import Path

import marz

from docsforge import utils
from docsforge.config_base import Config
from docsforge.config_options import Choice, Deprecated, DictOfItems, ListOfItems, Optional, SubConfig, Type
from docsforge.core.plugin_base import BasePlugin

# Default field boosts, mirroring SearchPlugin.on_config.
MARZ_FIELD_BOOSTS = {"title": 1e3, "text": 1e0, "tags": 1e6}

# Matches data-search-* attributes stripped from page content before indexing.
DATA_SEARCH_ATTRS_PATTERN = re.compile(r"\s?data-search-\w+=\"[^\"]+\"")

# Heading tags that delimit index sections.
HEADING_TAGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})

# Reference Marz uses for root ("") entries: refs must not be empty, and no
# real page URL is ever exactly "/". The frontend maps this back to "".
# Keep in sync with MARZ_ROOT_REF in integrations/search/_/index.ts.
MARZ_ROOT_REF = "/"


# Plugin configuration
pipeline = ("stemmer", "stopWordFilter", "trimmer")


class SearchFieldConfig(Config):
    boost = Type((int, float), default=1.0)


class SearchConfig(Config):
    enabled = Type(bool, default=True)
    lang = Optional(ListOfItems(Type(str)))
    separator = Optional(Type(str))
    pipeline = Optional(ListOfItems(Choice(pipeline)))
    fields = DictOfItems(SubConfig(SearchFieldConfig), default={})
    jieba_dict = Deprecated(message="Unsupported option: Marz handles CJK natively")
    jieba_dict_user = Deprecated(message="Unsupported option: Marz handles CJK natively")
    indexing = Deprecated(message="Unsupported option")
    prebuild_index = Deprecated(message="Unsupported option")
    min_search_length = Deprecated(message="Unsupported option")


# Search plugin
class SearchPlugin(BasePlugin[SearchConfig]):
    """Full-text search with Marz backend."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_dirty = False
        self.is_dirtyreload = False
        self.search_index = None
        self.search_indices: dict[str, SearchIndex] = {}
        self._default_locale: str | None = None
        self._locales: list[str] = []
        self._entries_cache: dict[str, dict[str, list[dict]]] = {}
        self._entries_cache_file: Path | None = None

    def on_startup(self, *, command, dirty):
        self.is_dirty = dirty

    def on_config(self, config):
        if not self.config.enabled:
            return

        # Detect i18n configuration.
        i18n_languages = config.get("extra", {}).get("i18n_languages", [])
        if i18n_languages:
            self._default_locale = config["extra"].get("i18n_default_locale")
            self._locales = [lang["locale"] for lang in i18n_languages if lang.get("build", True)]
        else:
            self._default_locale = None
            self._locales = []

        # Load the persisted per-page search-entry cache.
        cache_dir = Path(".docsforge/cache")
        self._entries_cache_file = cache_dir / "search_entries.json"
        self._entries_cache = self._load_entries_cache()

        # Set defaults from theme translations
        if not self.config.lang:
            self.config.lang = [self._translate(config, "search.config.lang")]
        if not self.config.separator:
            self.config.separator = self._translate(config, "search.config.separator")

        if self.config.pipeline is None:
            self.config.pipeline = list(filter(len, re.split(
                r"\s*,\s*", self._translate(config, "search.config.pipeline")
            )))

        # Default field boosts
        if "title" not in self.config.fields:
            self.config.fields["title"] = {"boost": 1e3}
        if "text" not in self.config.fields:
            self.config.fields["text"] = {"boost": 1e0}
        if "tags" not in self.config.fields:
            self.config.fields["tags"] = {"boost": 1e6}

        # Initialize search index/indices
        if self._locales:
            for locale in self._locales:
                idx_config = dict(self.config)
                idx_config["lang"] = [locale]
                self.search_indices[locale] = SearchIndex(**idx_config)
        else:
            self.search_index = SearchIndex(**self.config)

    def _index_for_page(self, page):
        if not self._locales:
            return self.search_index
        locale = getattr(page.file, "i18n_locale", None) or self._default_locale
        if locale is None:
            locale = self._locales[0]
        return self.search_indices.get(locale)

    def on_page_context(self, context, *, page, config, nav):
        if not self.config.enabled:
            return
        index = self._index_for_page(page)
        if index is not None:
            before = len(index.entries)
            index.add_entry_from_context(page)
            page_entries = index.entries[before:]
            locale = self._locale_for_page(page)
            self._entries_cache.setdefault(locale, {})[page.file.src_uri] = page_entries
        page.content = DATA_SEARCH_ATTRS_PATTERN.sub("", page.content)
        # Tell the frontend which search index this locale page should use.
        locale = self._locale_for_page(page)
        context["search_index_url"] = self._search_index_url(locale)

    def _locale_for_page(self, page) -> str:
        return getattr(page.file, "i18n_locale", None) or self._default_locale or ""

    def _search_index_url(self, locale: str | None) -> str:
        """Return the search index path relative to site root for the given locale."""
        if not self._locales or locale == self._default_locale or locale is None:
            return "search/search_index.json"
        return f"search/search_index.{locale}.json"

    def _load_entries_cache(self) -> dict[str, dict[str, list[dict]]]:
        """Load the persisted per-page search-entry cache."""
        if self._entries_cache_file is None or not self._entries_cache_file.exists():
            return {}
        try:
            with open(self._entries_cache_file, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {}

    def _save_entries_cache(self) -> None:
        """Persist the per-page search-entry cache."""
        if self._entries_cache_file is None:
            return
        self._entries_cache_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._entries_cache_file.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._entries_cache, f)
        tmp.replace(self._entries_cache_file)

    def _file_locale(self, src_uri: str) -> str:
        """Return the locale for a source URI, inferring from filename suffix."""
        if not self._locales:
            return ""
        stem, _ = os.path.splitext(src_uri)
        for locale in self._locales:
            if locale != self._default_locale and stem.endswith(f".{locale}"):
                return locale
        return self._default_locale or ""

    def _current_source_uris(self, config) -> set[str]:
        """Return all Markdown source URIs under docs_dir."""
        docs_dir = Path(config.docs_dir)
        if not docs_dir.exists():
            return set()
        return {
            p.relative_to(docs_dir).as_posix()
            for p in docs_dir.rglob("*.md")
            if p.is_file()
        }

    def _prepare_index_entries(self, index, locale: str, config):
        """Assemble the search index from the entries cache, recovering if needed."""
        cache = self._entries_cache.setdefault(locale, {})

        # Drop entries for deleted sources.
        current_uris = self._current_source_uris(config)
        for uri in list(cache.keys()):
            if uri not in current_uris:
                del cache[uri]

        # If the cache is empty/corrupted, rebuild by re-rendering sources.
        if not cache:
            cache.update(self._recover_entries_for_locale(config, locale, index))

        index.entries = []
        for entries in cache.values():
            index.entries.extend(entries)

    def _recover_entries_for_locale(self, config, locale: str, index):
        """Re-render Markdown sources for the locale to rebuild search entries."""
        from docsforge.files import InclusionLevel, get_files
        from docsforge.pages import Page

        entries_by_uri: dict[str, list[dict]] = {}
        files = get_files(config)
        for file in files.documentation_pages(inclusion=InclusionLevel.is_included):
            if self._file_locale(file.src_uri) != locale:
                continue
            if not Path(file.abs_dest_path).exists():
                continue
            if file.page is None:
                page = Page(None, file, config)
                file.page = page
            else:
                page = file.page
            page.read_source(config)
            page.render(config, files)
            before = len(index.entries)
            index.add_entry_from_context(page)
            entries_by_uri[file.src_uri] = index.entries[before:]
        return entries_by_uri

    def on_post_build(self, *, config):
        if not self.config.enabled:
            return
        if self._locales:
            for locale in self._locales:
                index = self.search_indices[locale]
                path = os.path.join(config.site_dir, self._search_index_url(locale))
                self._prepare_index_entries(index, locale, config)
                data = index.generate_search_index(prev=None)
                utils.write_file(data.encode("utf-8"), path)
                utils.write_file(
                    index.generate_marz_index(),
                    os.path.splitext(path)[0] + ".marz",
                )
        else:
            path = os.path.join(config.site_dir, "search", "search_index.json")
            self._prepare_index_entries(self.search_index, "", config)
            data = self.search_index.generate_search_index(prev=None)
            utils.write_file(data.encode("utf-8"), path)
            utils.write_file(
                self.search_index.generate_marz_index(),
                os.path.splitext(path)[0] + ".marz",
            )
        self._save_entries_cache()

    def on_serve(self, server, *, config, builder):
        self.is_dirtyreload = self.is_dirty

    def _translate(self, config, value):
        from docsforge.templates import resolve_lang_partial

        env = config.theme.get_env()
        language = "partials/language.html"
        context = {
            "config": config,
            "lang_partial": resolve_lang_partial(
                config.theme.get("language"), config.theme.dirs
            ),
        }
        template = env.get_template(language, None, context)
        return template.module.t(value)


# Search index
class SearchIndex:
    """Search index entry store with Marz binary export."""

    def __init__(self, **config):
        self.config = config
        self.entries = []

    def add_entry_from_context(self, page):
        search = page.meta.get("search") or {}
        if search.get("exclude"):
            return

        parser = Parser()
        parser.feed(page.content)
        parser.close()

        for section in parser.data:
            if not section.is_excluded():
                self.create_entry_for_section(section, page.toc, page.url, page)

    def create_entry_for_section(self, section, toc, url, page):
        item = self._find_toc_by_id(toc, section.id)
        if item:
            url = url + item.url
        elif section.id:
            url = url + "#" + section.id

        if not section.title:
            section.title = [str(page.meta.get("title", page.title))]

        title = "".join(section.title).strip()
        text = "".join(section.text).strip()

        entry = {
            "location": url,
            "title": self._strip_zwsp(title),
            "text": self._strip_zwsp(text)
        }

        tags = page.meta.get("tags")
        if isinstance(tags, list):
            entry["tags"] = []
            for name in tags:
                if name and isinstance(name, (str, int, float, bool)):
                    entry["tags"].append(str(name))

        search = page.meta.get("search") or {}
        if "boost" in search:
            entry["boost"] = search["boost"]

        self.entries.append(entry)

    def generate_search_index(self, prev):
        config = {
            key: self.config[key]
            for key in ["lang", "separator", "pipeline", "fields"]
        }

        if prev and self.entries:
            # Replace all entries belonging to pages that were rebuilt.
            changed_paths = {
                entry["location"].split("#")[0]
                for entry in self.entries
            }
            kept_entries = [
                entry for entry in prev.entries
                if entry["location"].split("#")[0] not in changed_paths
            ]
            self.entries = kept_entries + self.entries

        if prev and not self.entries:
            self.entries = prev.entries

        # Deterministic output order (the build loop can populate entries in
        # non-deterministic order under parallel rendering). Sort by location
        # so the index is byte-reproducible across builds.
        self.entries.sort(key=lambda e: e.get("location", ""))

        data = {"config": config, "docs": self.entries}
        return json.dumps(data, separators=(",", ":"), default=str)

    def _find_toc_by_id(self, toc, id):
        for toc_item in toc:
            if toc_item.id == id:
                return toc_item
            result = self._find_toc_by_id(toc_item.children, id)
            if result is not None:
                return result
        return None

    def generate_marz_index(self) -> bytes:
        """Build a Marz binary index from the current entries.

        Entries are the same raw (unsegmented) documents serialized to
        `search_index.json`; the frontend loads these bytes for retrieval
        and uses the JSON for display data.
        """
        lang = self.config.get("lang") or ["en"]
        if isinstance(lang, str):
            lang = [lang]
        builder = marz.IndexBuilder(",".join(lang), ref_field="location")

        fields = ["title", "text"]
        if any(e.get("tags") for e in self.entries):
            fields.append("tags")
        for name in fields:
            builder.field(name, self._marz_boost(
                (self.config.get("fields") or {}).get(name),
                MARZ_FIELD_BOOSTS[name],
            ))

        entries = sorted(self.entries, key=lambda e: e.get("location", ""))
        for entry in entries:
            location = entry.get("location", "")
            doc = {
                "location": location if isinstance(location, str) and location else MARZ_ROOT_REF,
                "title": entry.get("title") or "",
                "text": entry.get("text") or "",
            }
            if "tags" in fields:
                tags = entry.get("tags")
                doc["tags"] = " ".join(tags) if isinstance(tags, list) else (tags or "")
            builder.add(doc, boost=self._marz_boost(
                entry.get("boost"), 1.0,
            ))
        return builder.build().to_bytes()

    @staticmethod
    def _strip_zwsp(data: str) -> str:
        """Strip zero-width spaces from indexed text.

        Defensive with Marz: no plugin inserts zero-width spaces any more
        (jieba is gone), but external index-building hooks could. Cheap and
        keeps the serialized JSON free of invisible characters.
        """
        return data.replace("\u200b", "")

    @staticmethod
    def _marz_boost(value, default: float) -> float:
        """Coerce a boost to a finite float Marz accepts, else the default."""
        try:
            number = float(value)
        except (TypeError, ValueError):
            return default
        return number if math.isfinite(number) else default


# HTML parser for search index
class Element:
    """HTML element with attributes."""

    def __init__(self, tag, attrs=None):
        self.tag = tag
        self.attrs = attrs or {}

    def __repr__(self):
        return self.tag

    def __eq__(self, other):
        if isinstance(other, Element):
            return self.tag == other.tag
        return self.tag == other

    def __hash__(self):
        return hash(self.tag)

    def is_excluded(self):
        return "data-search-exclude" in self.attrs


class Section:
    """HTML section with title and text."""

    def __init__(self, el, depth=0):
        self.el = el
        self.depth = depth
        self.text = []
        self.title = []
        self.id = None

    def __repr__(self):
        if self.id:
            return "#".join([self.el.tag, self.id])
        return self.el.tag

    def is_excluded(self):
        return self.el.is_excluded()


class Parser(HTMLParser):
    """Parse HTML into sections for search indexing."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.skip_tags = {"object", "script", "style"}
        self._skip_ids: set[int] = set()
        self.keep = {"p", "code", "pre", "li", "ol", "ul", "sub", "sup"}
        self.context = []
        self.section = None
        self.data = []

    def _is_skipped(self):
        """Return True if the current context is inside skipped content."""
        return any(
            el.tag in self.skip_tags or id(el) in self._skip_ids
            for el in self.context
        )

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        el = Element(tag, attrs)
        if tag not in void:
            self.context.append(el)
        else:
            return

        if tag in HEADING_TAGS:
            depth = len(self.context)
            if "id" in attrs:
                if tag != "h1" and not self.data:
                    self.section = Section(Element("hx"), depth)
                    self.data.append(self.section)
                self.section = Section(el, depth)
                if self.data:
                    self.section.id = attrs["id"]
                self.data.append(self.section)

        if not self.section:
            self.section = Section(Element("hx"))
            self.data.append(self.section)

        for key, value in attrs.items():
            if key == "data-search-exclude":
                self._skip_ids.add(id(el))
                return
            if key == "class" and value == "linenodiv":
                self._skip_ids.add(id(el))
                return

        if not self._is_skipped() and tag in self.keep:
            data = self.section.text
            if self.section.el in self.context:
                data = self.section.title
            data.append(f"<{tag}>")

    def handle_endtag(self, tag):
        if not self.context or self.context[-1] != tag:
            return

        if self.section.depth > len(self.context):
            for section in reversed(self.data):
                if section.depth <= len(self.context):
                    self.section.depth = float("inf")
                    self.section = section
                    break

        el = self.context.pop()
        if id(el) in self._skip_ids:
            self._skip_ids.discard(id(el))
            return

        if not self._is_skipped() and tag in self.keep:
            data = self.section.text
            if self.section.el in self.context:
                data = self.section.title
            index = data.index(f"<{tag}>")
            for i in range(index + 1, len(data)):
                if not data[i].isspace():
                    index = len(data)
                    break
            if len(data) > index:
                while len(data) > index:
                    data.pop()
            else:
                data.append(f"</{tag}>")

    def handle_data(self, data):
        if self._is_skipped():
            return

        if "pre" not in self.context:
            data = " " if data.isspace() else data.replace("\n", " ")

        if not self.section:
            self.section = Section(Element("hx"))
            self.data.append(self.section)

        if self.section.el in self.context:
            permalink = False
            for el in self.context:
                if el.tag == "a" and el.attrs.get("class") == "headerlink":
                    permalink = True
            if not permalink:
                self.section.title.append(escape(data, quote=False))
        elif data.isspace():
            if not self.section.text or not self.section.text[-1].isspace() or "pre" in self.context:
                self.section.text.append(data)
        else:
            self.section.text.append(escape(data, quote=False))


# Self-closing tags
void = {
    "area", "base", "br", "col", "embed", "hr", "img",
    "input", "link", "meta", "param", "source", "track", "wbr"
}

log = logging.getLogger("docsforge.search")
