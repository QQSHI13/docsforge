"""Unit tests for the search plugin (docsforge.core.search).

Focuses on the pure-logic pieces: SearchIndex entry creation, tag extraction,
the Marz binary export, and the incremental-prev merge. No network.
"""
from __future__ import annotations

from types import SimpleNamespace

from docsforge.core.search import Element, SearchConfig, SearchIndex


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

    def test_generate_marz_index_roundtrips_entries(self):
        import marz

        idx = SearchIndex(**_full_config())
        idx.add_entry_from_context(_page("<h1>Guide</h1><p>body words here</p>", url="p/"))
        raw = idx.generate_marz_index()
        assert isinstance(raw, bytes) and len(raw) > 64  # past the header
        loaded = marz.Index.from_bytes(raw)
        refs = [h.ref for h in loaded.search("words")]
        assert any(r.startswith("p/") for r in refs)

    def test_generate_marz_index_uses_raw_cjk_text(self):
        import marz

        cfg = _full_config(lang=["ja"])
        idx = SearchIndex(**cfg)
        idx.add_entry_from_context(_page("<p>検索エンジン</p>", url="p/"))
        # No zero-width segmentation joiners: raw text is indexed as-is.
        assert all("\u200b" not in e["text"] for e in idx.entries)
        loaded = marz.Index.from_bytes(idx.generate_marz_index())
        assert any(h.ref.startswith("p/") for h in loaded.search("検索エンジン"))

    def test_generate_marz_index_applies_boosts(self):
        import marz

        idx = SearchIndex(**_full_config())
        idx.add_entry_from_context(_page("<p>same words here</p>", url="a/",
                                         meta={"search": {"boost": 9}}))
        idx.add_entry_from_context(_page("<p>same words here</p>", url="b/"))
        loaded = marz.Index.from_bytes(idx.generate_marz_index())
        refs = [h.ref for h in loaded.search("words")]
        assert refs and refs[0].startswith("a/")
    def test_generate_marz_index_tolerates_bad_boosts(self):
        idx = SearchIndex(**_full_config())
        idx.entries = [
            {"location": "a/", "title": "t", "text": "w", "boost": "junk"},
            {"location": "b/", "title": "t", "text": "w", "boost": float("inf")},
        ]
        raw = idx.generate_marz_index()
        assert isinstance(raw, bytes)

    def test_generate_marz_index_maps_empty_location_to_root_ref(self):
        import marz

        from docsforge.core.search import MARZ_ROOT_REF

        idx = SearchIndex(**_full_config())
        idx.entries = [{"location": "", "title": "Home", "text": "welcome words here"}]
        loaded = marz.Index.from_bytes(idx.generate_marz_index())
        refs = [h.ref for h in loaded.search("welcome")]
        assert refs == [MARZ_ROOT_REF]
        assert MARZ_ROOT_REF != ""

    def test_element_eq_compares_tag_with_other_element(self):
        assert Element("div") == Element("div")
        assert Element("div") != Element("span")
        assert Element("div") != "span"
        assert Element("div") == "div"

    def test_search_config_lang_accepts_list_of_strings(self):
        cfg = SearchConfig()
        cfg.load_dict({"lang": ["en", "zh-CN"]})
        failed, _ = cfg.validate()
        assert not failed
        assert cfg["lang"] == ["en", "zh-CN"]

    def test_search_config_lang_rejects_scalar_string(self):
        cfg = SearchConfig()
        cfg.load_dict({"lang": "en"})
        failed, _ = cfg.validate()
        assert failed

    def test_dirty_reload_dedup_matches_full_page_path(self):
        import json

        prev = SearchIndex(**_full_config())
        prev.add_entry_from_context(_page("<p>foo</p>", url="foo/"))
        prev.add_entry_from_context(_page("<p>foobar</p>", url="foobar/"))

        idx = SearchIndex(**_full_config())
        idx.add_entry_from_context(_page("<p>new foo</p>", url="foo/"))
        data = json.loads(idx.generate_search_index(prev=prev))

        locations = [e["location"] for e in data["docs"]]
        assert any(loc.startswith("foo/") for loc in locations)
        assert any(loc.startswith("foobar/") for loc in locations)

    def test_prev_preserved_when_no_new_entries(self):
        import json

        prev = SearchIndex(**_full_config())
        prev.add_entry_from_context(_page("<p>old</p>", url="old/"))
        idx = SearchIndex(**_full_config())
        data = json.loads(idx.generate_search_index(prev=prev))
        # no new entries -> prev entries carried forward
        assert any(e["location"].startswith("old") for e in data["docs"])
