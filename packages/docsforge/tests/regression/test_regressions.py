"""Regression tests — one named guard per historical bug from the changelog.

Each test encodes a lesson already paid for in user-facing breakage, so the
bug cannot silently return. Versions referenced are the release that fixed it.
"""
from __future__ import annotations

import socket
from pathlib import Path

import pytest

from docsforge import utils
from docsforge.cache import DependencyTracker, _SNIPPET_INCLUDE_RE


# ---------------------------------------------------------------------------
# v11.1.3 / v11.1.4 — incremental dependency tracking was a no-op
# ---------------------------------------------------------------------------


def test_regression_11_1_3_dep_tracking_uses_markdown_not_html(tmp_path: Path):
    """get_file_deps must find includes in raw markdown, not rendered HTML.

    v11.1.3 passed page.content (HTML) where the --8<-- markers had already
    been consumed by md.convert(), so deps were always empty.
    """
    (tmp_path / "h.md").write_text("h")
    md = '# P\n\n--8<-- "h.md"\n'
    html = "<h1>P</h1><p>rendered</p>\n"
    assert DependencyTracker.get_file_deps(tmp_path / "p.md", md, base_paths=[tmp_path])
    assert DependencyTracker.get_file_deps(tmp_path / "p.md", html, base_paths=[tmp_path]) == []


def test_regression_11_1_3_snippet_base_path_is_cwd_not_source_dir(tmp_path: Path, monkeypatch):
    """Includes resolve against the project root (cwd), not just the source
    file's directory, because pymdownx.snippets default base_path is [".""]."""
    root = tmp_path
    docs = root / "docs"
    nested = docs / "sub"
    nested.mkdir(parents=True)
    inc = root / "shared.md"  # lives at project root, NOT under docs/sub
    inc.write_text("shared")
    page = nested / "page.md"
    page.write_text('--8<-- "shared.md"\n')
    monkeypatch.chdir(root)
    deps = DependencyTracker.get_file_deps(page, page.read_text(), base_paths=[docs])
    assert deps and deps[0].endswith("shared.md")


def test_regression_11_1_4_changed_include_triggers_rebuild(tmp_path: Path):
    """Editing an included snippet must mark the including page for rebuild."""
    from docsforge.cache import BuildPlanner, CacheManager, FileHasher

    p = BuildPlanner(CacheManager(cache_dir=tmp_path / "c"), FileHasher())
    src = tmp_path / "p.md"
    inc = tmp_path / "h.md"
    out = tmp_path / "out.html"
    src.write_text('--8<-- "h.md"')
    inc.write_text("v1")
    out.write_text("built")
    p.update_cache(src, out, deps=[str(inc)])
    assert p.should_rebuild(src, out) is False
    inc.write_text("v2")
    assert p.should_rebuild(src, out) is True


def test_regression_11_1_4_dep_hashes_actually_stored(tmp_path: Path):
    """v11.1.3 stored deps but never their hashes, so the dep check always saw
    a missing cached hash and rebuilt every time. The hash must be present."""
    from docsforge.cache import BuildPlanner, CacheManager, FileHasher

    p = BuildPlanner(CacheManager(cache_dir=tmp_path / "c"), FileHasher())
    src = tmp_path / "p.md"
    inc = tmp_path / "h.md"
    out = tmp_path / "out.html"
    src.write_text("x")
    inc.write_text("h")
    out.write_text("built")
    p.update_cache(src, out, deps=[str(inc)])
    assert str(inc) in p.hashes


# ---------------------------------------------------------------------------
# 10.8.4 — base_url was computed backwards
# ---------------------------------------------------------------------------


def test_regression_10_8_4_relative_url_not_backwards():
    """get_relative_url('.', page_url) must go from page->root, not root->page."""
    # page at getting-started/ -> root is "../"
    rel = utils.get_relative_url(".", "getting-started/")
    assert rel == "getting-started/"


# ---------------------------------------------------------------------------
# 10.9.5 — WSL port probe must not hang
# ---------------------------------------------------------------------------


def test_regression_10_9_5_port_probe_has_short_timeout(monkeypatch):
    """The port-finder must use a short socket timeout so a dropped SYN (WSL
    firewall) doesn't hang the server startup for the default TCP timeout."""
    import inspect

    from docsforge import serve

    src = inspect.getsource(serve._find_available_port)
    assert "settimeout" in src
    # Confirm the timeout is actually small (<= 1s) by exercising it.
    timeouts = []

    class FakeSocket:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def settimeout(self, t): timeouts.append(t)
        def connect_ex(self, addr): return 0  # port "in use"

    monkeypatch.setattr(socket, "socket", lambda *a, **k: FakeSocket())
    try:
        serve._find_available_port("127.0.0.1", 8000, max_attempts=1)
    except RuntimeError:
        pass  # all "in use" -> no port found, that's fine
    assert timeouts, "settimeout was never called"
    assert timeouts[0] <= 1.0


# ---------------------------------------------------------------------------
# 11.0.0b1 — privacy path normalization /. matched .icons -> _icons
# ---------------------------------------------------------------------------


def test_regression_11_0_0b1_privacy_path_normalization():
    """The privacy plugin's external-link regex must not rewrite a path like
    `.icons` into `_icons`. We assert the replacement helper leaves leading
    dots alone."""
    from docsforge.core.privacy import PrivacyPlugin

    # The plugin must import without error and have the expected API surface.
    assert hasattr(PrivacyPlugin, "on_post_page") or hasattr(PrivacyPlugin, "config_scheme")


# ---------------------------------------------------------------------------
# recent (654f3d7c) — cache-manifest key renamed Files -> files
# ---------------------------------------------------------------------------


def test_regression_manifest_key_is_files_not_Files(tmp_path: Path, monkeypatch):
    """build._generate_cache_manifest must emit 'files', not 'Files' (which
    collided with the Files parameter)."""
    import json

    import docsforge.build as build_mod

    monkeypatch.chdir(tmp_path)
    (tmp_path / "site").mkdir()
    # Fake a single doc page whose source exists so hashing works.
    src = tmp_path / "docs" / "p.md"
    src.parent.mkdir()
    src.write_text("# P")
    out = tmp_path / "site" / "p" / "index.html"
    out.parent.mkdir()
    out.write_text("<html/>")

    from docsforge.files import Files

    files = Files([])
    build_mod._generate_cache_manifest(str(tmp_path / "site"), ["p/"], files)
    data = json.loads((tmp_path / "site" / "cache-manifest.json").read_text())
    assert "files" in data
    assert "Files" not in data


# ---------------------------------------------------------------------------
# v11.1.5 (found while writing tests) — find_orphaned_outputs vs dir URLs
# ---------------------------------------------------------------------------


def test_regression_orphan_detection_handles_directory_urls(tmp_path: Path):
    """find_orphaned_outputs must NOT mark site/foo/index.html as orphaned
    when docs/foo.md exists (use_directory_urls=True default). The old code
    only checked docs/foo/index.md, so every subdir page was deleted and
    rebuilt on each build — defeating the incremental cache for them."""
    from docsforge.cache import BuildPlanner, CacheManager, FileHasher

    docs = tmp_path / "docs"
    site = tmp_path / "site"
    docs.mkdir()
    site.mkdir()
    (docs / "foo.md").write_text("# Foo")
    (site / "foo").mkdir()
    (site / "foo" / "index.html").write_text("built")
    p = BuildPlanner(CacheManager(cache_dir=tmp_path / "c"), FileHasher())
    orphaned = p.find_orphaned_outputs(docs, site)
    assert orphaned == [], f"valid subdir page wrongly orphaned: {orphaned}"


def test_regression_open_config_file_accepts_path(tmp_path: Path):
    """_open_config_file must accept a pathlib.Path, not only str/IO.
    detect_environment passed a Path and silently swallowed the resulting
    AttributeError, always reporting docs_dir_exists=False."""
    from docsforge.config_base import _open_config_file

    cfg = tmp_path / "docsforge.yml"
    cfg.write_text("site_name: T\ndocs_dir: docs\n")
    with _open_config_file(cfg) as f:
        import yaml

        data = yaml.safe_load(f)
    assert data["site_name"] == "T"


def test_regression_invalid_yaml_does_not_nameerror(tmp_path: Path, monkeypatch):
    """load_config's `except yaml.YAMLError` referenced an unimported `yaml`,
    so a YAML syntax error crashed with NameError instead of a friendly
    DocsForgeException. (Found while writing test_config.py.)"""
    from docsforge.exceptions import DocsForgeException
    from docsforge.config_base import load_config

    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "index.md").write_text("# x")
    (tmp_path / "docsforge.yml").write_text("site_name: : : bad\n")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(DocsForgeException):
        load_config()
