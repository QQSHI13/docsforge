"""Unit tests for docsforge.build."""
from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import Mock

import pytest

from docsforge import build as build_mod
from docsforge.build import _write_outputs
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
