"""Unit tests for docsforge.check."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

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
