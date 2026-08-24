"""Unit tests for docsforge.yaml_utils."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

from docsforge import exceptions
from docsforge.yaml_utils import get_yaml_loader, yaml_load


class TestGetYamlLoader:
    def test_default_loader_is_safe(self):
        loader = get_yaml_loader()
        assert issubclass(loader, yaml.SafeLoader)
        assert not issubclass(loader, yaml.Loader)


class TestInherit:
    def _write_configs(self, tmp_path: Path, child_body: str, parent_body: str) -> tuple[Path, Path]:
        parent = tmp_path / "parent.yml"
        parent.write_text(textwrap.dedent(parent_body).strip() + "\n")
        child = tmp_path / "child.yml"
        child.write_text(textwrap.dedent(child_body).strip() + "\n")
        return child, parent

    def test_inherit_merges_parent(self, tmp_path):
        child, _ = self._write_configs(
            tmp_path,
            """
            INHERIT: parent.yml
            site_name: Child
            """,
            """
            site_name: Parent
            extra:
              key: value
            """,
        )
        with open(child, "rb") as fd:
            result = yaml_load(fd)
        assert result["site_name"] == "Child"
        assert result["extra"]["key"] == "value"

    def test_inherit_traversal_rejected(self, tmp_path):
        child, _ = self._write_configs(
            tmp_path,
            """
            INHERIT: ../parent.yml
            site_name: Child
            """,
            "site_name: Parent\n",
        )
        with open(child, "rb") as fd, pytest.raises(exceptions.ConfigurationError):
            yaml_load(fd)

    def test_inherit_directory_rejected(self, tmp_path):
        child, _ = self._write_configs(
            tmp_path,
            """
            INHERIT: subdir
            site_name: Child
            """,
            "site_name: Parent\n",
        )
        (tmp_path / "subdir").mkdir()
        with open(child, "rb") as fd, pytest.raises(exceptions.ConfigurationError):
            yaml_load(fd)

    def test_inherit_missing_rejected(self, tmp_path):
        child = tmp_path / "child.yml"
        child.write_text("INHERIT: missing.yml\nsite_name: Child\n")
        with open(child, "rb") as fd, pytest.raises(exceptions.ConfigurationError):
            yaml_load(fd)
