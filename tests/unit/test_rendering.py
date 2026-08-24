"""Unit tests for docsforge.rendering."""
from __future__ import annotations

from xml.etree import ElementTree as etree

from docsforge.rendering import _extract_alt_texts, _remove_anchorlink, _strip_tags


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

    def test_preserves_literal_comparisons(self):
        # HTMLParser must not treat "< b >" as a tag.
        assert _strip_tags("<p>a < b > c</p>") == "a < b > c"


class TestRemoveAnchorlink:
    def test_removes_last_anchorlink(self):
        el = etree.Element("h1")
        el.text = "Title"
        anchor = etree.SubElement(el, "a")
        anchor.set("class", "headerlink")
        anchor.tail = ""
        _remove_anchorlink(el)
        assert [child.tag for child in el] == []
        assert el.text == "Title"

    def test_removes_non_last_anchorlink(self):
        el = etree.Element("h1")
        el.text = "Title "
        anchor = etree.SubElement(el, "a")
        anchor.set("class", "headerlink")
        anchor.tail = " suffix "
        span = etree.SubElement(el, "span")
        span.text = "x"
        _remove_anchorlink(el)
        assert [child.tag for child in el] == ["span"]
        assert el.text == "Title  suffix "
        assert span.text == "x"

    def test_leaves_non_headerlink_anchors(self):
        el = etree.Element("h1")
        el.text = "Title "
        anchor = etree.SubElement(el, "a")
        anchor.set("class", "external")
        anchor.tail = ""
        _remove_anchorlink(el)
        assert [child.tag for child in el] == ["a"]


class TestExtractAltTexts:
    def test_replaces_image_with_alt_text(self):
        img = etree.Element("img")
        img.set("alt", "description")
        parent = etree.Element("p")
        parent.text = "before "
        parent.append(img)
        img.tail = " after"
        _extract_alt_texts(parent)
        assert [child.tag for child in parent] == []
        assert parent.text == "before description after"

    def test_replaces_image_with_empty_alt_text(self):
        img = etree.Element("img")
        img.set("alt", "")
        parent = etree.Element("p")
        parent.text = "before "
        parent.append(img)
        img.tail = " after"
        _extract_alt_texts(parent)
        assert [child.tag for child in parent] == []
        assert parent.text == "before  after"

    def test_leaves_image_without_alt_attribute(self):
        img = etree.Element("img")
        parent = etree.Element("p")
        parent.text = "before "
        parent.append(img)
        img.tail = " after"
        _extract_alt_texts(parent)
        assert [child.tag for child in parent] == ["img"]
        assert parent.text == "before "
        assert img.tail == " after"
