"""Verify the example plugins (examples/plugins/) load and behave correctly.

These guard the plugin authoring contract: the examples double as
documentation, so a broken example would mislead users.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

EXAMPLES = Path(__file__).resolve().parents[2] / "examples" / "plugins"
HOOKS = Path(__file__).resolve().parents[2] / "examples" / "hooks"

# Module names injected into sys.modules by this test file.
_LOADED_MODULE_NAMES: list[str] = []


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    _LOADED_MODULE_NAMES.append(name)
    try:
        spec.loader.exec_module(module)  # type: ignore[union-attr]
    except Exception:
        sys.modules.pop(name, None)
        _LOADED_MODULE_NAMES.remove(name)
        raise
    return module


@pytest.fixture(autouse=True)
def _cleanup_example_modules():
    yield
    for name in _LOADED_MODULE_NAMES:
        sys.modules.pop(name, None)
    _LOADED_MODULE_NAMES.clear()


def test_reading_time_plugin():
    mod = _load_module("reading_time_ex", EXAMPLES / "reading-time" / "reading_time" / "__init__.py")
    p = mod.ReadingTimePlugin()
    p.load_config({"wpm": 100})
    ctx: dict = {}
    page = SimpleNamespace(markdown="one two three four five")
    p.on_page_context(ctx, page=page, config=None, nav=None)
    assert ctx["reading_time"] == 1  # 5 words / 100 wpm

    # Long page rounds up.
    page2 = SimpleNamespace(markdown=" ".join("word" for _ in range(250)))
    ctx2: dict = {}
    p.on_page_context(ctx2, page=page2, config=None, nav=None)
    assert ctx2["reading_time"] >= 2


def test_last_modified_plugin(tmp_path: Path):
    mod = _load_module("last_modified_ex", EXAMPLES / "last-modified" / "last_modified" / "__init__.py")
    p = mod.LastModifiedPlugin()
    p.load_config({"date_format": "%Y-%m-%d"})
    src = tmp_path / "page.md"
    src.write_text("# hi")
    page = SimpleNamespace(file=SimpleNamespace(abs_src_path=str(src)), meta={})
    out = p.on_page_markdown("body", page=page, config=None, files=None)
    assert out == "body"  # markdown unchanged
    assert page.meta["last_modified"]  # a date string was set
    # Missing source path -> no crash, markdown unchanged.
    page2 = SimpleNamespace(file=SimpleNamespace(abs_src_path="/nope/missing.md"), meta={})
    assert p.on_page_markdown("x", page=page2, config=None, files=None) == "x"


def test_hook_draft_banner():
    mod = _load_module("draft_banner_ex", HOOKS / "hook_draft_banner.py")
    # Draft path -> banner prepended.
    page_draft = SimpleNamespace(file=SimpleNamespace(src_uri="drafts/wip.md"))
    out = mod.on_page_markdown("body", page=page_draft, config=None, files=None)
    assert "DRAFT" in out and out.endswith("body")
    # Non-draft path -> unchanged.
    page_final = SimpleNamespace(file=SimpleNamespace(src_uri="guide/intro.md"))
    assert mod.on_page_markdown("body", page=page_final, config=None, files=None) == "body"


def test_custom_filter_plugin():
    from jinja2 import Environment

    mod = _load_module(
        "custom_filter_ex",
        EXAMPLES / "custom-filter" / "custom_filter" / "__init__.py",
    )
    p = mod.CustomFilterPlugin()
    p.load_config({})
    env = Environment()
    p.on_env(env, config=None, files=None)
    assert env.filters["pluralize"](1, "comment") == "comment"
    assert env.filters["pluralize"](3, "comment") == "comments"
    assert env.filters["pluralize"](3, "person", "people") == "people"
    # Renders through a real template.
    tmpl = env.from_string("{{ n }} {{ n | pluralize('comment') }}")
    assert tmpl.render(n=5) == "5 comments"
