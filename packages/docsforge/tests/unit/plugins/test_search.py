"""Unit tests for the search plugin (docsforge.core.search).

Focuses on the pure-logic pieces: SearchIndex entry creation, tag extraction,
the jieba gating, and the incremental-prev merge. No network.
"""
from __future__ import annotations

from types import SimpleNamespace

from docsforge.core.search import SearchIndex


def _page(content, url="page/", title="T", meta=None):
    p = SimpleNamespace()
    p.content = content
    p.url = url
    p.title = title
    p.toc = []
    p.meta = meta or {}
    return p


def _full_config(**overrides):
    """SearchIndex.generate_search_index reads lang/separator/pipeline/fields."""
    cfg = {
        "lang": ["en"],
        "separator": " ",
        "pipeline": ["stemmer", "stopWordFilter", "trimmer"],
        "fields": {},
    }
    cfg.update(overrides)
    return cfg


class TestSearchIndex:
    def test_add_entry_from_context_captures_text(self):
        idx = SearchIndex()
        page = _page("<h1>Hello</h1><p>world of docs</p>", url="hello/")
        idx.add_entry_from_context(page)
        assert len(idx.entries) >= 1
        joined = " ".join(e["text"] for e in idx.entries)
        assert "world" in joined

    def test_excluded_page_yields_no_entry(self):
        idx = SearchIndex()
        page = _page("<p>x</p>", meta={"search": {"exclude": True}})
        idx.add_entry_from_context(page)
        assert idx.entries == []

    def test_entry_location_uses_page_url(self):
        idx = SearchIndex()
        idx.add_entry_from_context(_page("<p>body</p>", url="foo/bar/"))
        assert all(e["location"].startswith("foo/bar") for e in idx.entries)

    def test_tags_from_meta_propagated_to_entry(self):
        idx = SearchIndex()
        page = _page("<p>body</p>", meta={"tags": ["python", "docs", 3]})
        idx.add_entry_from_context(page)
        flat = [e for e in idx.entries if "tags" in e]
        assert flat, "no entry carried tags"
        tags = flat[0]["tags"]
        assert "python" in tags and "docs" in tags
        assert "3" in tags  # numeric tags stringified

    def test_boost_from_meta(self):
        idx = SearchIndex()
        page = _page("<p>body</p>", meta={"search": {"boost": 5}})
        idx.add_entry_from_context(page)
        assert any(e.get("boost") == 5 for e in idx.entries)

    def test_generate_search_index_emits_config_and_docs(self):
        import json

        idx = SearchIndex(**_full_config())
        idx.add_entry_from_context(_page("<p>body</p>", url="p/"))
        data = json.loads(idx.generate_search_index(prev=None))
        assert "config" in data and "docs" in data
        assert data["config"]["lang"] == ["en"]
        assert isinstance(data["docs"], list)

    def test_needs_jieba_only_for_zh(self):
        assert SearchIndex(lang="zh").needs_jieba is True
        assert SearchIndex(lang="zh-CN").needs_jieba is True
        assert SearchIndex(lang="en").needs_jieba is False
        assert SearchIndex(jieba_dict="d.txt").needs_jieba is True
        assert SearchIndex().needs_jieba is False

    def test_prev_preserved_when_no_new_entries(self):
        import json

        prev = SearchIndex(**_full_config())
        prev.add_entry_from_context(_page("<p>old</p>", url="old/"))
        idx = SearchIndex(**_full_config())
        data = json.loads(idx.generate_search_index(prev=prev))
        # no new entries -> prev entries carried forward
        assert any(e["location"].startswith("old") for e in data["docs"])
