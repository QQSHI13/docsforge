"""Unit tests for init.py — the project scaffolding generator."""
from __future__ import annotations

from docsforge.init import (
    COLOR_MAP,
    _generate_config,
    _generate_gitignore,
    _generate_readme,
)


class TestGenerateConfig:
    def test_minimal_config(self):
        cfg = _generate_config(
            site_name="My Docs",
            site_url=None,
            theme_color="teal",
            privacy=False,
        )
        assert "site_name: My Docs" in cfg
        assert "theme:" in cfg
        assert "name: material" in cfg
        assert "primary: teal" in cfg

    def test_includes_repo_url_and_edit_uri(self):
        cfg = _generate_config(
            site_name="X",
            site_url=None,
            theme_color="teal",
            privacy=False,
            repo_url="https://github.com/u/r",
        )
        assert "repo_url: https://github.com/u/r" in cfg
        assert "edit_uri:" in cfg

    def test_privacy_flag_emits_config(self):
        cfg = _generate_config("X", None, "teal", privacy=True)
        assert "privacy:" in cfg

    def test_all_color_presets_map(self):
        for color in COLOR_MAP:
            cfg = _generate_config("X", None, color, False)
            primary = COLOR_MAP[color]["primary"]
            assert f"primary: {primary}" in cfg

    def test_unknown_color_falls_back_to_teal(self):
        cfg = _generate_config("X", None, "not-a-color", False)
        assert "primary: teal" in cfg

    def test_site_description_included(self):
        cfg = _generate_config("X", None, "teal", False, site_description="A description")
        assert "site_description: A description" in cfg

    def test_author_and_copyright(self):
        cfg = _generate_config("X", None, "teal", False, author_name="QQ", copyright="2026 QQ")
        assert "QQ" in cfg


class TestGenerateReadme:
    def test_contains_site_name(self):
        rd = _generate_readme("My Project")
        assert "My Project" in rd
        assert "docsforge" in rd.lower()


class TestGenerateGitignore:
    def test_ignores_site_and_cache(self):
        gi = _generate_gitignore()
        assert "site/" in gi
        assert ".docsforge/" in gi or "cache" in gi.lower()
