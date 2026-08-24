"""Unit tests for docsforge.theme."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from docsforge import utils
from docsforge.config_base import ValidationError
from docsforge.theme import Theme


class TestThemeEnvironment:
    def test_autoescape_enabled(self):
        theme = Theme(name="material")
        env = theme.get_env()
        assert env.autoescape  # callable from select_autoescape, truthy for html/xml


class TestRedirectTemplate:
    def _render(self, location: str):
        theme = Theme(name="material")
        env = theme.get_env()
        page = SimpleNamespace(meta={"location": location})
        config = SimpleNamespace(site_name="Test")
        return env.get_template("redirect.html").render(page=page, config=config)

    def test_allows_https_url(self):
        out = self._render("https://example.com/page")
        assert "url=https://example.com/page" in out
        assert "window.location.replace" in out

    def test_allows_site_relative_path(self):
        out = self._render("/new-location/")
        assert "url=/new-location/" in out
        assert "window.location.replace" in out

    def test_blocks_javascript_scheme(self):
        out = self._render("javascript:alert(1)")
        assert 'http-equiv="refresh"' not in out
        assert "window.location.replace" not in out

    def test_blocks_protocol_relative_url(self):
        out = self._render("//evil.com/")
        assert 'http-equiv="refresh"' not in out
        assert "window.location.replace" not in out


class TestThemeConfigLoading:
    def test_loads_config_for_requested_theme_name(self, monkeypatch):
        """The theme config must be loaded for the requested theme name.

        Regression test: the loop over the built-in static templates used to
        rebind the `name` parameter, so the config was always loaded for
        'sitemap.xml' instead of the requested theme.
        """
        loaded = []
        monkeypatch.setattr(
            Theme, "_load_theme_config", lambda self, name: loaded.append(name)
        )
        Theme(name="mytheme")
        assert loaded == ["mytheme"]

    def test_no_theme_config_loaded_without_name(self, monkeypatch):
        loaded = []
        monkeypatch.setattr(
            Theme, "_load_theme_config", lambda self, name: loaded.append(name)
        )
        Theme()
        assert loaded == []


class TestThemeConfigValidation:
    @pytest.fixture()
    def theme_dir(self, tmp_path, monkeypatch):
        """Serve theme configs from a tmp dir instead of the installed themes."""
        monkeypatch.setattr(utils, "get_theme_dir", lambda name: str(tmp_path))
        return tmp_path

    def test_missing_config_file_raises_validation_error(self, theme_dir):
        with pytest.raises(
            ValidationError, match="does not appear to have a configuration file"
        ):
            Theme(name="brokentheme")

    def test_invalid_yaml_raises_validation_error(self, theme_dir):
        (theme_dir / "docsforge_theme.yml").write_text("palette: [unclosed\n")
        with pytest.raises(ValidationError, match="invalid configuration file"):
            Theme(name="brokentheme")

    def test_extends_must_be_a_string(self, theme_dir):
        (theme_dir / "docsforge_theme.yml").write_text("extends:\n  - foo\n  - bar\n")
        with pytest.raises(ValidationError, match="invalid 'extends' value"):
            Theme(name="brokentheme")

    def test_extends_unknown_parent_raises_validation_error(self, theme_dir, monkeypatch):
        monkeypatch.setattr(utils, "get_theme_names", lambda: ["material"])
        (theme_dir / "docsforge_theme.yml").write_text("extends: nosuchtheme\n")
        with pytest.raises(ValidationError, match="does not appear to be installed"):
            Theme(name="childtheme")

    def test_extends_loads_parent_theme(self, tmp_path, monkeypatch):
        parent = tmp_path / "parent"
        child = tmp_path / "child"
        parent.mkdir()
        child.mkdir()
        (parent / "docsforge_theme.yml").write_text(
            "static_templates:\n  - parent.html\n"
        )
        (child / "docsforge_theme.yml").write_text(
            "extends: parent\nstatic_templates:\n  - child.html\n"
        )
        monkeypatch.setattr(utils, "get_theme_dir", lambda name: str(tmp_path / name))
        monkeypatch.setattr(utils, "get_theme_names", lambda: ["parent", "child"])
        theme = Theme(name="child")
        assert {"parent.html", "child.html"} <= theme.static_templates

    def test_static_templates_must_be_a_list(self, theme_dir):
        (theme_dir / "docsforge_theme.yml").write_text("static_templates: justastring\n")
        with pytest.raises(ValidationError, match="invalid 'static_templates' value"):
            Theme(name="brokentheme")

    def test_static_templates_items_must_be_strings(self, theme_dir):
        (theme_dir / "docsforge_theme.yml").write_text(
            "static_templates:\n  - 404.html\n  - 123\n"
        )
        with pytest.raises(ValidationError, match="invalid 'static_templates' value"):
            Theme(name="brokentheme")


class TestThemeNameSync:
    def test_theme_config_name_key_does_not_desync(self, tmp_path, monkeypatch):
        """A 'name' key in docsforge_theme.yml must not override the theme name."""
        (tmp_path / "docsforge_theme.yml").write_text("name: eviltheme\n")
        monkeypatch.setattr(utils, "get_theme_dir", lambda name: str(tmp_path))
        theme = Theme(name="mytheme")
        assert theme.name == "mytheme"
        assert theme["name"] == "mytheme"

    def test_user_config_does_not_desync_name(self):
        theme = Theme(name="mytheme", palette=[], direction="ltr")
        assert theme.name == "mytheme"
        assert theme["name"] == "mytheme"
