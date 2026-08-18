"""Unit tests for the social plugin (docsforge.core.social).

The social plugin is a flattened, vendored port of mkdocs-material's social
plugin. Rendering cards requires the optional `pillow` and `cairosvg`
dependencies (`docsforge[social]`); tests that exercise actual rendering are
guarded with `pytest.importorskip` and skip when the deps are missing.
"""
from __future__ import annotations

import logging
import textwrap
from pathlib import Path

import pytest

from docsforge import config_options
from docsforge.config_base import load_config
from docsforge.core import social as social_module
from docsforge.core.social import SocialPlugin


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
            site_url: https://example.com/
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


class TestConfig:
    def test_valid_options_load(self):
        plugin = SocialPlugin()
        errors, warnings = plugin.load_config({
            "enabled": True,
            "cache": True,
            "cache_dir": ".docsforge/cache/social",
            "log": True,
            "log_level": "info",
            "cards": True,
            "cards_dir": "assets/images/social",
            "cards_layout": "variant",
            "cards_layout_options": {"background_color": "#123456"},
            "cards_include": ["*.md"],
            "cards_exclude": ["drafts/*"],
            "debug": False,
            "debug_on_build": False,
            "debug_grid": True,
            "debug_grid_step": 32,
            "debug_color": "grey",
        })
        assert errors == []
        assert warnings == []
        assert plugin.config.cards_layout == "variant"
        assert plugin.config.cards_include == ["*.md"]
        assert plugin.config.cards_layout_options["background_color"] == "#123456"

    def test_defaults(self):
        plugin = SocialPlugin()
        errors, warnings = plugin.load_config({})
        assert errors == []
        assert warnings == []
        assert plugin.config.enabled is True
        assert plugin.config.cache is True
        assert plugin.config.cache_dir == ".docsforge/cache/social"
        assert plugin.config.log is True
        assert plugin.config.log_level == "warn"
        assert plugin.config.cards_layout == "default"
        assert plugin.config.cards_layout_options == {}
        assert plugin.config.cards_include == []
        assert plugin.config.cards_exclude == []
        assert plugin.config.debug is False

    def test_invalid_option_types_raise(self):
        plugin = SocialPlugin()
        errors, warnings = plugin.load_config({"cache": "yes"})
        assert [key for key, _ in errors] == ["cache"]
        assert isinstance(plugin.config, config_options.Config)

    def test_unknown_options_warn(self):
        plugin = SocialPlugin()
        errors, warnings = plugin.load_config({"concurrency": 4})
        assert errors == []
        # The concurrency option moved to the global config in 12.5.4;
        # plugin-level usage is reported as a warning.
        assert any(key == "concurrency" for key, _ in warnings)
        # Other unknown options warn the same way.
        errors, warnings = plugin.load_config({"cards_font": "Comic Sans"})
        assert errors == []
        assert any(key == "cards_font" for key, _ in warnings)

    def test_not_auto_loaded(self, tmp_path):
        # Social has heavy optional deps (Pillow, cairosvg), so it must NOT
        # auto-load like the other core plugins — only when declared under
        # `plugins:`.
        cfg = _load_config(tmp_path)
        assert "material/social" not in cfg.plugins

    def test_loads_when_declared(self, tmp_path):
        (tmp_path / "docs").mkdir(exist_ok=True)
        (tmp_path / "docs" / "index.md").write_text("# Home\n")
        cfg = tmp_path / "docsforge.yml"
        cfg.write_text(
            textwrap.dedent(
                """
                site_name: Test
                docs_dir: docs
                site_dir: site
                site_url: https://example.com/
                theme:
                  name: material
                plugins:
                  - social
                """
            ).strip()
            + "\n"
        )
        loaded = load_config(config_file=str(cfg))
        assert "material/social" in loaded.plugins
        assert isinstance(loaded.plugins["material/social"], SocialPlugin)


class TestMissingDeps:
    """on_config must warn (not crash) when rendering deps are unavailable."""

    def test_on_config_warns_when_deps_missing(self, tmp_path, caplog, monkeypatch):
        monkeypatch.setattr(social_module, "import_errors", {"ModuleNotFoundError('no PIL')"})
        monkeypatch.setattr(social_module, "cairosvg_error", "")
        plugin = SocialPlugin()
        errors, warnings = plugin.load_config({"cache_dir": str(tmp_path / ".cache")})
        assert errors == []
        cfg = _load_config(tmp_path)
        with caplog.at_level(logging.WARNING, logger="mkdocs.material.social"):
            plugin.on_config(cfg)
        assert "docsforge[social]" in caplog.text
        assert "Required dependencies" in caplog.text

    def test_on_config_warns_on_cairosvg_runtime_error(self, tmp_path, caplog, monkeypatch):
        monkeypatch.setattr(social_module, "import_errors", set())
        monkeypatch.setattr(social_module, "cairosvg_error", "boom")
        plugin = SocialPlugin()
        plugin.load_config({"cache_dir": str(tmp_path / ".cache")})
        cfg = _load_config(tmp_path)
        with caplog.at_level(logging.WARNING, logger="mkdocs.material.social"):
            plugin.on_config(cfg)
        assert "cairosvg" in caplog.text and "boom" in caplog.text

    def test_on_config_silent_when_deps_present(self, tmp_path, caplog, monkeypatch):
        monkeypatch.setattr(social_module, "import_errors", set())
        monkeypatch.setattr(social_module, "cairosvg_error", "")
        plugin = SocialPlugin()
        plugin.load_config({"cache_dir": str(tmp_path / ".cache")})
        cfg = _load_config(tmp_path)
        with caplog.at_level(logging.WARNING, logger="mkdocs.material.social"):
            plugin.on_config(cfg)
        assert "docsforge[social]" not in caplog.text
        assert "Required dependencies" not in caplog.text


class TestLayouts:
    def test_embedded_layouts_resolve(self, tmp_path):
        plugin = SocialPlugin()
        plugin.load_config({"cache_dir": str(tmp_path / ".cache")})
        cfg = _load_config(tmp_path)
        plugin.on_config(cfg)

        # All embedded layouts must resolve and validate, independent of the
        # rendering dependencies
        for name in ("default", "variant", "accent", "invert", "image"):
            layout, variables = plugin._resolve_layout(name, cfg)
            assert layout.size.width > 0 and layout.size.height > 0
            assert len(layout.layers) == len(variables)

    def test_unknown_layout_raises(self, tmp_path):
        plugin = SocialPlugin()
        plugin.load_config({"cache_dir": str(tmp_path / ".cache")})
        cfg = _load_config(tmp_path)
        plugin.on_config(cfg)
        with pytest.raises(Exception, match="Couldn't find layout"):
            plugin._resolve_layout("does-not-exist", cfg)

    def test_custom_layout_dir_overrides(self, tmp_path):
        layouts = tmp_path / "custom-layouts"
        layouts.mkdir()
        (layouts / "custom.yml").write_text(
            textwrap.dedent(
                """
                size: { width: 800, height: 400 }
                layers:
                  - background:
                      color: "#000000"
                """
            ).strip()
            + "\n"
        )
        plugin = SocialPlugin()
        plugin.load_config({
            "cache_dir": str(tmp_path / ".cache"),
            "cards_layout_dir": str(layouts),
        })
        cfg = _load_config(tmp_path)
        plugin.on_config(cfg)
        layout, _ = plugin._resolve_layout("custom.yml", cfg)
        assert layout.size.width == 800
        assert layout.size.height == 400
        assert layout.layers[0].background.color == "#000000"


@pytest.mark.parametrize("layout_name", ["default", "variant", "accent", "invert", "image"])
def test_layout_template_roundtrip(layout_name):
    # Sanity-check the embedded templates parse to well-formed layouts
    data = social_module._LAYOUTS[layout_name]
    layout = social_module.Layout(config_file_path=f"{layout_name}.yml")
    layout.load_dict(social_module.yaml.load(data, social_module.SafeLoader) or {})
    errors, warnings = layout.validate()
    assert errors == []


def _find_font() -> Path | None:
    for pattern in ("/usr/share/fonts/**/*.ttf", "/usr/share/fonts/**/*.otf"):
        for font in sorted(Path("/").glob(pattern.lstrip("/"))):
            return font
    return None


class TestRendering:
    def test_generate_handles_locale_suffixed_pages(self, tmp_path, monkeypatch):
        # Pages created by the i18n plugin (e.g. 'index.zh.html') must not
        # trip the ".png" assertion in _path_to_file - the card path is
        # computed by replacing the file extension instead
        monkeypatch.setattr(social_module, "import_errors", {"ModuleNotFoundError('no PIL')"})

        from types import SimpleNamespace

        plugin = SocialPlugin()
        plugin.load_config({"cache_dir": str(tmp_path / ".cache")})
        cfg = _load_config(tmp_path)
        plugin.on_config(cfg)

        page = SimpleNamespace(
            title="首页",
            is_homepage=False,
            is_index=False,
            meta={},
            file=SimpleNamespace(
                src_uri="index.zh.md",
                src_path="index.zh.md",
                dest_uri="index.zh.html",
            ),
        )

        plugin.on_startup(command="build", dirty=True)
        try:
            # Missing deps: must raise PluginError (gracefully loggable),
            # not AssertionError
            with pytest.raises(social_module.PluginError, match="docsforge\\[social\\]"):
                plugin._generate("default", page, cfg)
        finally:
            plugin.on_shutdown()

    def test_generate_writes_png(self, tmp_path, monkeypatch):
        pytest.importorskip("PIL")
        pytest.importorskip("cairosvg")
        font = _find_font()
        if font is None:
            pytest.skip("no system font available for rendering")

        from types import SimpleNamespace

        plugin = SocialPlugin()
        plugin.load_config({
            "cache_dir": str(tmp_path / ".cache"),
            "cards_layout_options": {"font_family": "Go"},
        })
        cfg = _load_config(tmp_path)
        plugin.on_config(cfg)

        # Avoid downloading fonts from Google Fonts - use a local one instead
        def fake_resolve_font(family, style, variant=""):
            return str(font)

        monkeypatch.setattr(plugin, "_resolve_font", fake_resolve_font)

        page = SimpleNamespace(
            title="Test Page",
            is_homepage=False,
            is_index=True,
            meta={},
            file=SimpleNamespace(
                src_uri="index.md",
                src_path="index.md",
                dest_uri="index.html",
            ),
        )

        # on_page_markdown + on_post_page emulate the build pipeline
        plugin.on_startup(command="build", dirty=True)
        try:
            plugin.on_page_markdown("# Title", page=page, config=cfg, files=None)
            out = plugin.on_post_page("<html><head></head><body></body></html>",
                                      page=page, config=cfg)
        finally:
            plugin.on_shutdown()

        assert out is not None
        assert "og:image" in out
        png = tmp_path / ".cache" / "assets" / "images" / "social" / "index.png"
        assert png.is_file()
        assert png.read_bytes().startswith(b"\x89PNG")
