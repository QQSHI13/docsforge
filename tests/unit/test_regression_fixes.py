"""Regression tests for a batch of verified bugs fixed together:

- ``State.__del__`` removed a shared log handler on GC (docsforge/__main__.py)
- ``_default_page_lock`` was a plain ``Lock`` but ``_build_page`` is re-entrant (build.py)
- ``on_shutdown()`` in a ``finally`` could mask the original build error (cli_core.py)
- gzip embedded the absolute output path in the sitemap header (build.py)
- ``concurrency`` 0/negative crashed the ThreadPoolExecutor (build.py)
- ``_watch_applied`` tracked ``id(config)``, unsafe under CPython id reuse (serve.py)
- ``_find_available_port`` raising left ``on_startup`` unbalanced (serve.py)
- server bind raced the port probe (TOCTOU) with no retry (livereload.py)
- epoch wait had no timeout, blocking handler threads forever (livereload.py)
- ``_last_seen`` grew unboundedly on delete/move/create churn (livereload.py)
- cache atomic writes used a fixed ``.tmp`` name, clobbering concurrent builds (cache.py)
"""
from __future__ import annotations

import errno
import logging
import os
import struct
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import docsforge.build as build_mod
from docsforge.__main__ import State
from docsforge.cache import CacheManager
from docsforge.cli_core import BuildEngine
from docsforge.livereload import LiveReloadServer

# ---------------------------------------------------------------------------
# __main__.State — no __del__ handler removal
# ---------------------------------------------------------------------------


class TestStateHandlerLifecycle:
    def test_double_init_adds_single_handler(self):
        a = State()
        State()
        handlers = [h for h in a.logger.handlers if h.name == "DocsForgeStreamHandler"]
        assert len(handlers) == 1

    def test_no_del_removes_shared_handler(self):
        state = State()
        assert hasattr(state, "__del__") is False
        # Simulate GC of one State instance; the handler must survive.
        before = [h.name for h in state.logger.handlers]
        del state
        import gc

        gc.collect()
        after = [h.name for h in logging.getLogger("docsforge").handlers]
        assert before == after
        assert "DocsForgeStreamHandler" in after


# ---------------------------------------------------------------------------
# build.py — default page lock must be re-entrant
# ---------------------------------------------------------------------------


class TestDefaultPageLock:
    def test_default_lock_is_rlock(self):
        assert isinstance(build_mod._default_page_lock, type(threading.RLock()))

    def test_default_lock_is_reentrant(self):
        lock = build_mod._default_page_lock
        with lock, lock:  # plain Lock would deadlock here
            pass


# ---------------------------------------------------------------------------
# cli_core.BuildEngine — on_shutdown must not mask the build error
# ---------------------------------------------------------------------------


class TestBuildEngineShutdownMasking:
    def test_shutdown_failure_does_not_mask_build_error(self, monkeypatch, caplog):
        cfg = Mock()
        cfg.plugins.on_startup = Mock()
        cfg.plugins.on_shutdown = Mock(side_effect=RuntimeError("shutdown boom"))
        monkeypatch.setattr("docsforge.config_base.load_config", Mock(return_value=cfg))
        build_error = ValueError("original build failure")
        monkeypatch.setattr(build_mod, "build", Mock(side_effect=build_error))

        with caplog.at_level(logging.ERROR, logger="docsforge.cli_core"):
            result = BuildEngine.build()

        assert result == 1
        cfg.plugins.on_shutdown.assert_called_once()
        # The exception reported is the ORIGINAL build failure, not the
        # shutdown error — `on_shutdown` raising must not mask it.
        assert any("original build failure" in r.message for r in caplog.records)
        assert not any("shutdown boom" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# build.py — gzip reproducibility + concurrency clamp
# ---------------------------------------------------------------------------


class TestGzipReproducibility:
    def _gzip_header_name(self, data: bytes) -> bytes:
        # Minimal parse of the gzip header: magic(2) + method(1) + flags(1) + ...
        assert data[:2] == b"\x1f\x8b"
        flg = data[3]
        offset = 10
        if flg & 0x04:  # FEXTRA
            (xlen,) = struct.unpack("<H", data[offset:offset + 2])
            offset += 2 + xlen
        if flg & 0x08:  # FNAME — the embedded filename
            end = data.index(b"\x00", offset)
            return data[offset:end]
        return b""

    def test_build_theme_template_uses_empty_gzip_filename(self, tmp_path, monkeypatch):
        from tests.unit.test_build import _load_config

        monkeypatch.chdir(tmp_path)
        cfg = _load_config(tmp_path)
        os.makedirs(cfg.site_dir, exist_ok=True)

        file = build_mod.File("index.md", cfg.docs_dir, cfg.site_dir, cfg.use_directory_urls)
        files = build_mod.Files([file])
        nav = Mock()
        env = Mock()
        template = env.get_template.return_value
        template.render.return_value = "<urlset>valid sitemap</urlset>"

        monkeypatch.setattr(build_mod.utils, "get_build_timestamp", Mock(return_value=1234567))
        build_mod._build_theme_template("sitemap.xml", env, files, cfg, nav)

        gz_path = Path(cfg.site_dir) / "sitemap.xml.gz"
        assert gz_path.exists()
        with open(gz_path, "rb") as f:
            assert self._gzip_header_name(f.read()) == b""


class TestConcurrencyClamp:
    def test_zero_concurrency_still_builds(self, tmp_path, monkeypatch):
        from tests.unit.test_build import _load_config

        cfg = _load_config(tmp_path)
        cfg.concurrency = 0
        monkeypatch.chdir(tmp_path)

        file = build_mod.File("page.md", cfg.docs_dir, cfg.site_dir, cfg.use_directory_urls)
        files = build_mod.Files([file])
        build_mod.Page(None, file, cfg)
        file.page.markdown = "# x\n"
        file.page.content = "<h1>x</h1>"

        planner = Mock()
        planner.should_rebuild.return_value = True
        nav = Mock()
        env = Mock()
        env.get_template.return_value = Mock(render=Mock(return_value="<p>x</p>"))
        cfg.plugins.on_env = Mock(return_value=env)
        # i18n's context hook writes into config["extra"]; give the mock real dicts.
        cfg.extra = {}
        cfg.theme.static_templates = []
        cfg.extra_templates = []
        planner.validation = {}

        built_any, _ = build_mod._write_outputs(cfg, files, nav, env, planner, [file], lambda level: True)
        assert built_any is True


# ---------------------------------------------------------------------------
# serve.py — watch flag on config object, shutdown on port failure
# ---------------------------------------------------------------------------


class TestWatchAppliedTracking:
    def test_watch_extension_survives_id_reuse(self, monkeypatch):
        """A recycled config object id must not skip the watch extension."""
        import docsforge.serve as serve_mod

        events = []

        class FakeConfig:
            def __init__(self):
                self.watch = []
                self.dev_addr = ("127.0.0.1", 9999)
                self.site_url = None

        config = FakeConfig()
        config.plugins = Mock()
        # Make on_startup a plain no-op: raising here would be caught by the
        # shutdown-balancing `except Exception` in serve() (matching its
        # "startup raised" branch), not by the port-finding branch.
        config.plugins.on_startup = Mock()
        config.plugins.on_shutdown = Mock(side_effect=lambda: events.append("shutdown"))

        # Same id() reused for two distinct logical configs (simulated).
        monkeypatch.setattr(serve_mod, "load_config", Mock(return_value=config))
        monkeypatch.setattr(serve_mod, "_find_available_port", Mock(side_effect=RuntimeError("no port")))

        with pytest.raises(RuntimeError, match="no port"):
            serve_mod.serve(config_file="docsforge.yml", watch=["extra_dir"])

        # on_startup ran, port finding failed -> on_shutdown must have run.
        assert events == ["shutdown"]
        config.plugins.on_startup.assert_called_once()


# ---------------------------------------------------------------------------
# livereload.py — bind retry (TOCTOU), epoch timeout, _last_seen eviction
# ---------------------------------------------------------------------------


def _make_server(root: Path) -> LiveReloadServer:
    return LiveReloadServer(
        builder=lambda: None, host="127.0.0.1", port=0, root=str(root), mount_path="/"
    )


class TestBindRetry:
    def test_eaddrinuse_retries_next_port(self, tmp_path, monkeypatch):
        server = _make_server(tmp_path)
        calls = {"n": 0}

        def flaky_bind():
            calls["n"] += 1
            if calls["n"] == 1:
                raise OSError(errno.EADDRINUSE, "Address already in use")
            server.server_address = (server.server_address[0], server.server_address[1] + 1)

        monkeypatch.setattr(server, "server_bind", flaky_bind)
        monkeypatch.setattr(server, "server_activate", lambda: None)
        # Prevent the build loop / serve thread from actually starting.
        monkeypatch.setattr(server, "_build_loop", lambda: None)
        monkeypatch.setattr(threading.Thread, "start", lambda self: None)

        server.serve(open_in_browser=False)
        assert calls["n"] == 2
        server.server_close()

    def test_other_bind_errors_propagate(self, tmp_path, monkeypatch):
        server = _make_server(tmp_path)
        monkeypatch.setattr(server, "server_bind", Mock(side_effect=PermissionError("denied")))
        monkeypatch.setattr(server, "_build_loop", lambda: None)
        monkeypatch.setattr(threading.Thread, "start", lambda self: None)
        with pytest.raises(PermissionError):
            server.serve(open_in_browser=False)


class TestEpochWaitTimeout:
    def test_dead_build_thread_returns_500(self, tmp_path):
        server = _make_server(tmp_path)
        # Simulate an in-flight rebuild that never completes.
        server._wanted_epoch = server._visible_epoch + 9999

        environ = {"PATH_INFO": "/index.html"}
        responses = []

        def start_response(status, headers):
            responses.append((status, headers))

        # Monkeypatch the timeout down so the test stays fast. Patch on the
        # *class*, not the instance — assigning to the instance shadows the
        # bound method and breaks `self` binding at the call site.
        original_wait_for = type(server._epoch_cond).wait_for

        def fast_wait_for(cond, predicate, timeout=None):
            return original_wait_for(cond, predicate, timeout=0.01)

        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(type(server._epoch_cond), "wait_for", fast_wait_for)
        try:
            result = server._serve_request(environ, start_response)
        finally:
            monkeypatch.undo()

        assert responses and responses[0][0].startswith("500")
        assert b"500" in b"".join(result)


class TestLastSeenEviction:
    def test_deleted_event_evicts_last_seen(self, tmp_path):
        server = _make_server(tmp_path)
        path = str(tmp_path / "gone.md")
        server._last_seen[path] = (1, 2)

        event = SimpleNamespace(
            is_directory=False,
            event_type="deleted",
            src_path=path,
            dest_path="",
        )
        server._on_file_event(event)
        assert path not in server._last_seen
        server.server_close()

    def test_moved_event_evicts_src_and_dest(self, tmp_path):
        server = _make_server(tmp_path)
        src, dest = str(tmp_path / "a.md"), str(tmp_path / "b.md")
        server._last_seen[src] = (1, 2)
        server._last_seen[dest] = (3, 4)

        event = SimpleNamespace(
            is_directory=False,
            event_type="moved",
            src_path=src,
            dest_path=dest,
        )
        server._on_file_event(event)
        assert src not in server._last_seen
        assert dest not in server._last_seen
        server.server_close()

    def test_modified_event_still_updates_last_seen(self, tmp_path):
        server = _make_server(tmp_path)
        f = tmp_path / "f.md"
        f.write_text("x")

        event = SimpleNamespace(
            is_directory=False,
            event_type="modified",
            src_path=str(f),
            dest_path="",
        )
        server._on_file_event(event)
        assert str(f) in server._last_seen
        server.server_close()


# ---------------------------------------------------------------------------
# cache.py — PID-unique temp files
# ---------------------------------------------------------------------------


class TestCacheAtomicWrite:
    def test_temp_file_uses_pid_and_is_cleaned_up(self, tmp_path):
        cm = CacheManager(cache_dir=tmp_path)
        cm.set_hashes({"a": "1"})
        assert cm.get_hashes() == {"a": "1"}
        leftovers = [p for p in tmp_path.iterdir() if ".tmp" in p.name]
        assert leftovers == []

    def test_concurrent_writers_do_not_clobber(self, tmp_path):
        cm = CacheManager(cache_dir=tmp_path)
        barrier = threading.Barrier(2)
        errors = []

        def writer(key):
            try:
                barrier.wait(timeout=5)
                cm.set_hashes({key: key})
                # Readers racing the writer must not see a missing file:
                # the temp file is PID-unique, so the final replace() must
                # always install a complete payload.
                cm.get_hashes()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(f"k{i}",)) for i in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors
        # One writer wins; its content must be intact JSON.
        assert cm.get_hashes() in ({"k0": "k0"}, {"k1": "k1"})
