"""Search plugin - full-text search with Lunr.js backend.

Always enabled. Supports multiple languages and Chinese segmentation.
"""

from __future__ import annotations

import json
import logging
import os
import re

from backrefs import bre
from html import escape
from html.parser import HTMLParser

from docsforge import utils
from docsforge.config_options import Choice, Deprecated, ListOfItems, Optional, SubConfig, Type
from docsforge.config_base import Config
from docsforge.core.plugin_base import BasePlugin


def _get_jieba():
    """Lazy-load jieba to avoid dictionary loading penalty for non-Chinese sites."""
    global jieba
    if jieba is None:
        try:
            import jieba as _jieba
            jieba = _jieba
        except ImportError:
            jieba = None
    return jieba

jieba = None


def _needs_jieba(config) -> bool:
    """Return True if jieba Chinese segmentation should be loaded."""
    if config.get("jieba_dict") or config.get("jieba_dict_user"):
        return True
    lang = config.get("lang")
    if isinstance(lang, str):
        return lang.startswith('zh')
    if isinstance(lang, list):
        return any(isinstance(l, str) and l.startswith('zh') for l in lang)
    return False


# Plugin configuration
pipeline = ("stemmer", "stopWordFilter", "trimmer")


class SearchFieldConfig(Config):
    boost = Type((int, float), default=1.0)


class SearchConfig(Config):
    enabled = Type(bool, default=True)
    lang = Optional(ListOfItems(Type(str)))
    separator = Optional(Type(str))
    pipeline = Optional(ListOfItems(Choice(pipeline)))
    fields = Type(dict, default={})
    jieba_dict = Optional(Type(str))
    jieba_dict_user = Optional(Type(str))
    indexing = Deprecated(message="Unsupported option")
    prebuild_index = Deprecated(message="Unsupported option")
    min_search_length = Deprecated(message="Unsupported option")


# Search plugin
class SearchPlugin(BasePlugin[SearchConfig]):
    """Full-text search with Lunr.js backend."""

    optional_dependencies = ['jieba']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_dirty = False
        self.is_dirtyreload = False
        self.search_index_prev = None
        self.search_index = None
        self.search_indices: dict[str, SearchIndex] = {}
        self.search_indices_prev: dict[str, SearchIndex] = {}
        self._default_locale: str | None = None
        self._locales: list[str] = []

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

        # Set defaults from theme translations
        if not self.config.lang:
            self.config.lang = [self._translate(config, "search.config.lang")]
        if not self.config.separator:
            self.config.separator = self._translate(config, "search.config.separator")

        if self.config.pipeline is None:
            self.config.pipeline = list(filter(len, re.split(
                r"\s*,\s*", self._translate(config, "search.config.pipeline")
            )))

        # Validate fields
        validator = SubConfig(SearchFieldConfig)
        for field_config in self.config.fields.values():
            validator.run_validation(field_config)

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

        # Configure jieba only when Chinese search is requested
        if _needs_jieba(self.config):
            jieba_lib = _get_jieba()
            if not jieba_lib:
                log.warning(
                    "Chinese content may not be segmented correctly without jieba. "
                    "Install it for better Chinese search: pip install docsforge[chinese]"
                )
            elif self.config.jieba_dict:
                path = os.path.normpath(self.config.jieba_dict)
                if os.path.isfile(path):
                    jieba_lib.set_dictionary(path)
                else:
                    log.warning(f"jieba_dict not found: {self.config.jieba_dict}")

            if jieba_lib and self.config.jieba_dict_user:
                path = os.path.normpath(self.config.jieba_dict_user)
                if os.path.isfile(path):
                    jieba_lib.load_userdict(path)
                else:
                    log.warning(f"jieba_dict_user not found: {self.config.jieba_dict_user}")

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
            index.add_entry_from_context(page)
        page.content = re.sub(
            r"\s?data-search-\w+=\"[^\"]+\"",
            "",
            page.content
        )

    def on_post_build(self, *, config):
        if not self.config.enabled:
            return
        if self._locales:
            for locale in self._locales:
                index = self.search_indices[locale]
                prev = self.search_indices_prev.get(locale)
                data = index.generate_search_index(prev)
                if locale == self._default_locale:
                    path = os.path.join(config.site_dir, "search", "search_index.json")
                else:
                    path = os.path.join(config.site_dir, locale, "search", "search_index.json")
                utils.write_file(data.encode("utf-8"), path)
                if self.is_dirty:
                    self.search_indices_prev[locale] = index
        else:
            base = os.path.join(config.site_dir, "search")
            path = os.path.join(base, "search_index.json")
            data = self.search_index.generate_search_index(self.search_index_prev)
            utils.write_file(data.encode("utf-8"), path)
            if self.is_dirty:
                self.search_index_prev = self.search_index

    def on_serve(self, server, *, config, builder):
        self.is_dirtyreload = self.is_dirty

    def _translate(self, config, value):
        env = config.theme.get_env()
        language = "partials/language.html"
        template = env.get_template(language, None, {"config": config})
        return template.module.t(value)


# Search index
class SearchIndex:
    """Lunr.js compatible search index."""

    def __init__(self, **config):
        self.config = config
        self.entries = []
        self.needs_jieba = _needs_jieba(config)

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

        if self.needs_jieba:
            jieba_lib = _get_jieba()
            if jieba_lib:
                title = self._segment_chinese(title)
                text = self._segment_chinese(text)

        entry = {
            "location": url,
            "title": title,
            "text": text
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
            path = self.entries[0]["location"].split("#")[0]
            entries = [
                entry for entry in prev.entries
                if entry["location"].split("#")[0] != path
            ]
            self.entries = entries + self.entries

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

    def _segment_chinese(self, data):
        expr = bre.compile(r"(\p{script: Han}+)", bre.UNICODE)

        jieba_lib = _get_jieba()
        if not jieba_lib:
            return data

        def replace(match):
            value = match.group(0)
            return "".join([
                "\u200b",
                "\u200b".join(jieba_lib.cut(value)),
                "\u200b",
            ])

        return expr.sub(replace, data).strip("\u200b")


# HTML parser for search index
class Element:
    """HTML element with attributes."""

    def __init__(self, tag, attrs=None):
        self.tag = tag
        self.attrs = attrs or {}

    def __repr__(self):
        return self.tag

    def __eq__(self, other):
        if other is Element:
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
        self.skip = {"object", "script", "style"}
        self.keep = {"p", "code", "pre", "li", "ol", "ul", "sub", "sup"}
        self.context = []
        self.section = None
        self.data = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        el = Element(tag, attrs)
        if tag not in void:
            self.context.append(el)
        else:
            return

        if tag in [f"h{x}" for x in range(1, 7)]:
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
                self.skip.add(el)
                return
            if key == "class" and value == "linenodiv":
                self.skip.add(el)
                return

        if not self.skip.intersection(self.context) and tag in self.keep:
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
        if el in self.skip:
            if el.tag not in ["script", "style", "object"]:
                self.skip.remove(el)
            return

        if not self.skip.intersection(self.context) and tag in self.keep:
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
        if self.skip.intersection(self.context):
            return

        if "pre" not in self.context:
            if not data.isspace():
                data = data.replace("\n", " ")
            else:
                data = " "

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
            if not self.section.text or not self.section.text[-1].isspace():
                self.section.text.append(data)
            elif "pre" in self.context:
                self.section.text.append(data)
        else:
            self.section.text.append(escape(data, quote=False))


# Self-closing tags
void = {
    "area", "base", "br", "col", "embed", "hr", "img",
    "input", "link", "meta", "param", "source", "track", "wbr"
}

log = logging.getLogger("docsforge.search")
