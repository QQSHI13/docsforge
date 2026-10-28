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

    def test_inherit_mixed_drives_rejected(self, tmp_path, monkeypatch):
        # On Windows, os.path.commonpath raises ValueError for paths on different
        # drives; that must surface as a clear ConfigurationError.
        child = tmp_path / "child.yml"
        child.write_text("INHERIT: D:/other/parent.yml\nsite_name: Child\n")

        def fake_commonpath(paths):
            raise ValueError("Paths don't have the same drive")

        monkeypatch.setattr("os.path.commonpath", fake_commonpath)
        with open(child, "rb") as fd, pytest.raises(
            exceptions.ConfigurationError, match="outside the config directory"
        ):
            yaml_load(fd)

    def test_inherit_self_reference_rejected(self, tmp_path):
        child = tmp_path / "child.yml"
        child.write_text("INHERIT: child.yml\nsite_name: Child\n")
        with open(child, "rb") as fd, pytest.raises(
            exceptions.ConfigurationError, match="Circular INHERIT chain"
        ):
            yaml_load(fd)

    def test_inherit_cycle_rejected(self, tmp_path):
        (tmp_path / "a.yml").write_text("INHERIT: b.yml\nsite_name: A\n")
        (tmp_path / "b.yml").write_text("INHERIT: a.yml\nsite_name: B\n")
        with open(tmp_path / "a.yml", "rb") as fd, pytest.raises(
            exceptions.ConfigurationError, match="Circular INHERIT chain"
        ):
            yaml_load(fd)

    def test_inherit_cycle_error_names_the_cycle(self, tmp_path):
        (tmp_path / "a.yml").write_text("INHERIT: b.yml\nsite_name: A\n")
        (tmp_path / "b.yml").write_text("INHERIT: a.yml\nsite_name: B\n")
        with open(tmp_path / "a.yml", "rb") as fd, pytest.raises(
            exceptions.ConfigurationError
        ) as excinfo:
            yaml_load(fd)
        message = str(excinfo.value)
        assert "a.yml" in message and "b.yml" in message
        assert "a.yml -> " in message

    def test_inherit_chain_still_merges(self, tmp_path):
        (tmp_path / "base.yml").write_text("site_name: Base\nextra:\n  from_base: 1\n")
        (tmp_path / "mid.yml").write_text("INHERIT: base.yml\nmid: 1\n")
        child = tmp_path / "child.yml"
        child.write_text("INHERIT: mid.yml\nchild: 1\n")
        with open(child, "rb") as fd:
            result = yaml_load(fd)
        assert result["site_name"] == "Base"
        assert result["extra"]["from_base"] == 1
        assert result["mid"] == 1 and result["child"] == 1


class TestDuplicateKeys:
    def test_duplicate_top_level_key_rejected(self, tmp_path):
        cfg = tmp_path / "dup.yml"
        cfg.write_text("site_name: One\nsite_name: Two\n")
        with open(cfg, "rb") as fd, pytest.raises(exceptions.ConfigurationError) as excinfo:
            yaml_load(fd)
        message = str(excinfo.value)
        assert "Duplicate key 'site_name'" in message
        assert "line 1" in message and "line 2" in message
        assert "dup.yml" in message

    def test_duplicate_nested_key_rejected(self, tmp_path):
        cfg = tmp_path / "dup.yml"
        cfg.write_text("theme:\n  name: material\n  name: mkdocs\n")
        with open(cfg, "rb") as fd, pytest.raises(
            exceptions.ConfigurationError, match="Duplicate key 'name'"
        ):
            yaml_load(fd)

    def test_merge_keys_still_allowed(self, tmp_path):
        # `<<:` may legitimately repeat; flatten_mapping merges them.
        cfg = tmp_path / "merge.yml"
        cfg.write_text("base: &b {x: 1}\nchild:\n  <<: *b\n  y: 2\n")
        with open(cfg, "rb") as fd:
            assert yaml_load(fd)["child"] == {"x": 1, "y": 2}

    def test_unique_keys_unaffected(self, tmp_path):
        cfg = tmp_path / "ok.yml"
        cfg.write_text("site_name: One\nsite_url: https://example.com\n")
        with open(cfg, "rb") as fd:
            assert yaml_load(fd) == {"site_name": "One", "site_url": "https://example.com"}


class TestPythonNameTag:
    def test_unresolvable_module_reports_helpful_error(self, tmp_path):
        cfg = tmp_path / "cfg.yml"
        cfg.write_text("slugify: !!python/name:not_a_real_module_xyz.func\n")
        with open(cfg, "rb") as fd, pytest.raises(exceptions.ConfigurationError) as excinfo:
            yaml_load(fd)
        message = str(excinfo.value)
        assert "not_a_real_module_xyz.func" in message
        assert "module.attr" in message

    def test_unresolvable_attribute_reports_helpful_error(self, tmp_path):
        cfg = tmp_path / "cfg.yml"
        cfg.write_text("slugify: !!python/name:json.not_a_real_attr\n")
        with open(cfg, "rb") as fd, pytest.raises(exceptions.ConfigurationError) as excinfo:
            yaml_load(fd)
        assert "not_a_real_attr" in str(excinfo.value)

    def test_resolvable_tag_returns_the_object(self, tmp_path):
        cfg = tmp_path / "cfg.yml"
        cfg.write_text("value: !!python/name:pymdownx.slugs.uslugify\n")
        with open(cfg, "rb") as fd:
            assert callable(yaml_load(fd)["value"])

    def test_non_markdown_module_is_logged_at_debug(self, tmp_path, caplog):
        cfg = tmp_path / "cfg.yml"
        cfg.write_text("value: !!python/name:json.dumps\n")
        with caplog.at_level("DEBUG", logger="docsforge.yaml_utils"), open(cfg, "rb") as fd:
            yaml_load(fd)
        assert any("non-Markdown module" in r.message for r in caplog.records)

    def test_markdown_module_is_not_logged(self, tmp_path, caplog):
        cfg = tmp_path / "cfg.yml"
        cfg.write_text("value: !!python/name:pymdownx.slugs.uslugify\n")
        with caplog.at_level("DEBUG", logger="docsforge.yaml_utils"), open(cfg, "rb") as fd:
            yaml_load(fd)
        assert not [r for r in caplog.records if "non-Markdown module" in r.message]
