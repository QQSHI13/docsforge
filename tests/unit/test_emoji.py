"""Unit tests for docsforge.emoji (twemoji vendoring)."""
from __future__ import annotations

from docsforge import emoji as emoji_mod


class FakeStash:
    """Minimal stand-in for markdown.util.HtmlStash."""

    def __init__(self):
        self.items = []

    def store(self, content):
        self.items.append(content)
        return ""

    def getvalue(self):
        return "".join(self.items)


class FakeMd:
    def __init__(self):
        self.htmlStash = FakeStash()


def _render(uc, shortname=":smile:"):
    md = FakeMd()
    el = emoji_mod.to_svg("twemoji", shortname, None, uc, "alt", None, "symbols", {}, md)
    return el, md.htmlStash.getvalue()


class TestUnicodeEmoji:
    def test_inlines_vendored_svg(self):
        el, svg = _render("1f604")  # :smile:
        assert el.tag == "span"
        assert el.attrib["class"] == "twemoji"
        assert "<svg" in svg
        assert "cdn.jsdelivr" not in svg
        assert "twemoji.maxcdn" not in svg

    def test_multi_codepoint_inlines_vendored_svg(self):
        el, svg = _render("1f1fa-1f1f8")  # :us:
        assert el.tag == "span"
        assert "<svg" in svg
        assert svg.startswith("<svg xmlns")

    def test_unknown_codepoint_falls_back_to_pymdownx(self):
        el, _svg = _render("ffffff")  # not part of the vendored set
        assert el.tag == "img"
        assert "ffffff.svg" in el.attrib["src"]


class TestFindTwemoji:
    def test_returns_vendored_path_for_known_codepoint(self):
        path = emoji_mod._find_twemoji_svg("1f604")
        assert path is not None
        assert path.endswith("1f604.svg")

    def test_returns_none_for_unknown_codepoint(self):
        assert emoji_mod._find_twemoji_svg("ffffff") is None
