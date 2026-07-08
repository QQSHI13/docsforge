"""Unit tests for docsforge.rendering."""
from __future__ import annotations

import pytest

from docsforge.rendering import _strip_tags


class TestStripTags:
    def test_strips_simple_tags(self):
        assert _strip_tags("<p>Hello world</p>") == "Hello world"

    def test_strips_nested_tags(self):
        assert _strip_tags("<h1><strong>Bold</strong> title</h1>") == "Bold title"

    def test_preserves_entities(self):
        assert _strip_tags("<p>Foo &amp; Bar</p>") == "Foo &amp; Bar"

    def test_removes_comments(self):
        assert _strip_tags("a <!-- hidden --> b") == "a b"

    def test_collapses_whitespace(self):
        assert _strip_tags("<p>  a   b  </p>") == "a b"

    def test_handles_empty_string(self):
        assert _strip_tags("") == ""
