"""A rebuilt page must label its siblings with the *rendered* nav title.

`Page.title` prefers `_title_from_render`, which only `Page.render()` sets. An
incremental build renders just the dirty pages, so before this was fixed every
other page fell back to a naive `# ` scan (or the filename). A rebuilt page then
labelled its siblings wrongly — e.g. a setext heading (`Title\n====`) was shown
as the filename — while untouched pages kept the correct label, so one site
displayed different nav labels depending on which page you were on.

The fix persists the rendered title per page and seeds it back for pages the
build skips.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

import pytest

from docsforge.build import build
from docsforge.config_base import load_config

pytestmark = pytest.mark.slow

NAV_TITLE = "工具"
WRONG_TITLE = "Others"  # filename fallback for others.md


def _build_once(project: Path, caplog) -> int:
    """Run one build; return how many pages it rendered.

    The count is the test's precondition, not decoration: a build that renders
    EVERY page derives every title from a real render, so it passes with or
    without the fix. Only a build that renders a single page exercises the
    incremental path, where skipped pages must get their title from cache.
    """
    cfg = load_config(config_file=str(project / "docsforge.yml"))
    cfg.plugins.on_startup(command="build", dirty=True)
    # A build that renders nothing logs no "Rendering N pages" line at all, so
    # stale records from an earlier build would be read as this build's count.
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="docsforge"):
        try:
            build(cfg, dirty=True)
        finally:
            cfg.plugins.on_shutdown()
    for record in reversed(caplog.records):
        match = re.search(r"Rendering (\d+) pages", record.getMessage())
        if match:
            return int(match.group(1))
    return 0


def _write_project(root: Path, monkeypatch) -> None:
    docs = root / "docs"
    docs.mkdir(parents=True)
    (docs / "index.md").write_text("# Home\n")
    # Setext H1: the `# ` scan misses it, `Page.render()` finds it.
    (docs / "others.md").write_text(f"{NAV_TITLE}\n====\n\n正文内容。\n")
    (docs / "a.md").write_text("# Page A\n\ncontent a\n")
    (docs / "b.md").write_text("# Page B\n\ncontent b\n")
    (root / "docsforge.yml").write_text(
        "site_name: T\nsite_url: https://example.com/\n"
        "theme:\n  name: material\n  font: false\n"
        "offline:\n  mode: none\n"
        # Hermetic: CACHE_DIR is a relative path, and privacy would otherwise
        # try to fetch mermaid from unpkg (5s timeout per attempt).
        "privacy: false\n"
    )
    # The build cache lives at the relative path `.docsforge/cache`, so the
    # process must run inside the project or it reads the repo's own cache.
    monkeypatch.chdir(root)


def _nav_titles(html: str) -> set[str]:
    """Titles appearing as a sidebar nav label in the rendered page.

    Tolerant of minification: with the minifier active, attribute quotes are
    stripped (`class=md-ellipsis`); on interpreters without a `minify-go` wheel
    they are kept (`class="md-ellipsis"`). Matching the raw marker only would
    pass on one and fail on the other.
    """
    out = set()
    for match in re.finditer(r"""md-ellipsis["']?>([^<]*)""", html):
        out.add(match.group(1))
    return out


def _touch(project: Path, name: str, text: str) -> None:
    with (project / "docs" / name).open("a", encoding="utf-8") as fh:
        fh.write(text)


def test_rebuilt_page_uses_rendered_title_for_siblings(tmp_path, caplog, monkeypatch):
    _write_project(tmp_path, monkeypatch)

    # Cold build: every page is rendered, so the setext title is exact.
    assert _build_once(tmp_path, caplog) == 4

    # A no-op build must render nothing. This is also the regression guard for
    # a bug the title cache introduced: the nav signature was computed BEFORE
    # the render phase, from fallback titles, so saving it made the next build
    # disagree and re-render every page a second time.
    assert _build_once(tmp_path, caplog) == 0

    # Touch b.md: exactly one page is rendered, and its nav must still label
    # the untouched setext page with the rendered title, not the filename.
    _touch(tmp_path, "b.md", "\n<!-- changed -->\n")
    assert _build_once(tmp_path, caplog) == 1

    titles = _nav_titles((tmp_path / "site" / "b" / "index.html").read_text(encoding="utf-8"))
    assert NAV_TITLE in titles
    assert WRONG_TITLE not in titles


def test_rendered_title_survives_repeated_incremental_builds(tmp_path, caplog, monkeypatch):
    _write_project(tmp_path, monkeypatch)
    _build_once(tmp_path, caplog)

    for i in range(3):
        _touch(tmp_path, "b.md", f"\n<!-- change {i} -->\n")
        assert _build_once(tmp_path, caplog) == 1, f"rebuild {i} was not incremental"
        titles = _nav_titles(
            (tmp_path / "site" / "b" / "index.html").read_text(encoding="utf-8")
        )
        assert NAV_TITLE in titles, f"lost rendered title on rebuild {i}"
        assert WRONG_TITLE not in titles, f"filename fallback leaked on rebuild {i}"


def test_frontmatter_title_still_wins_over_cache(tmp_path, caplog, monkeypatch):
    """A frontmatter edit must take effect even with a cached rendered title."""
    _write_project(tmp_path, monkeypatch)
    _build_once(tmp_path, caplog)

    # Frontmatter is read from source every build and outranks both the cache
    # and `_title_from_render`.
    (tmp_path / "docs" / "others.md").write_text("---\ntitle: 前置标题\n---\n\n正文。\n")
    _touch(tmp_path, "b.md", "\n<!-- changed -->\n")
    _build_once(tmp_path, caplog)

    titles = _nav_titles((tmp_path / "site" / "b" / "index.html").read_text(encoding="utf-8"))
    assert "前置标题" in titles
