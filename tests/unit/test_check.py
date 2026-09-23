"""Unit tests for docsforge.check."""
from __future__ import annotations

import textwrap
from pathlib import Path

import yaml

from docsforge.check import fix_config


def _write_config(root: Path, body: str) -> Path:
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs" / "index.md").write_text("# Home\n")
    cfg = root / "docsforge.yml"
    cfg.write_text(textwrap.dedent(body).strip() + "\n")
    return cfg


class TestFixConfig:
    def test_removes_builtin_plugins(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_config(
            tmp_path,
            """
            site_name: Test
            plugins:
              - search
              - tags
              - some-third-party
            """,
        )
        assert fix_config() == 0
        raw = (tmp_path / "docsforge.yml").read_text()
        assert "search" not in raw
        assert "tags" not in raw
        assert "some-third-party" in raw

    def test_fix_config_no_op_when_clean(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path, "site_name: Test\n")
        assert fix_config() == 0

    def test_preserves_string_theme_when_no_top_level_keys(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path, "site_name: Test\ntheme: material\n")
        assert fix_config() == 0
        raw = yaml.safe_load((tmp_path / "docsforge.yml").read_text())
        assert raw["theme"] == "material"

    def test_promotes_string_theme_when_top_level_keys_present(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_config(
            tmp_path,
            """
            site_name: Test
            theme: material
            palette:
              - scheme: default
                primary: teal
            """,
        )
        assert fix_config() == 0
        raw = yaml.safe_load((tmp_path / "docsforge.yml").read_text())
        assert raw["theme"] == {
            "name": "material",
            "palette": [{"scheme": "default", "primary": "teal"}],
        }
        assert "palette" not in raw

    def test_merges_top_level_keys_into_dict_theme(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_config(
            tmp_path,
            """
            site_name: Test
            theme:
              name: material
            features:
              - navigation.tabs
            """,
        )
        assert fix_config() == 0
        raw = yaml.safe_load((tmp_path / "docsforge.yml").read_text())
        assert raw["theme"] == {
            "name": "material",
            "features": ["navigation.tabs"],
        }
        assert "features" not in raw


class TestBuiltinPluginDeclarations:
    def test_fix_config_keeps_options_carrying_builtins(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_config(
            tmp_path,
            """
            site_name: Test
            plugins:
              - search
              - privacy:
                  enabled: false
              - blog: {}
            """,
        )
        assert fix_config() == 0
        raw = (tmp_path / "docsforge.yml").read_text()
        assert "search" not in raw
        assert "enabled: false" in raw
        assert "blog" not in raw


class TestCheckNav:
    def _run_check(self, tmp_path, monkeypatch, capsys):
        from docsforge.check import check

        monkeypatch.chdir(tmp_path)
        rc = check()
        out = capsys.readouterr().out
        return rc, out

    def test_nav_missing_file_is_error(self, tmp_path, monkeypatch, capsys):
        _write_config(
            tmp_path,
            """
            site_name: Test
            nav:
              - Home: index.md
              - Ghost: ghost.md
            """,
        )
        rc, out = self._run_check(tmp_path, monkeypatch, capsys)
        assert rc == 1
        assert "ghost.md" in out

    def test_unreferenced_page_warns(self, tmp_path, monkeypatch, capsys):
        _write_config(
            tmp_path,
            """
            site_name: Test
            nav:
              - Home: index.md
            """,
        )
        (tmp_path / "docs" / "orphan.md").write_text("# Orphan\n")
        rc, out = self._run_check(tmp_path, monkeypatch, capsys)
        assert rc == 0
        assert "orphan.md" in out

    def test_i18n_twins_do_not_warn(self, tmp_path, monkeypatch, capsys):
        _write_config(
            tmp_path,
            """
            site_name: Test
            extra:
              i18n_languages:
                - locale: en
                  name: English
                  default: true
                - locale: zh
                  name: Chinese
            nav:
              - Home: index.md
            """,
        )
        (tmp_path / "docs" / "index.zh.md").write_text("# Home ZH\n")
        (tmp_path / "docs" / "other.md").write_text("# Other\n")
        (tmp_path / "docs" / "other.zh.md").write_text("# Other ZH\n")
        rc, out = self._run_check(tmp_path, monkeypatch, capsys)
        assert rc == 0
        # Twins are covered by their base entry: never reported...
        assert "index.zh.md" not in out
        assert "other.zh.md" not in out
        # ...while a genuinely unreferenced base warns exactly once.
        assert "other.md" in out

    def test_malformed_nav_warns(self, tmp_path, monkeypatch, capsys):
        _write_config(
            tmp_path,
            """
            site_name: Test
            nav:
              - {title: Empty}
            """,
        )
        rc, out = self._run_check(tmp_path, monkeypatch, capsys)
        assert rc == 0
        assert "neither 'path' nor 'children'" in out

    def test_missing_extra_asset_warns(self, tmp_path, monkeypatch, capsys):
        _write_config(
            tmp_path,
            """
            site_name: Test
            nav:
              - Home: index.md
            extra_css:
              - css/missing.css
              - https://cdn.example/x.css
            """,
        )
        rc, out = self._run_check(tmp_path, monkeypatch, capsys)
        assert rc == 0
        assert "css/missing.css" in out
        assert "cdn.example" not in out


class TestLivereloadShutdown:
    def test_shutdown_before_serve_starts(self, tmp_path):
        from docsforge.livereload import LiveReloadServer

        server = LiveReloadServer(
            builder=lambda: None,
            host="127.0.0.1",
            port=0,
            root=str(tmp_path),
            mount_path="/",
        )
        server.shutdown(wait=True)  # must not raise RuntimeError


class TestDisabledPluginDisplay:
    def test_disabled_builtins_show_disabled_without_warning(
        self, tmp_path, monkeypatch, capsys
    ):
        from docsforge.check import check

        (tmp_path / "docs").mkdir(exist_ok=True)
        (tmp_path / "docs" / "index.md").write_text("# Home\n")
        (tmp_path / "docsforge.yml").write_text(
            "site_name: Test\n"
            "plugins:\n"
            "  - privacy:\n"
            "      enabled: false\n"
            "  - search\n"
            "nav:\n"
            "  - Home: index.md\n"
        )
        monkeypatch.chdir(tmp_path)
        assert check() == 0
        out = capsys.readouterr().out
        assert "✗ privacy (disabled)" in out
        # The bare `search` redeclaration still warns; the options-carrying
        # privacy declaration must not.
        assert "'search' is built-in" in out
        assert "'privacy' is built-in" not in out
