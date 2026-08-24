"""Unit tests for the tags plugin (docsforge.core.tags)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from docsforge.config_base import ValidationError
from docsforge.core.tags import (
    Listing,
    ListingConfig,
    ListingManager,
    ListingTree,
    Mapping,
    MappingManager,
    Tag,
    TagsConfig,
    TagSet,
    _mapping_from_json,
)
from docsforge.nav import Link
from docsforge.toc import AnchorLink, TableOfContents


class TestTagModel:
    def test_name_and_repr(self):
        assert Tag("python").name == "python"
        assert repr(Tag("python")) == "Tag('python')"
        assert str(Tag("python")) == "python"

    def test_equality_by_name(self):
        assert Tag("a") == Tag("a")
        assert Tag("a") != Tag("b")

    def test_hash_by_name(self):
        # tags with the same name must be interchangeable in sets/dicts
        assert hash(Tag("x")) == hash(Tag("x"))
        s = {Tag("x"), Tag("x"), Tag("y")}
        assert len(s) == 2

    def test_sorting_by_name(self):
        ordered = sorted([Tag("c"), Tag("a"), Tag("b")])
        assert [t.name for t in ordered] == ["a", "b", "c"]

    def test_iteration_walks_parents(self):
        root = Tag("lang")
        child = Tag("python", parent=root)
        names = [t.name for t in child]
        assert names == ["python", "lang"]

    def test_contains_checks_ancestry(self):
        root = Tag("lang")
        child = Tag("python", parent=root)
        assert root in child
        assert child not in root
        assert Tag("other") not in child

    def test_hidden_attribute(self):
        t = Tag("secret", hidden=True)
        assert t.hidden is True
        assert Tag("open").hidden is False


class TestListing:
    def test_iter_yields_listing_trees(self):
        listing = Listing(None, "id", ListingConfig())
        item = SimpleNamespace(url="page/", title="Page", file=None)
        listing.add(Mapping(item, tags=[Tag("a"), Tag("b")]))

        trees = list(listing)
        assert all(isinstance(tree, ListingTree) for tree in trees)
        assert {tree.tag.name for tree in trees} == {"a", "b"}


class TestTagSet:
    def test_allowed_tags_are_accepted(self):
        tag_set = TagSet(allowed=["a", "b"])
        assert tag_set.validate(["a", "b"]) == {"a", "b"}

    def test_disallowed_tags_raise_validation_error(self):
        tag_set = TagSet(allowed=["a", "b"])
        with pytest.raises(ValidationError):
            tag_set.validate(["a", "c"])


class TestMapping:
    def test_accepts_item_and_tags(self):
        link = Link("Title", "url/")
        mapping = Mapping(link, tags=[Tag("a"), Tag("b")])

        assert mapping.item is link
        assert mapping.page is link
        assert Tag("a") in mapping.tags
        assert Tag("b") in mapping.tags

    def test_from_json_deserializes_link_item(self):
        mapping = _mapping_from_json(
            {"item": {"url": "page/", "title": "Page"}, "tags": ["a", "b"]}
        )

        assert isinstance(mapping.item, Link)
        assert mapping.item.url == "page/"
        assert mapping.item.title == "Page"
        assert {tag.name for tag in mapping.tags} == {"a", "b"}


class TestMappingManager:
    def test_add_normalizes_non_string_tags(self):
        config = TagsConfig()
        manager = MappingManager(config)
        page = SimpleNamespace(
            url="page/",
            meta={"tags": ["a", 123, True]},
            file=SimpleNamespace(abs_src_path="/docs/page.md"),
        )

        mapping = manager.add(page, "")
        assert mapping is not None
        assert {tag.name for tag in mapping.tags} == {"a", "123", "True"}


class TestListingManager:
    @pytest.fixture()
    def renderer(self):
        return SimpleNamespace(render=lambda page, name, **kwargs: "")

    def _page(self, listing_id, content=None, toc=None):
        return SimpleNamespace(
            url="page/",
            title="Page",
            content=content or f'<h6 id="{listing_id}/slug"></h6>',
            toc=toc
            or TableOfContents([AnchorLink("listing", f"{listing_id}/slug", 6)]),
            file=SimpleNamespace(src_uri="page.md", abs_src_path="/docs/page.md"),
        )

    def test_slugify_uses_sensible_defaults(self):
        config = TagsConfig()
        manager = ListingManager(config)

        # Should not crash when tags_slugify_format and tags_slugify_separator
        # use their default values.
        assert manager._slugify(Tag("Hello World")) == "Hello-World"

    def test_sort_listing_tags_uses_sensible_default(self):
        config = TagsConfig()
        manager = ListingManager(config)
        children = {
            Tag("b"): ListingTree(Tag("b")),
            Tag("a"): ListingTree(Tag("a")),
        }

        # Should not crash when listings_tags_sort_by uses its default value.
        sorted_children = manager._sort_listing_tags(children)
        assert [tag.name for tag in sorted_children] == ["a", "b"]

    def test_populate_with_empty_listing_removes_injection_point(self, renderer):
        listing_id = "page.md:0-10"
        page = self._page(listing_id)
        listing = Listing(page, listing_id, ListingConfig())

        manager = ListingManager(TagsConfig())
        manager.data.add(listing)
        manager.populate(listing, [], renderer)

        # When no anchors are generated the injection point is replaced with
        # an empty string instead of None.
        assert page.content == ""

    def test_populate_with_tag_does_not_crash(self, renderer):
        listing_id = "page.md:0-20"
        page = self._page(listing_id)
        listing = Listing(page, listing_id, ListingConfig())

        item = SimpleNamespace(url="other/", title="Other", file=None)
        mapping = Mapping(item, tags=[Tag("Hello World")])
        listing.add(mapping)

        manager = ListingManager(TagsConfig())
        manager.data.add(listing)
        manager.populate(listing, [mapping], renderer)

        assert isinstance(page.content, str)
