"""Incremental-build regression: the blog entrypoint must re-render when the
post set changes, even though its own source file is unchanged.

The entrypoint (blog/index.md) lists every post, so adding, editing, or
removing a post has to force a re-render on incremental builds. This is
implemented via the `on_page_deps` plugin event + `BuildPlanner.deps_changed`.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest


def _write_project(root: Path, posts: dict[str, str]) -> None:
    docs = root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "index.md").write_text("# Home\n")
    blog = docs / "blog"
    blog.mkdir(exist_ok=True)
    (blog / "index.md").write_text("# Blog\n")
    posts_dir = blog / "posts"
    posts_dir.mkdir(exist_ok=True)
    for name, body in posts.items():
        (posts_dir / name).write_text(body)
    (root / "docsforge.yml").write_text(
        textwrap.dedent(
            """
            site_name: Blog Test
            docs_dir: docs
            site_dir: site
            privacy: false
            theme:
              name: material
            """
        )
    )


def _build(root: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    from docsforge.build import build
    from docsforge.config_base import load_config

    monkeypatch.chdir(root)
    cfg = load_config(config_file=str(root / "docsforge.yml"))
    cfg.plugins.on_startup(command="build", dirty=True)
    try:
        build(cfg, dirty=True)
    finally:
        cfg.plugins.on_shutdown()
    return (root / "site" / "blog" / "index.html").read_text()


_POST = "---\ndate: {date}\n---\n# {title}\n"


class TestBlogIncremental:
    def test_blog_index_updates_on_incremental_builds(self, tmp_path, monkeypatch):
        root = tmp_path / "proj"
        _write_project(
            root,
            {
                "2026-01-01-first.md": _POST.format(date="2026-01-01", title="First"),
                "2026-01-02-second.md": _POST.format(date="2026-01-02", title="Second"),
            },
        )

        # Initial build lists both posts.
        idx = _build(root, monkeypatch)
        assert "First" in idx and "Second" in idx

        # No-op incremental build must NOT rewrite the output.
        before = (root / "site" / "blog" / "index.html").stat().st_mtime_ns
        _build(root, monkeypatch)
        after = (root / "site" / "blog" / "index.html").stat().st_mtime_ns
        assert before == after

        # Adding a post must re-render the entrypoint.
        posts = root / "docs" / "blog" / "posts"
        (posts / "2026-01-03-third.md").write_text(
            _POST.format(date="2026-01-03", title="Third")
        )
        idx = _build(root, monkeypatch)
        assert "Third" in idx

        # Editing a post must be reflected (excerpt change).
        (posts / "2026-01-01-first.md").write_text(
            _POST.format(date="2026-01-01", title="First") + "\nEDITED-EXCERPT\n"
        )
        idx = _build(root, monkeypatch)
        assert "EDITED-EXCERPT" in idx

        # Removing a post must drop it from the listing.
        (posts / "2026-01-02-second.md").unlink()
        idx = _build(root, monkeypatch)
        assert "Second" not in idx
