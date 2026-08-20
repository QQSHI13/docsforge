"""Unit tests for the incremental build cache (docsforge/cache.py).

This module is pure logic with no network/theme dependency, so it is the
cheapest to test thoroughly and the most likely to silently regress (it
shipped broken in v11.1.3 and was fixed in v11.1.4).
"""
from __future__ import annotations

import json
from pathlib import Path

from docsforge.cache import (
    CACHE_VERSION,
    BuildPlanner,
    CacheManager,
    DependencyTracker,
    FileHasher,
    _SNIPPET_INCLUDE_RE,
)

import pytest


# ---------------------------------------------------------------------------
# Snippet include regex
# ---------------------------------------------------------------------------


class TestSnippetIncludeRegex:
    def _paths(self, line: str) -> list[str]:
        return _SNIPPET_INCLUDE_RE.findall(line)

    def test_quoted_path(self):
        assert self._paths('--8<-- "hello.py"') == ["hello.py"]

    def test_single_dash_marker(self):
        assert self._paths('-8<-- "snippets/header.md"') == ["snippets/header.md"]

    def test_bare_unquoted_path(self):
        assert self._paths("--8<-- code.py") == ["code.py"]

    def test_indented(self):
        assert self._paths('    --8<-- "a/b.md"') == ["a/b.md"]

    def test_line_range_suffix(self):
        assert self._paths('--8<-- "file.md:5,10"') == ["file.md"]

    def test_anchor_range_suffix(self):
        assert self._paths('--8<-- "file.md#L5"') == ["file.md"]

    @pytest.mark.parametrize(
        "line",
        [
            "plain text --8<-- no",        # not at line start
            "## not an include",           # a heading
            "Use `--8<-- \"x\"` to include",  # inline in backticks
            "",                            # empty
        ],
    )
    def test_non_include_lines_do_not_match(self, line: str):
        assert self._paths(line) == []


# ---------------------------------------------------------------------------
# DependencyTracker.get_file_deps
# ---------------------------------------------------------------------------


class TestGetFileDeps:
    def test_resolves_against_docs_dir(self, tmp_path: Path):
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "includes").mkdir()
        (docs / "includes" / "header.md").write_text("hdr")
        page = docs / "page.md"
        page.write_text('--8<-- "includes/header.md"\n')
        deps = DependencyTracker.get_file_deps(page, page.read_text(), base_paths=[docs])
        assert len(deps) == 1
        assert deps[0].endswith("header.md")

    def test_resolves_against_source_dir(self, tmp_path: Path):
        page = tmp_path / "page.md"
        page.write_text('# P\n\n--8<-- "sibling.md"\n')
        (tmp_path / "sibling.md").write_text("sib")
        deps = DependencyTracker.get_file_deps(page, page.read_text(), base_paths=[tmp_path])
        assert deps and deps[0].endswith("sibling.md")

    def test_resolves_against_cwd_fallback(self, tmp_path: Path, monkeypatch):
        page = tmp_path / "docs" / "page.md"
        page.parent.mkdir(parents=True)
        page.write_text('--8<-- "top.md"\n')
        # top.md lives at cwd (project root), not under docs/
        top = tmp_path / "top.md"
        top.write_text("top")
        monkeypatch.chdir(tmp_path)
        deps = DependencyTracker.get_file_deps(page, page.read_text(), base_paths=[tmp_path / "docs"])
        assert deps and Path(deps[0]).name == "top.md"

    def test_absolute_include_rejected(self, tmp_path: Path):
        """An absolute include (--8<-- "/etc/passwd") must never be tracked,
        even when the target file exists: it escapes the project's include
        roots and would leak arbitrary files into the dependency graph."""
        outside = tmp_path / "outside.md"
        outside.write_text("secret")
        docs = tmp_path / "docs"
        docs.mkdir()
        page = docs / "page.md"
        page.write_text(f'--8<-- "{outside}"\n')
        deps = DependencyTracker.get_file_deps(page, page.read_text(), base_paths=[docs])
        assert deps == []

    def test_include_traversal_escaping_all_bases_rejected(self, tmp_path: Path, monkeypatch):
        """A `../..` include that escapes every candidate base directory must
        be ignored, even when the target file exists."""
        secret = tmp_path / "secret.md"
        secret.write_text("s")
        project = tmp_path / "proj"
        docs = project / "docs"
        docs.mkdir(parents=True)
        page = docs / "page.md"
        page.write_text('--8<-- "../../secret.md"\n')
        monkeypatch.chdir(project)
        deps = DependencyTracker.get_file_deps(page, page.read_text(), base_paths=[docs])
        assert deps == []

    def test_only_existing_files_returned(self, tmp_path: Path):
        # A --8<-- line inside a code fence pointing at a non-existent file
        page = tmp_path / "page.md"
        page.write_text("# Demo\n\n```\n--8<-- \"hello.py\"\n```\n")
        deps = DependencyTracker.get_file_deps(page, page.read_text(), base_paths=[tmp_path])
        assert deps == []

    def test_dedupes_repeated_includes(self, tmp_path: Path):
        inc = tmp_path / "h.md"
        inc.write_text("h")
        page = tmp_path / "p.md"
        page.write_text('--8<-- "h.md"\n\n--8<-- "h.md"\n')
        deps = DependencyTracker.get_file_deps(page, page.read_text(), base_paths=[tmp_path])
        assert len(deps) == 1

    def test_html_input_yields_no_deps(self, tmp_path: Path):
        """Regression guard for the v11.1.3 bug: passing page.content (HTML)."""
        (tmp_path / "h.md").write_text("h")
        html = "<p>--8<-- \"h.md\"</p>\n<h1>rendered</h1>"
        deps = DependencyTracker.get_file_deps(tmp_path / "p.md", html, base_paths=[tmp_path])
        assert deps == []

    def test_reads_source_from_disk_when_content_none(self, tmp_path: Path):
        (tmp_path / "h.md").write_text("h")
        page = tmp_path / "p.md"
        page.write_text('--8<-- "h.md"\n')
        deps = DependencyTracker.get_file_deps(page, content=None, base_paths=[tmp_path])
        assert deps and deps[0].endswith("h.md")

    def test_missing_source_file_returns_empty(self, tmp_path: Path):
        deps = DependencyTracker.get_file_deps(tmp_path / "nope.md", content=None, base_paths=[tmp_path])
        assert deps == []


# ---------------------------------------------------------------------------
# FileHasher / CacheManager
# ---------------------------------------------------------------------------


class TestFileHasher:
    def test_hash_file_is_deterministic(self, tmp_path: Path):
        f = tmp_path / "a.txt"
        f.write_text("hello")
        assert FileHasher.hash_file(f) == FileHasher.hash_file(f)

    def test_hash_file_changes_on_edit(self, tmp_path: Path):
        f = tmp_path / "a.txt"
        f.write_text("v1")
        h1 = FileHasher.hash_file(f)
        f.write_text("v2")
        assert FileHasher.hash_file(f) != h1

    def test_hash_string(self):
        assert FileHasher.hash_string("x") == FileHasher.hash_string("x")
        assert FileHasher.hash_string("x") != FileHasher.hash_string("y")


class TestCacheManager:
    def test_roundtrip_hashes_and_deps(self, tmp_path: Path):
        cm = CacheManager(cache_dir=tmp_path / "c")
        cm.set_hashes({"a": "1"})
        cm.set_deps({"a": ["b"]})
        assert cm.get_hashes() == {"a": "1"}
        assert cm.get_deps() == {"a": ["b"]}

    def test_corrupt_json_recovers_to_empty(self, tmp_path: Path):
        cm = CacheManager(cache_dir=tmp_path / "c")
        # CacheManager.__init__ already created the dir; write garbage into it.
        (tmp_path / "c" / "hashes.json").write_text("{not valid json")
        assert cm.get_hashes() == {}

    def test_config_hash_roundtrip(self, tmp_path: Path):
        cm = CacheManager(cache_dir=tmp_path / "c")
        assert cm.get_config_hash() is None
        cm.set_config_hash("abc")
        assert cm.get_config_hash() == "abc"

    def test_version_roundtrip(self, tmp_path: Path):
        cm = CacheManager(cache_dir=tmp_path / "c")
        assert cm.get_version() == 0
        cm.set_version(CACHE_VERSION)
        assert cm.get_version() == CACHE_VERSION

    def test_tikz_hashes_roundtrip(self, tmp_path: Path):
        cm = CacheManager(cache_dir=tmp_path / "c")
        assert cm.get_tikz_hashes() == {}
        cm.set_tikz_hashes({"diagram.tex": "abc"})
        assert cm.get_tikz_hashes() == {"diagram.tex": "abc"}

    def test_invalidate_clears_all(self, tmp_path: Path):
        cm = CacheManager(cache_dir=tmp_path / "c")
        cm.set_hashes({"a": "1"})
        cm.set_config_hash("x")
        cm.set_tikz_hashes({"d.tex": "h"})
        cm.invalidate()
        assert cm.get_hashes() == {}
        assert cm.get_config_hash() is None
        assert cm.get_tikz_hashes() == {}


# ---------------------------------------------------------------------------
# BuildPlanner
# ---------------------------------------------------------------------------


class TestBuildPlanner:
    def _planner(self, tmp_path: Path) -> BuildPlanner:
        return BuildPlanner(CacheManager(cache_dir=tmp_path / "c"), FileHasher())

    def test_rebuild_when_output_missing(self, tmp_path: Path):
        p = self._planner(tmp_path)
        src = tmp_path / "p.md"
        src.write_text("x")
        # output does not exist
        assert p.should_rebuild(src, tmp_path / "out.html") is True

    def test_rebuild_when_source_hash_changed(self, tmp_path: Path):
        p = self._planner(tmp_path)
        src = tmp_path / "p.md"
        out = tmp_path / "out.html"
        src.write_text("v1")
        out.write_text("built")
        p.update_cache(src, out, deps=[])
        # source unchanged -> no rebuild
        assert p.should_rebuild(src, out) is False
        # source changes -> rebuild
        src.write_text("v2")
        assert p.should_rebuild(src, out) is True

    def test_rebuild_when_dependency_changed(self, tmp_path: Path):
        """The v11.1.4 feature: editing an included file rebuilds the page."""
        p = self._planner(tmp_path)
        src = tmp_path / "p.md"
        inc = tmp_path / "h.md"
        out = tmp_path / "out.html"
        src.write_text('--8<-- "h.md"')
        inc.write_text("v1")
        out.write_text("built")
        deps = [str(inc)]
        p.update_cache(src, out, deps=deps)
        # source untouched, include untouched -> no rebuild
        assert p.should_rebuild(src, out) is False
        # edit the include -> rebuild even though page source is unchanged
        inc.write_text("v2")
        assert p.should_rebuild(src, out) is True

    def test_no_rebuild_when_unchanged(self, tmp_path: Path):
        p = self._planner(tmp_path)
        src = tmp_path / "p.md"
        out = tmp_path / "out.html"
        src.write_text("x")
        out.write_text("built")
        p.update_cache(src, out, deps=[])
        assert p.should_rebuild(src, out) is False

    def test_full_rebuild_on_config_hash_change(self, tmp_path: Path):
        p = self._planner(tmp_path)
        cfg = tmp_path / "docsforge.yml"
        cfg.write_text("site_name: A\n")
        p.save(config_hash=FileHasher().hash_file(cfg))
        assert p.should_full_rebuild(cfg) is False
        cfg.write_text("site_name: B\n")
        assert p.should_full_rebuild(cfg) is True

    def test_full_rebuild_when_no_cached_config_hash(self, tmp_path: Path):
        p = self._planner(tmp_path)
        cfg = tmp_path / "docsforge.yml"
        cfg.write_text("site_name: A\n")
        assert p.should_full_rebuild(cfg) is True

    def test_full_rebuild_on_pkg_version_change(self, tmp_path: Path):
        """A docsforge upgrade (version change) must trigger a full rebuild so
        theme/template/SW updates propagate to the built site."""
        p = self._planner(tmp_path)
        cfg = tmp_path / "docsforge.yml"
        cfg.write_text("site_name: A\n")
        p.save(config_hash=FileHasher().hash_file(cfg), pkg_version="11.2.0")
        # Same version -> no full rebuild.
        assert p.should_full_rebuild(cfg, pkg_version="11.2.0") is False
        # New version -> full rebuild.
        assert p.should_full_rebuild(cfg, pkg_version="11.3.6") is True

    def test_full_rebuild_on_theme_template_change(self, tmp_path: Path):
        """Editing base.html / a partial / a custom_dir template must trigger a
        full rebuild so every page re-renders."""
        from docsforge.cache import BuildPlanner, CacheManager, FileHasher
        p = self._planner(tmp_path)
        cfg = tmp_path / "docsforge.yml"
        cfg.write_text("site_name: A\n")
        tdir = tmp_path / "tpl"
        tdir.mkdir()
        (tdir / "base.html").write_text("v1")
        sig1 = p.theme_signature([str(tdir)])
        p.save(config_hash=FileHasher().hash_file(cfg), pkg_version="x", theme_sig=sig1)
        assert p.should_full_rebuild(cfg, pkg_version="x", theme_sig=sig1) is False
        # Edit a template -> signature changes -> stored sig mismatches -> rebuild.
        (tdir / "base.html").write_text("v2")
        sig2 = p.theme_signature([str(tdir)])
        assert sig2 != sig1
        p2 = BuildPlanner(CacheManager(cache_dir=tmp_path / "c"), FileHasher())
        assert p2.should_full_rebuild(cfg, pkg_version="x", theme_sig=sig2) is True

    def test_invalidate_clears_in_memory_hashes(self, tmp_path: Path):
        """planner.invalidate() must clear in-memory hashes, not just disk files
        — otherwise unchanged pages would skip rebuild after a config/version change."""
        p = self._planner(tmp_path)
        src = tmp_path / "p.md"
        out = tmp_path / "out.html"
        src.write_text("x"); out.write_text("built")
        p.update_cache(src, out, deps=[])
        assert p.hashes, "hashes populated"
        p.invalidate()
        assert p.hashes == {}, "in-memory hashes cleared"
        assert p.config_hash is None
        # meta is retained (source contents unchanged across a version bump)
        assert isinstance(p.meta, dict)

    def test_update_cache_stores_dep_hashes(self, tmp_path: Path):
        """Regression for the latent bug: dep hashes were never stored, making
        the dep check a no-op (cached hash always missing -> always rebuild)."""
        p = self._planner(tmp_path)
        src = tmp_path / "p.md"
        inc = tmp_path / "h.md"
        out = tmp_path / "out.html"
        src.write_text("x")
        inc.write_text("h")
        out.write_text("built")
        p.update_cache(src, out, deps=[str(inc)])
        # The dep's hash must be present so a later unchanged build can return
        # False instead of rebuilding every time.
        assert str(inc) in p.hashes

    def test_find_orphaned_outputs(self, tmp_path: Path):
        docs = tmp_path / "docs"
        site = tmp_path / "site"
        docs.mkdir()
        site.mkdir()
        (docs / "kept.md").write_text("k")
        (site / "kept").mkdir()
        (site / "kept" / "index.html").write_text("k")  # has .md source
        (site / "gone").mkdir()
        (site / "gone" / "index.html").write_text("g")  # no source
        p = self._planner(tmp_path)
        orphaned = p.find_orphaned_outputs(docs, site)
        names = {o.name for o in orphaned}
        assert "index.html" in names
        assert {o.parent.name for o in orphaned} == {"gone"}

    def test_save_persists_version(self, tmp_path: Path):
        cm = CacheManager(cache_dir=tmp_path / "c")
        p = BuildPlanner(cm, FileHasher())
        p.save(config_hash="x")
        assert cm.get_version() == CACHE_VERSION

    def test_should_scan_orphans_skips_when_no_removals(self, tmp_path: Path):
        p = self._planner(tmp_path)
        # First build (no cached set) -> scan.
        assert p.should_scan_orphans({"a.md", "b.md"}) is True
        p.update_sources({"a.md", "b.md"})
        # Same set -> skip.
        assert p.should_scan_orphans({"a.md", "b.md"}) is False
        # Added a file (set grew) -> skip.
        assert p.should_scan_orphans({"a.md", "b.md", "c.md"}) is False
        # Removed a file -> scan.
        assert p.should_scan_orphans({"a.md"}) is True

    def test_current_hash_uses_mtime_size_cache(self, tmp_path: Path):
        """_current_hash must not re-read a file whose mtime+size are unchanged."""
        p = self._planner(tmp_path)
        f = tmp_path / "p.md"
        f.write_text("hello")
        calls = {"n": 0}
        real_hash = p.hasher.hash_file
        def counting(path):
            calls["n"] += 1
            return real_hash(path)
        p.hasher.hash_file = counting  # type: ignore
        h1 = p._current_hash(f)
        h2 = p._current_hash(f)        # second call: mtime+size unchanged -> cache hit, no re-read
        assert h1 == h2
        assert calls["n"] == 1, f"expected 1 read, got {calls['n']}"
        # Edit the file (size changes) -> re-read.
        f.write_text("hello world")
        h3 = p._current_hash(f)
        assert calls["n"] == 2
        assert h3 != h1

    def test_failed_build_not_cached(self, tmp_path: Path, monkeypatch):
        """Regression for v11.1.4 bug 3: build.py must skip update_cache when a
        page build raises. Here we assert the helper contract the build loop
        relies on: update_cache is only meaningful after a successful build,
        and calling it on failure would mark a broken page as up-to-date."""
        p = self._planner(tmp_path)
        src = tmp_path / "p.md"
        out = tmp_path / "out.html"
        src.write_text("x")
        out.write_text("built")
        # Simulate: build failed -> caller must NOT call update_cache.
        # If the caller honors that, the page stays "needs rebuild" next time.
        assert p.should_rebuild(src, out) is True
        # (contract documented; the actual build.py loop is covered by E2E)
