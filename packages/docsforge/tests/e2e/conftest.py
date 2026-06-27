"""E2E browser tests (Playwright) — service worker / offline / search.

These run a real Chromium against a built fixture site. They skip
gracefully when Playwright or a browser binary is unavailable, so the
default `pytest` run (and the CI `test` job) is never broken by them.
A dedicated CI `e2e` job installs Chromium and runs `pytest -m e2e`.
"""
from __future__ import annotations

import http.server
import socketserver
import threading
from pathlib import Path
from typing import Iterator

import pytest

pytestmark = pytest.mark.e2e


def _can_launch_browser() -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    try:
        p = sync_playwright().start()
        b = p.chromium.launch()
        b.close()
        p.stop()
        return True
    except Exception:
        return False


_HAS_BROWSER = None


def has_browser() -> bool:
    global _HAS_BROWSER
    if _HAS_BROWSER is None:
        _HAS_BROWSER = _can_launch_browser()
    return _HAS_BROWSER


def _build_fixture(tmp_path: Path) -> Path:
    """Build a small docsforge site and return its site_dir."""
    from docsforge.config_base import load_config
    from docsforge.build import build

    root = tmp_path / "proj"
    docs = root / "docs"
    docs.mkdir(parents=True)
    (docs / "index.md").write_text("# Home\n\nWelcome to the [second](second.md) page.\n")
    (docs / "second.md").write_text("# Second\n\nAnother page.\n")
    (root / "docsforge.yml").write_text(
        "site_name: E2E\n"
        "docs_dir: docs\nsite_dir: site\nprivacy: false\n"
        "theme:\n  name: material\n"
        "  palette:\n    - {scheme: default, primary: teal, accent: teal}\n"
    )
    import os
    cwd = os.getcwd()
    os.chdir(root)
    try:
        cfg = load_config(config_file=str(root / "docsforge.yml"))
        cfg.plugins.on_startup(command="build", dirty=True)
        try:
            build(cfg, dirty=True)
        finally:
            cfg.plugins.on_shutdown()
    finally:
        os.chdir(cwd)
    return root / "site"


class _Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, directory: str = ".", **kw):
        super().__init__(*a, directory=directory, **kw)

    def log_message(self, *a, **kw):  # silence
        pass


@pytest.fixture(scope="module")
def served_site(tmp_path_factory) -> Iterator[tuple[str, Path]]:
    """Build a fixture site and serve it over HTTP for the module."""
    if not has_browser():
        pytest.skip("Playwright/Chromium unavailable — E2E tests skipped")
    site_dir = _build_fixture(tmp_path_factory.mktemp("e2e"))
    port = _free_port()
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", port), lambda *a: _Handler(*a, directory=str(site_dir)))
    httpd.daemon_threads = True
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield (f"http://127.0.0.1:{port}/", site_dir)
    httpd.shutdown()


def _free_port() -> int:
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def context_page(served_site):
    """A fresh Playwright context/page (isolated SW state per test)."""
    from playwright.sync_api import sync_playwright

    base_url, _ = served_site
    p = sync_playwright().start()
    browser = p.chromium.launch()
    context = browser.new_context()
    page = context.new_page()
    try:
        yield base_url, page, context
    finally:
        context.close()
        browser.close()
        p.stop()
