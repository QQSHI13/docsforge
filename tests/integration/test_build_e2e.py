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

        files = cm["files"]
        # Pages are present with directory-index URLs.
        assert "./" in files, "homepage missing from cache manifest"
        assert any(k.endswith("/") for k in files), (
            "no directory-index pages in cache manifest"
        )
        assert "404.html" in files, "404 page missing from cache manifest"

        # Theme assets and the search index are now included so the SW can
        # cache everything without parsing HTML.
        assert any(k.startswith("assets/javascripts/bundle") for k in files), (
            "theme JS bundle missing from cache manifest"
        )
        assert any(k.startswith("assets/stylesheets/main") for k in files), (
            "theme CSS missing from cache manifest"
        )
        assert "assets/images/favicon.png" in files, (
            "favicon missing from cache manifest"
        )
        assert any(k.startswith("assets/javascripts/workers/search") for k in files), (
            "search worker missing from cache manifest"
        )

        # The SW should not cache itself or its own manifest.
        assert "sw.js" not in files, "sw.js must not be in cache manifest"
        assert "cache-manifest.json" not in files, (
            "cache-manifest.json must not be in cache manifest"
        )

        # Sizes map: exact byte count of every built file, matching disk.
        sizes = cm["sizes"]
        assert set(sizes.keys()) == set(files.keys()), (
            "sizes must cover exactly the manifest files"
        )
        for key, size in sizes.items():
            assert isinstance(size, int) and size > 0
        assert sizes["404.html"] == (tmp_project / "site" / "404.html").stat().st_size, (
            "size must be the exact built-file byte count"
        )

    def test_offline_mode_none_skips_sw_and_manifests(self, tmp_project, monkeypatch):
        """With offline.mode: none, no service worker or PWA artifacts are
        generated and pages carry no SW registration or manifest link."""
        cfg = tmp_project / "docsforge.yml"
        cfg.write_text(cfg.read_text() + "offline:\n  mode: none\n")
        _build_once(monkeypatch, tmp_project)
        site = tmp_project / "site"
        for missing in ("sw.js", "cache-manifest.json", "manifest.json"):
            assert not (site / missing).exists(), f"{missing} must not exist in none mode"
        assert not (site / "assets" / "javascripts" / "sw.js").exists()
        html = (site / "index.html").read_text()
        assert 'rel="manifest"' not in html
        assert "serviceWorker.register" not in html
        assert "'serviceWorker' in navigator" not in html

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
        # Minified worker: the injected base URL is a plain string literal.
        assert 'BASE_URL="/"' in content
        assert "__DOCSFORGE_BASE_URL__" not in content

    def test_service_worker_base_url_respects_subpath(self, tmp_project, monkeypatch):
        cfg = tmp_project / "docsforge.yml"
        cfg.write_text(cfg.read_text() + "site_url: https://example.com/docs/\n")
        _build_once(monkeypatch, tmp_project)
        sw = tmp_project / "site" / "sw.js"
        assert 'BASE_URL="/docs/"' in sw.read_text()

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

    def test_nav_change_rebuilds_existing_pages(self, tmp_project, monkeypatch):
        """Changing a page title must re-render existing pages so navigation stays consistent."""
        cfg = tmp_project / "docsforge.yml"
        cfg.write_text(
            cfg.read_text()
            + "nav:\n  - path: index.md\n  - path: other.md\n"
        )
        (tmp_project / "docs" / "other.md").write_text("# Other\n\nOther content.\n")
        _build_once(monkeypatch, tmp_project)

        out = tmp_project / "site" / "index.html"
        before = out.stat().st_mtime_ns
        time.sleep(0.01)

        (tmp_project / "docs" / "other.md").write_text("# Renamed Other\n\nOther content.\n")
        _build_once(monkeypatch, tmp_project)

        after = out.stat().st_mtime_ns
        assert after > before, "existing page was not rebuilt after nav change"
        html = out.read_text()
        assert "Renamed Other" in html, "renamed page title missing from existing page navigation"

    def test_search_index_survives_empty_previous_index(self, tmp_project, monkeypatch):
        """If the on-disk search index is lost, an incremental build must regenerate it."""
        _build_once(monkeypatch, tmp_project)
        index_path = tmp_project / "site" / "search" / "search_index.json"
        assert index_path.is_file()
        original_count = len(json.loads(index_path.read_text())["docs"])
        assert original_count > 0

        # Simulate cache corruption / loss.
        index_path.write_text('{"config":{},"docs":[]}')
        cache_path = tmp_project / ".docsforge" / "cache" / "search_entries.json"
        if cache_path.exists():
            cache_path.unlink()

        _build_once(monkeypatch, tmp_project)
        recovered = json.loads(index_path.read_text())
        assert len(recovered["docs"]) == original_count, (
            "search index was not regenerated after previous index was emptied"
        )

    def test_search_index_incremental_update(self, tmp_project, monkeypatch):
        """Editing a page must update its entries in the search index without losing others."""
        _build_once(monkeypatch, tmp_project)
        index_path = tmp_project / "site" / "search" / "search_index.json"
        original = json.loads(index_path.read_text())

        time.sleep(0.01)
        (tmp_project / "docs" / "index.md").write_text(
            "# Home\n\nWelcome to the test site. UNIQUE_KEYWORD_FOR_SEARCH.\n"
        )
        _build_once(monkeypatch, tmp_project)

        updated = json.loads(index_path.read_text())
        assert any("UNIQUE_KEYWORD_FOR_SEARCH" in e.get("text", "") for e in updated["docs"]), (
            "edited page content was not reflected in search index"
        )
        assert len(updated["docs"]) == len(original["docs"]), (
            "search index lost entries for unchanged pages"
        )


class TestBuildDoneHook:
    """The `on_build_done` hook event fires after ALL build outputs exist."""

    def test_build_done_runs_after_sw_and_manifests(self, tmp_project, monkeypatch):
        import json
        hook = tmp_project / "hook_build_done.py"
        hook.write_text(
            "import json\n"
            "from pathlib import Path\n"
            "def on_build_done(config, **kwargs):\n"
            "    site = Path(config.site_dir)\n"
            "    Path(site / 'build_done_marker.json').write_text(json.dumps({\n"
            "        'sw': (site / 'sw.js').is_file(),\n"
            "        'cache_manifest': (site / 'cache-manifest.json').is_file(),\n"
            "        'pwa_manifest': (site / 'manifest.json').is_file(),\n"
            "        'sitemap': (site / 'sitemap.xml').is_file(),\n"
            "    }))\n"
        )
        cfg_path = tmp_project / "docsforge.yml"
        cfg_path.write_text(cfg_path.read_text() + "\nhooks:\n  - hook_build_done.py\n")

        _build_once(monkeypatch, tmp_project)

        marker = tmp_project / "site" / "build_done_marker.json"
        assert marker.is_file(), "on_build_done hook did not run"
        data = json.loads(marker.read_text())
        assert data["sw"] is True
        assert data["cache_manifest"] is True
        assert data["pwa_manifest"] is True
        assert data["sitemap"] is True

    def test_build_done_skipped_on_strict_abort(self, tmp_project, monkeypatch):
        hook = tmp_project / "hook_build_done.py"
        hook.write_text(
            "def on_build_done(config, **kwargs):\n"
            "    from pathlib import Path\n"
            "    Path(config.site_dir, 'build_done_marker.json').write_text('x')\n"
        )
        cfg_path = tmp_project / "docsforge.yml"
        cfg = cfg_path.read_text()
        cfg_path.write_text(cfg + "\nhooks:\n  - hook_build_done.py\nstrict: true\n")

        # A broken link produces a warning -> strict mode aborts the build.
        (tmp_project / "docs" / "broken.md").write_text("[bad](missing.md)\n")

        from docsforge.build import Abort, build
        from docsforge.config_base import load_config
        monkeypatch.chdir(tmp_project)
        cfg = load_config(config_file=str(tmp_project / "docsforge.yml"))
        with pytest.raises(Abort):
            build(cfg, dirty=True)

        assert not (tmp_project / "site" / "build_done_marker.json").exists()
