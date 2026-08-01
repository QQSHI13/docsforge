"""Unit tests for docsforge.check."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

from docsforge.check import check, fix_config


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
