"""Unit tests for docsforge.nav."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from docsforge.exceptions import BuildError
from docsforge.nav import Link, Page, Section, _data_to_navigation
from docsforge.config_base import load_config


def _write_config(root: Path) -> Path:
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs" / "index.md").write_text("# Home\n")
    cfg = root / "docsforge.yml"
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
    return cfg


@pytest.fixture()
def nav_config(tmp_path):
    cfg_path = _write_config(tmp_path)
    return load_config(config_file=str(cfg_path))


class TestDataToNavigationValidation:
    def test_string_entry_is_accepted(self, nav_config):
        from docsforge.files import Files

        result = _data_to_navigation("index.md", Files([]), nav_config)
        assert isinstance(result, Link)
        assert result.url == "index.md"

    def test_dict_with_string_value_is_accepted(self, nav_config, tmp_path):
        from docsforge.files import File, Files

        file = File("index.md", str(tmp_path), str(tmp_path / "site"), True)
        files = Files([file])
        result = _data_to_navigation({"Home": "index.md"}, files, nav_config)
        assert isinstance(result[0], Page)

    def test_non_string_path_raises(self, nav_config):
        with pytest.raises(BuildError, match="nav entry must be a string"):
            _data_to_navigation(123, None, nav_config)

    def test_non_string_key_raises(self, nav_config):
        with pytest.raises(BuildError, match="nav entry key must be a string"):
            _data_to_navigation({123: "index.md"}, None, nav_config)

    def test_non_string_value_in_list_raises(self, nav_config):
        with pytest.raises(BuildError, match="nav entry value must be a string"):
            _data_to_navigation([{"Home": 123}], None, nav_config)

    def test_multi_key_dict_in_list_raises(self, nav_config):
        with pytest.raises(BuildError, match="exactly one key"):
            _data_to_navigation([{"A": "a.md", "B": "b.md"}], None, nav_config)

    def test_non_string_value_in_dict_raises(self, nav_config):
        with pytest.raises(BuildError, match="nav entry value must be a string"):
            _data_to_navigation({"Home": 123}, None, nav_config)

    def test_dict_with_nested_string_value_is_accepted(self, nav_config, tmp_path):
        from docsforge.files import File, Files

        file = File("index.md", str(tmp_path), str(tmp_path / "site"), True)
        files = Files([file])
        result = _data_to_navigation({"Section": {"Home": "index.md"}}, files, nav_config)
        assert result[0].title == "Section"
        assert isinstance(result[0].children[0], Page)

    def test_dict_with_list_value_in_list_is_accepted(self, nav_config, tmp_path):
        from docsforge.files import File, Files

        file_a = File("publishing-your-site.md", str(tmp_path), str(tmp_path / "site"), True)
        file_b = File("writing-your-docs.md", str(tmp_path), str(tmp_path / "site"), True)
        files = Files([file_a, file_b])
        result = _data_to_navigation(
            [{"Publishing": ["publishing-your-site.md", "writing-your-docs.md"]}],
            files,
            nav_config,
        )
        section = result[0]
        assert isinstance(section, Section)
        assert section.title == "Publishing"
        assert isinstance(section.children[0], Page)
        assert section.children[0].file.src_uri == "publishing-your-site.md"
        assert isinstance(section.children[1], Page)
        assert section.children[1].file.src_uri == "writing-your-docs.md"

    def test_dict_with_nested_dict_value_in_list_is_accepted(self, nav_config, tmp_path):
        from docsforge.files import File, Files

        file = File("index.md", str(tmp_path), str(tmp_path / "site"), True)
        files = Files([file])
        result = _data_to_navigation(
            [{"Section": {"Home": "index.md"}}],
            files,
            nav_config,
        )
        section = result[0]
        assert isinstance(section, Section)
        assert section.title == "Section"
        assert isinstance(section.children[0], Page)
