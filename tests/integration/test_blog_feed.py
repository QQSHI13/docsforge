"""Blog RSS/Atom feed generation (on_post_build)."""
from __future__ import annotations

import textwrap
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest


def _write_project(root: Path, site_url: str = "https://example.com/") -> None:
    docs = root / "docs"
    docs.mkdir(parents=True)
    (docs / "index.md").write_text("# Home\n")
    blog = docs / "blog"
    blog.mkdir()
    (blog / "index.md").write_text("# Blog\n")
    (blog / ".authors.yml").write_text(
        "authors:\n  qq:\n    name: QQ\n    description: author\n    avatar: https://example.com/q.png\n"
    )
    posts = blog / "posts"
    posts.mkdir()
    (posts / "2026-01-01-first.md").write_text(
        "---\ndate: 2026-01-01\nauthors: [qq]\n---\n# First Post\n\nHello **world** & more.\n"
    )
    (posts / "2026-01-02-second.md").write_text(
        "---\ndate: 2026-01-02\nauthors: [qq]\n---\n# Second\n"
    )
    (root / "docsforge.yml").write_text(
        textwrap.dedent(
            f"""
            site_name: My Blog
            site_url: {site_url}
            site_description: Test desc
            docs_dir: docs
            site_dir: site
            privacy: false
            theme:
              name: material
            """
        )
    )


def _build(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from docsforge.build import build
    from docsforge.config_base import load_config

    monkeypatch.chdir(root)
    cfg = load_config(config_file=str(root / "docsforge.yml"))
    cfg.plugins.on_startup(command="build", dirty=True)
    try:
        build(cfg, dirty=True)
    finally:
        cfg.plugins.on_shutdown()


class TestBlogFeed:
    def test_feeds_generated_and_valid(self, tmp_path, monkeypatch):
        root = tmp_path / "proj"
        _write_project(root)
        _build(root, monkeypatch)

        rss = root / "site" / "blog" / "feed_rss_created.xml"
        atom = root / "site" / "blog" / "feed_atom.xml"
        assert rss.is_file() and atom.is_file()

        rss_tree = ET.parse(rss)
        rss_root = rss_tree.getroot()
        assert rss_root.tag == "rss"
        channel = rss_root.find("channel")
        assert channel.findtext("title") == "Blog"
        assert channel.findtext("link") == "https://example.com/blog/"
        items = channel.findall("item")
        assert len(items) == 2
        # newest first
        assert items[0].findtext("title") == "Second"
        assert items[1].findtext("title") == "First Post"
        # RFC 1123 pubDate
        assert items[0].findtext("pubDate").startswith("Fri, 02 Jan 2026")
        # author display name, not the key
        assert items[0].findtext("author") == "QQ"
        # absolute post links
        assert items[1].findtext("link") == "https://example.com/blog/2026/01/01/first-post/"

        atom_root = ET.parse(atom).getroot()
        assert atom_root.tag.endswith("feed")
        entries = atom_root.findall("{http://www.w3.org/2005/Atom}entry")
        assert len(entries) == 2

    def test_feed_disabled_via_config(self, tmp_path, monkeypatch):
        root = tmp_path / "proj"
        _write_project(root)
        cfg_path = root / "docsforge.yml"
        cfg_path.write_text(
            cfg_path.read_text()
            + "plugins:\n  - blog:\n      feed: false\n"
        )
        _build(root, monkeypatch)
        assert not (root / "site" / "blog" / "feed_rss_created.xml").exists()
        assert not (root / "site" / "blog" / "feed_atom.xml").exists()

    def test_drafts_excluded_from_feed(self, tmp_path, monkeypatch):
        root = tmp_path / "proj"
        _write_project(root)
        (root / "docs" / "blog" / "posts" / "2026-01-03-draft.md").write_text(
            "---\ndate: 2026-01-03\ndraft: true\n---\n# Draft\n"
        )
        _build(root, monkeypatch)
        rss = ET.parse(root / "site" / "blog" / "feed_rss_created.xml").getroot()
        titles = [i.findtext("title") for i in rss.find("channel").findall("item")]
        assert "Draft" not in titles
