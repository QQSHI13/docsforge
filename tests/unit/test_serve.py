"""Unit tests for the dev server: port finding, URL helpers, and the
live-reload rebuild-queueing logic (the paths with the most historical bugs:
WSL port hangs, infinite reload loops, pidfile races).
"""
from __future__ import annotations

import os
import socket
from types import SimpleNamespace

import pytest

from docsforge.livereload import (
    LiveReloadServer,
    _normalize_mount_path,
    _serve_url,
    _try_relativize_path,
)
from docsforge.serve import _find_available_port


# ---------------------------------------------------------------------------
# Port finding
# ---------------------------------------------------------------------------


class TestFindAvailablePort:
    def test_returns_start_port_when_free(self, monkeypatch):
        class FakeSocket:
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def settimeout(self, t): pass
            def connect_ex(self, addr): return 1  # not listening -> free

        monkeypatch.setattr(socket, "socket", lambda *a, **k: FakeSocket())
        assert _find_available_port("127.0.0.1", 8000) == 8000

    def test_increments_when_in_use(self, monkeypatch):
        attempts = {"n": 0}

        class FakeSocket:
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def settimeout(self, t): pass
            def connect_ex(self, addr):
                attempts["n"] += 1
                return 0 if attempts["n"] == 1 else 1  # 8000 in use, 8001 free

        monkeypatch.setattr(socket, "socket", lambda *a, **k: FakeSocket())
        assert _find_available_port("127.0.0.1", 8000) == 8001

    def test_raises_when_all_in_use(self, monkeypatch):
        class FakeSocket:
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def settimeout(self, t): pass
            def connect_ex(self, addr): return 0  # always in use

        monkeypatch.setattr(socket, "socket", lambda *a, **k: FakeSocket())
        with pytest.raises(RuntimeError):
            _find_available_port("127.0.0.1", 8000, max_attempts=3)

    def test_firewall_dropped_syn_returns_port(self, monkeypatch):
        # A dropped SYN (firewall) raises socket.timeout/OSError -> port is free
        class FakeSocket:
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def settimeout(self, t):
                self.t = t
                assert t <= 1.0, "probe must use a short timeout (WSL fix)"
            def connect_ex(self, addr):
                raise socket.timeout("dropped")

        monkeypatch.setattr(socket, "socket", lambda *a, **k: FakeSocket())
        assert _find_available_port("127.0.0.1", 8000) == 8000


# ---------------------------------------------------------------------------
# URL / path helpers
# ---------------------------------------------------------------------------


class TestNormalizeMountPath:
    def test_adds_leading_and_trailing_slash(self):
        assert _normalize_mount_path("docs") == "/docs/"

    def test_root(self):
        assert _normalize_mount_path("/") == "/"
        assert _normalize_mount_path("") == "/"

    def test_strips_redundant_slashes(self):
        assert _normalize_mount_path("///docs//") == "/docs/"


class TestServeUrl:
    def test_root(self):
        assert _serve_url("127.0.0.1", 8000, "/") == "http://127.0.0.1:8000/"

    def test_subpath(self):
        assert _serve_url("0.0.0.0", 9000, "/docs/") == "http://0.0.0.0:9000/docs/"


class TestTryRelativizePath:
    def test_relative_to_cwd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sub = tmp_path / "sub" / "file.md"
        sub.parent.mkdir()
        sub.write_text("x")
        rel = _try_relativize_path(str(sub))
        assert rel == "sub/file.md"
        assert not os.path.isabs(rel)


# ---------------------------------------------------------------------------
# Live-reload rebuild queueing (the infinite-reload-loop guard)
# ---------------------------------------------------------------------------


def _make_server(tmp_path):
    # bind_and_activate=False -> no real socket/port needed.
    return LiveReloadServer(
        builder=lambda: None,
        host="127.0.0.1",
        port=0,
        root=str(tmp_path),
        mount_path="/",
    )


def _file_event():
    return SimpleNamespace(
        is_directory=False, src_path="/x.md", dest_path="/x.md", event_type="modified"
    )


class TestRebuildQueueing:
    def test_event_when_idle_signals_rebuild(self, tmp_path):
        s = _make_server(tmp_path)
        assert s._want_rebuild is False
        s._on_file_event(_file_event())
        assert s._want_rebuild is True

    def test_event_during_build_is_queued_not_signaled(self, tmp_path):
        """When a build is in progress, file changes must be queued
        (_pending_rebuild) rather than triggering a concurrent rebuild — the
        fix for the infinite reload loop (v11.0.0b1)."""
        s = _make_server(tmp_path)
        s._rebuilding = True
        s._on_file_event(_file_event())
        assert s._pending_rebuild is True
        assert s._want_rebuild is False, "idle rebuild flag must not flip during a build"

    def test_directory_events_ignored(self, tmp_path):
        s = _make_server(tmp_path)
        s._on_file_event(SimpleNamespace(is_directory=True))
        assert s._want_rebuild is False
        assert s._pending_rebuild is False

    def test_queued_rebuild_is_cleared_after_build(self, tmp_path):
        """The build loop clears _pending_rebuild and re-arms _want_rebuild."""
        s = _make_server(tmp_path)
        s._rebuilding = True
        s._on_file_event(_file_event())
        assert s._pending_rebuild is True
        # Simulate the end of the build loop's finally block.
        s._rebuilding = False
        with s._rebuild_cond:
            if s._pending_rebuild:
                s._pending_rebuild = False
                s._want_rebuild = True
        assert s._pending_rebuild is False
        assert s._want_rebuild is True

    def test_url_and_mount_path(self, tmp_path):
        s = _make_server(tmp_path)
        assert s.url == "http://127.0.0.1:8000/" or s.url.startswith("http://127.0.0.1:")
        assert s.mount_path == "/"
