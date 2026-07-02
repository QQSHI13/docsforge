"""End-to-end build tests against a real (throwaway) fixture site.

These exercise the full build.py pipeline: config load, markdown render,
theme templates, search index, PWA manifest, cache manifest, and the
incremental cache. They are slower than the unit tests but catch the
classes of regressions that shipped in v11.1.2/v11.1.3.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow


def _build_once(monkeypatch, cwd: Path) -> None:
    from docsforge.config_base import load_config
    from docsforge.build import build

    monkeypatch.chdir(cwd)
    cfg = load_config(config_file=str(cwd / "docsforge.yml"))
    cfg.plugins.on_startup(command="build", dirty=True)
    try:
        build(cfg, dirty=True)
    finally:
        cfg.plugins.on_shutdown()


class TestBuildE2E:
    def test_builds_all_pages_to_html(self, tmp_project, monkeypatch):
        _build_once(monkeypatch, tmp_project)
        site = tmp_project / "site"
        assert (site / "index.html").is_file()
        html = (site / "index.html").read_text()
        assert "<html" in html.lower()
        assert "Test Site" in html

    def test_generates_sitemap(self, tmp_project, monkeypatch):
        _build_once(monkeypatch, tmp_project)
        assert (tmp_project / "site" / "sitemap.xml").is_file()

    def test_generates_pwa_manifest(self, tmp_project, monkeypatch):
        _build_once(monkeypatch, tmp_project)
        m = json.loads((tmp_project / "site" / "manifest.json").read_text())
        assert m["name"] == "Test Site"
        assert "start_url" in m

    def test_generates_cache_manifest(self, tmp_project, monkeypatch):
        _build_once(monkeypatch, tmp_project)
        cm = json.loads((tmp_project / "site" / "cache-manifest.json").read_text())
        assert "version" in cm
        assert "files" in cm
        assert "Files" not in cm  # regression guard

    def test_second_build_is_incremental(self, tmp_project, monkeypatch):
        """The second build must not rewrite an unchanged page's output."""
        _build_once(monkeypatch, tmp_project)
        out = tmp_project / "site" / "index.html"
        mtime_before = out.stat().st_mtime_ns
        _build_once(monkeypatch, tmp_project)
        mtime_after = out.stat().st_mtime_ns
        assert mtime_after == mtime_before, "unchanged page was rewritten"

    def test_editing_md_triggers_rebuild(self, tmp_project, monkeypatch):
        _build_once(monkeypatch, tmp_project)
        out = tmp_project / "site" / "index.html"
        before = out.stat().st_mtime_ns
        time.sleep(0.01)
        (tmp_project / "docs" / "index.md").write_text("# Home\n\nEdited content.\n")
        _build_once(monkeypatch, tmp_project)
        after = out.stat().st_mtime_ns
        assert after > before, "edited page was not rebuilt"

    def test_deleting_md_removes_output(self, tmp_project, monkeypatch):
        extra = tmp_project / "docs" / "extra.md"
        extra.write_text("# Extra\n")
        _build_once(monkeypatch, tmp_project)
        assert (tmp_project / "site" / "extra" / "index.html").is_file()
        extra.unlink()
        _build_once(monkeypatch, tmp_project)
        assert not (tmp_project / "site" / "extra" / "index.html").is_file()

    def test_snippet_include_change_triggers_rebuild(self, tmp_project_with_include, monkeypatch):
        """The v11.1.4 feature, end-to-end: editing an included snippet must
        rebuild the page that includes it."""
        root, page, inc = tmp_project_with_include
        _build_once(monkeypatch, root)
        out = root / "site" / "page" / "index.html"
        assert out.is_file()
        before = out.stat().st_mtime_ns
        time.sleep(0.01)
        inc.write_text("# Included Header\n\nCHANGED CONTENT\n")
        _build_once(monkeypatch, root)
        after = out.stat().st_mtime_ns
        assert after > before, "editing an include did not rebuild the including page"

    def test_generates_service_worker_with_base_url(self, tmp_project, monkeypatch):
        _build_once(monkeypatch, tmp_project)
        sw = tmp_project / "site" / "sw.js"
        assert sw.is_file()
        content = sw.read_text()
        assert 'const BASE_URL = "/"' in content
        assert "__DOCSFORGE_BASE_URL__" not in content

    def test_service_worker_base_url_respects_subpath(self, tmp_project, monkeypatch):
        cfg = tmp_project / "docsforge.yml"
        cfg.write_text(cfg.read_text() + "site_url: https://example.com/docs/\n")
        _build_once(monkeypatch, tmp_project)
        sw = tmp_project / "site" / "sw.js"
        assert 'const BASE_URL = "/docs/"' in sw.read_text()

    def test_no_external_cdn_scripts_in_output(self, tmp_project, monkeypatch):
        """Hermetic check (privacy off): built HTML must not reference JS CDNs
        like unpkg/jsdelivr — those are vendored. Google Fonts <link>s are
        expected with privacy off and are allowed."""
        _build_once(monkeypatch, tmp_project)
        html = (tmp_project / "site" / "index.html").read_text()
        import re

        for url in re.findall(r'(?:src)=["\'](https?://[^"\']+)["\']', html):
            assert not any(h in url for h in ("unpkg.com", "cdn.jsdelivr", "cdnjs")), (
                f"unexpected CDN script in built page: {url}"
            )
