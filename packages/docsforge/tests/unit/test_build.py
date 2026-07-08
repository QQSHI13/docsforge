"""Unit tests for docsforge.build."""
from __future__ import annotations

import textwrap
import threading
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from docsforge import build as build_mod
from docsforge.build import (
    _build_page,
    _default_page_lock,
    _finalize_build,
    _populate_changed_pages,
    _remove_orphaned_output,
    _write_outputs,
)
from docsforge.config_base import load_config
from docsforge.exceptions import BuildError
from docsforge.files import File, Files
from docsforge.pages import Page


def _load_config(tmp_path: Path):
    (tmp_path / "docs").mkdir(exist_ok=True)
    (tmp_path / "docs" / "index.md").write_text("# Home\n")
    cfg = tmp_path / "docsforge.yml"
    cfg.write_text(
        textwrap.dedent(
            """
            site_name: Test
            docs_dir: docs
            site_dir: site
            privacy: false
            theme:
              name: material
              palette:
                - scheme: default
                  primary: teal
                  accent: teal
            """
        ).strip()
        + "\n"
    )
    return load_config(config_file=str(cfg))


class TestWriteOutputsStrictMode:
    def test_re_raises_in_strict_mode(self, tmp_path, monkeypatch):
        cfg = _load_config(tmp_path)
        cfg.strict = True
        monkeypatch.chdir(tmp_path)

        file = File("page.md", cfg.docs_dir, cfg.site_dir, cfg.use_directory_urls)
        files = Files([file])
        Page(None, file, cfg)

        planner = Mock()
        planner.should_rebuild.return_value = True

        nav = Mock()
        env = Mock()
        env.get_template.return_value = Mock(render=Mock(return_value="<p>x</p>"))

        cfg.plugins.on_env = Mock(return_value=env)
        cfg.plugins.on_post_build = Mock()

        def _bad_build_page(*args, **kwargs):
            raise BuildError("page failure")

        monkeypatch.setattr(build_mod, "_build_page", _bad_build_page)

        with pytest.raises(BuildError, match="page failure"):
            _write_outputs(cfg, files, nav, env, planner, [file], lambda level: True)

    def test_swallows_errors_when_not_strict(self, tmp_path, monkeypatch):
        cfg = _load_config(tmp_path)
        cfg.strict = False
        monkeypatch.chdir(tmp_path)

        file = File("page.md", cfg.docs_dir, cfg.site_dir, cfg.use_directory_urls)
        files = Files([file])
        Page(None, file, cfg)

        planner = Mock()
        planner.should_rebuild.return_value = True

        nav = Mock()
        env = Mock()
        env.get_template.return_value = Mock(render=Mock(return_value="<p>x</p>"))

        cfg.plugins.on_env = Mock(return_value=env)
        cfg.plugins.on_post_build = Mock()

        def _bad_build_page(*args, **kwargs):
            raise BuildError("page failure")

        monkeypatch.setattr(build_mod, "_build_page", _bad_build_page)

        # Should not raise when strict is False.
        _write_outputs(cfg, files, nav, env, planner, [file], lambda level: True)


class TestPopulateChangedPagesErrors:
    def test_collects_all_populate_errors(self, tmp_path, monkeypatch):
        cfg = _load_config(tmp_path)
        monkeypatch.chdir(tmp_path)

        file_a = File("a.md", cfg.docs_dir, cfg.site_dir, cfg.use_directory_urls)
        file_b = File("b.md", cfg.docs_dir, cfg.site_dir, cfg.use_directory_urls)
        files = Files([file_a, file_b])
        Page(None, file_a, cfg)
        Page(None, file_b, cfg)

        def _bad_populate(*args, **kwargs):
            raise BuildError("boom")

        monkeypatch.setattr(build_mod, "_populate_page", _bad_populate)

        with pytest.raises(ExceptionGroup, match="Errors populating pages") as exc_info:
            _populate_changed_pages(cfg, files, Mock(), [file_a, file_b], lambda level: True, None)
        assert len(exc_info.value.exceptions) == 2


class TestFinalizeBuildOrder:
    def test_pwa_generation_runs_after_post_build(self, tmp_path, monkeypatch):
        cfg = _load_config(tmp_path)
        monkeypatch.chdir(tmp_path)

        calls = []
        cfg.plugins.on_post_build = Mock(side_effect=lambda **kw: calls.append("on_post_build"))

        planner = Mock()
        planner.save = Mock()

        warning_counter = Mock()
        warning_counter.get_counts.return_value = None

        with patch.object(build_mod, "_generate_pwa_manifest_and_precache", lambda *a, **k: calls.append("pwa")):
            _finalize_build(
                cfg,
                Files([]),
                Mock(homepage=None),
                planner,
                warning_counter,
                built_any=False,
                sources_changed=False,
                config_path=Path("docsforge.yml"),
                theme_sig="",
                start=0.0,
            )

        assert calls == ["on_post_build", "pwa"]


class TestBuildPageLock:
    def test_default_lock_is_shared_module_singleton(self):
        # The fallback lock used when _page_lock is None must be shared across
        # calls, otherwise concurrent calls serialize on different locks.
        assert isinstance(_default_page_lock, type(threading.Lock()))
        # _build_page signature keeps _page_lock default as None for callers.
        assert _build_page.__defaults__[-1] is None


class TestWriteOutputsSuccessTracking:
    def test_returns_false_when_all_pages_fail(self, tmp_path, monkeypatch):
        cfg = _load_config(tmp_path)
        cfg.strict = False
        monkeypatch.chdir(tmp_path)

        file = File("page.md", cfg.docs_dir, cfg.site_dir, cfg.use_directory_urls)
        files = Files([file])
        Page(None, file, cfg)

        planner = Mock()
        planner.should_rebuild.return_value = True

        nav = Mock()
        env = Mock()
        env.get_template.return_value = Mock(render=Mock(return_value="<p>x</p>"))

        cfg.plugins.on_env = Mock(return_value=env)
        cfg.plugins.on_post_build = Mock()

        def _bad_build_page(*args, **kwargs):
            raise BuildError("page failure")

        monkeypatch.setattr(build_mod, "_build_page", _bad_build_page)

        result = _write_outputs(cfg, files, nav, env, planner, [file], lambda level: True)
        assert result is False


class TestRemoveOrphanedOutput:
    def test_logs_warning_on_oserror(self, tmp_path, caplog):
        missing = tmp_path / "does_not_exist.html"
        with caplog.at_level("WARNING", logger="docsforge.build"):
            _remove_orphaned_output(missing)
        assert "Could not remove orphaned output" in caplog.text
