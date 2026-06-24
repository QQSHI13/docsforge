"""Unit tests for the tags plugin Tag model (docsforge.core.tags)."""
from __future__ import annotations

import pytest

from docsforge.core.tags import Tag


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
