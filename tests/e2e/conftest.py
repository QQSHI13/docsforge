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
    p = None
    b = None
    try:
        p = sync_playwright().start()
        b = p.chromium.launch()
        return True
    except Exception:
        return False
    finally:
        try:
            if b:
                b.close()
        except Exception:
            pass
        try:
            if p:
                p.stop()
        except Exception:
            pass


_HAS_BROWSER = None


def has_browser() -> bool:
    global _HAS_BROWSER
    if _HAS_BROWSER is None:
        _HAS_BROWSER = _can_launch_browser()
    return _HAS_BROWSER


def _build_fixture(tmp_path: Path, site_name: str = "E2E", with_nav: bool = True, language: str | None = None) -> tuple[Path, Path]:
    """Build a small docsforge site and return (root, site_dir)."""
    from docsforge.config_base import load_config
    from docsforge.build import build

    root = tmp_path / "proj"
    docs = root / "docs"
    docs.mkdir(parents=True)
    (docs / "index.md").write_text("# Home\n\nWelcome to the [second](second.md) page.\n\nUniqueTokenHome\n")
    (docs / "second.md").write_text("# Second\n\nAnother page with searchable content.\n\nUniqueTokenSecond\n")
    (docs / "guide").mkdir()
    (docs / "guide" / "intro.md").write_text("# Introduction\n\nIntro material.\n")
    nav_block = (
        "nav:\n  - Home: index.md\n  - Second: second.md\n  - Guide:\n      - guide/intro.md\n"
        if with_nav else ""
    )
    (root / "docsforge.yml").write_text(
        "site_name: " + site_name + "\n"
        "docs_dir: docs\nsite_dir: site\nprivacy: false\n"
        + nav_block +
        "theme:\n  name: material\n"
        + (f"  language: {language}\n" if language else "") +
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
    return root, root / "site"


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
    _, site_dir = _build_fixture(tmp_path_factory.mktemp("e2e"))
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), lambda *a: _Handler(*a, directory=str(site_dir)))
    httpd.daemon_threads = True
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield (f"http://127.0.0.1:{port}/", site_dir)
    httpd.shutdown()


@pytest.fixture(scope="module")
def served_site_i18n(tmp_path_factory):
    """A fixture site built with theme.language='fr' for i18n checks."""
    if not has_browser():
        pytest.skip("Playwright/Chromium unavailable — E2E tests skipped")
    _, site_dir = _build_fixture(tmp_path_factory.mktemp("e2e-i18n"), language="fr")
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), lambda *a: _Handler(*a, directory=str(site_dir)))
    httpd.daemon_threads = True
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{port}/"
    httpd.shutdown()


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


@pytest.fixture
def served_dev(tmp_path_factory):
    """Run `docsforge serve` in a fixture project and yield its URL.

    Tests the dev-server path (the one with the most historical bugs) and
    verifies it behaves like a deployed site (SW installs, offline works).
    """
    import os
    import re
    import subprocess
    import sys
    import time

    if not has_browser():
        pytest.skip("Playwright/Chromium unavailable — E2E tests skipped")
    root, _ = _build_fixture(tmp_path_factory.mktemp("e2e-serve"))
    proc = subprocess.Popen(
        [sys.executable, "-m", "docsforge", "serve", "--no-open"],
        cwd=str(root),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )
    url = None
    deadline = time.time() + 40
    try:
        while time.time() < deadline:
            import select
            readable, _, _ = select.select([proc.stdout], [], [], max(0, deadline - time.time()))
            if not readable:
                if proc.poll() is not None:
                    break
                continue
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    break
                continue
            m = re.search(r"Serving on\s+(https?://\S+)", line)
            if m:
                url = m.group(1)
                break
        if not url:
            out = "".join(proc.stdout.readlines() or [])
            pytest.fail(f"docsforge serve did not start: {out[:500]}")
        yield url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
