"""Tests for the canonical heading-slug rules exported to the Studio extension."""

from __future__ import annotations

import json

import pytest
from markdown.extensions.toc import slugify as toc_slugify
from markdown.extensions.toc import slugify_unicode as toc_slugify_unicode

from docsforge.build import _slug_rules_from_config
from docsforge.slugger import RULES_VERSION, SlugRules, compute_rules, slugify

# Headings a real site contains: CJK, accented latin, punctuation, awkward
# separator edges (which the collapse regex leaves alone) and underscores.
HEADINGS = [
    "Installation",
    "Quick Start!",
    "Über uns",
    "naïve café",
    "中文标题测试",
    "混合 CJK and English 标题",
    "Foo-",
    "- Foo",
    "a - ",
    "--x--",
    "snake_case_heading",
    "__dunder__",
    "1.0 release (2026-10-28)",
    "a   b",
    "",
]


@pytest.mark.parametrize("title", HEADINGS)
def test_slugify_matches_engine(title: str) -> None:
    """Our slugify must agree with the engine's toc slugify, byte for byte."""
    assert slugify(title) == toc_slugify(title, "-")
    assert slugify(title, compute_rules(separator="_")) == toc_slugify(title, "_")


def test_compute_rules_defaults_match_stock_toc() -> None:
    rules = compute_rules()
    assert rules == SlugRules(
        separator="-",
        unicode=False,
        char_class="word",
        predictable=True,
        version=RULES_VERSION,
    )
    # The defaults must describe the stock slugify, not slugify_unicode.
    assert slugify("Über uns") == toc_slugify("Über uns", "-")
    assert slugify("中文标题", compute_rules(unicode=True)) != slugify("中文标题")


def test_compute_rules_carries_separator_and_unicode() -> None:
    rules = compute_rules(separator="_", unicode=False)
    assert rules.separator == "_"
    assert rules.unicode is False
    assert slugify("a b", rules) == toc_slugify("a b", "_")


def test_slug_rules_json_round_trip() -> None:
    rules = compute_rules(separator="+", unicode=True, predictable=False)
    assert SlugRules(**json.loads(rules.to_json())) == rules


def test_custom_slugify_is_unpredictable() -> None:
    """A custom toc.slugify cannot be described by parameters."""
    stock = _slug_rules_from_config({"mdx_configs": {"toc": {}}})
    assert (stock.separator, stock.unicode, stock.predictable) == ("-", False, True)

    unicode_rules = _slug_rules_from_config({"mdx_configs": {"toc": {"slugify": toc_slugify_unicode}}})
    assert (unicode_rules.unicode, unicode_rules.predictable) == (True, True)

    underscore = _slug_rules_from_config({"mdx_configs": {"toc": {"separator": "_"}}})
    assert (underscore.separator, underscore.unicode, underscore.predictable) == ("_", False, True)

    custom = _slug_rules_from_config({"mdx_configs": {"toc": {"slugify": lambda v, s: v}}})
    assert custom.predictable is False
