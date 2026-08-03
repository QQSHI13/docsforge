"""Unit tests for docsforge.build."""
from __future__ import annotations

import json
import struct
import textwrap
import threading
import zlib
from pathlib import Path
from unittest.mock import Mock, patch

import jinja2
import pytest

from docsforge import build as build_mod
from docsforge.build import (
    _build_page,
    _default_page_lock,
    _finalize_build,
    _populate_changed_pages,
    _remove_orphaned_output,
    _write_outputs,
)
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


class TestPopulateChangedPagesErrors:
    def test_collects_all_populate_errors(self, tmp_path, monkeypatch):
        cfg = _load_config(tmp_path)
        monkeypatch.chdir(tmp_path)

        file_a = File("a.md", cfg.docs_dir, cfg.site_dir, cfg.use_directory_urls)
        file_b = File("b.md", cfg.docs_dir, cfg.site_dir, cfg.use_directory_urls)
        files = Files([file_a, file_b])
        Page(None, file_a, cfg)
        Page(None, file_b, cfg)

        def _bad_populate(*args, **kwargs):
            raise BuildError("boom")

        monkeypatch.setattr(build_mod, "_populate_page", _bad_populate)

        with pytest.raises(ExceptionGroup, match="Errors populating pages") as exc_info:
            _populate_changed_pages(cfg, files, Mock(), [file_a, file_b], lambda level: True, None)
        assert len(exc_info.value.exceptions) == 2


class TestFinalizeBuildOrder:
    def test_pwa_generation_runs_after_post_build(self, tmp_path, monkeypatch):
        cfg = _load_config(tmp_path)
        monkeypatch.chdir(tmp_path)

        calls = []
        cfg.plugins.on_post_build = Mock(side_effect=lambda **kw: calls.append("on_post_build"))

        planner = Mock()
        planner.save = Mock()

        warning_counter = Mock()
        warning_counter.get_counts.return_value = None

        with patch.object(build_mod, "_generate_pwa_manifest_and_precache", lambda *a, **k: calls.append("pwa")):
            _finalize_build(
                cfg,
                Files([]),
                Mock(homepage=None),
                planner,
                warning_counter,
                built_any=True,
                sources_changed=False,
                config_path=Path("docsforge.yml"),
                theme_sig="",
                start=0.0,
            )

        assert calls == ["on_post_build", "pwa"]


class TestFinalizeBuildOptimizesAssets:
    """Asset optimization must run even on incremental builds with no changes."""

    def test_optimize_assets_runs_when_nothing_changed(self, tmp_path, monkeypatch):
        cfg = _load_config(tmp_path)
        monkeypatch.chdir(tmp_path)

        planner = Mock()
        planner.save = Mock()

        warning_counter = Mock()
        warning_counter.get_counts.return_value = None

        optimize_calls = []

        def fake_optimize(site_dir, **kwargs):
            optimize_calls.append((site_dir, kwargs))

        # Avoid running real plugin post_build handlers and PWA generation;
        # they require a full build state this test does not set up.
        cfg.plugins.on_post_build = Mock()

        with patch.object(build_mod, "optimize_assets", fake_optimize):
            with patch.object(build_mod, "_generate_pwa_manifest_and_precache", Mock()):
                _finalize_build(
                    cfg,
                    Files([]),
                    Mock(homepage=None),
                    planner,
                    warning_counter,
                    built_any=False,
                    sources_changed=False,
                    config_path=Path("docsforge.yml"),
                    theme_sig="",
                    start=0.0,
                )

        assert optimize_calls == [
            (
                cfg.site_dir,
                {
                    "built_any": False,
                    "sources_changed": False,
                    "cache_dir": planner.cache.cache_dir,
                },
            )
        ]


class TestInstantNavigationBundleIgnoresI18nAlternates:
    """The vendored instant-navigation bundle must not treat i18n hreflang
    alternates as version bases (which causes subdirectory sitemap.xml 404s)."""

    def test_bundle_selector_excludes_hreflang_alternates(self):
        from docsforge import utils

        theme_dir = utils.get_theme_dir('material')
        bundle_path = Path(theme_dir) / 'assets' / 'javascripts' / 'bundle.min.js'
        if not bundle_path.exists():
            pytest.skip('Vendored bundle not present')

        content = bundle_path.read_text(encoding='utf-8', errors='ignore')
        # The upstream selector would be M("link[rel=alternate]"); DocsForge
        # patches it to exclude hreflang alternates used by the i18n plugin.
        assert 'link[rel=alternate]:not([hreflang])' in content
        assert 'M("link[rel=alternate]")' not in content


class TestBuildPageLock:
    def test_default_lock_is_shared_module_singleton(self):
        # The fallback lock used when _page_lock is None must be shared across
        # calls, otherwise concurrent calls serialize on different locks.
        assert isinstance(_default_page_lock, type(threading.Lock()))
        # _build_page signature keeps _page_lock default as None for callers.
        assert _build_page.__defaults__[-1] is None


class TestWriteOutputsSuccessTracking:
    def test_returns_false_when_all_pages_fail(self, tmp_path, monkeypatch):
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

        result = _write_outputs(cfg, files, nav, env, planner, [file], lambda level: True)
        assert result is False


class TestRemoveOrphanedOutput:
    def test_logs_warning_on_oserror(self, tmp_path, caplog):
        missing = tmp_path / "does_not_exist.html"
        with caplog.at_level("WARNING", logger="docsforge.build"):
            _remove_orphaned_output(missing)
        assert "Could not remove orphaned output" in caplog.text


class TestBuildExtraTemplateUsesEnv:
    """Extra templates must be compiled against the theme Jinja environment."""

    def test_renders_with_theme_env_globals(self, tmp_path, monkeypatch):
        from docsforge.build import _build_extra_template

        cfg = _load_config(tmp_path)
        monkeypatch.chdir(tmp_path)

        env = jinja2.Environment()
        env.globals['custom_global'] = 'rendered-from-env'

        extra_file = File(
            'extra.html',
            src_dir=None,
            dest_dir=cfg.site_dir,
            use_directory_urls=cfg.use_directory_urls,
        )
        extra_file.content_string = '<span>{{ custom_global }}</span>'
        files = Files([extra_file])

        cfg.plugins = Mock()
        cfg.plugins.on_pre_template = lambda template, **kw: template
        cfg.plugins.on_template_context = lambda context, **kw: context
        cfg.plugins.on_post_template = lambda output, **kw: output

        _build_extra_template('extra.html', env, files, cfg, Mock())

        dest_path = Path(extra_file.abs_dest_path)
        assert dest_path.is_file()
        rendered = dest_path.read_text()
        assert '<span>rendered-from-env</span>' in rendered


class TestPwaManifestIcons:
    """Manifest icon metadata must be read from the actual image files."""

    @staticmethod
    def _make_png(width: int, height: int) -> bytes:
        signature = b'\x89PNG\r\n\x1a\n'

        def chunk(chunk_type: bytes, data: bytes) -> bytes:
            chunk_data = struct.pack('>I', len(data)) + chunk_type + data
            crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
            return chunk_data + struct.pack('>I', crc)

        ihdr = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
        # One filter byte plus one RGBA pixel per row.
        raw = b''.join(b'\x00' + b'\x00\x00\x00' * width for _ in range(height))
        idat = zlib.compress(raw)
        return signature + chunk(b'IHDR', ihdr) + chunk(b'IDAT', idat) + chunk(b'IEND', b'')

    def test_detects_size_and_mime_for_favicon_and_logo(self, tmp_path, monkeypatch):
        from docsforge.build import _generate_pwa_manifest_and_precache

        docs = tmp_path / "docs"
        docs.mkdir()
        site = tmp_path / "site"
        site.mkdir()

        (docs / "favicon.png").write_bytes(self._make_png(48, 48))
        (docs / "logo.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 64"><rect/></svg>'
        )

        class FakeTheme:
            static_templates = []

            def get(self, key: str, default=None):
                return {'favicon': 'favicon.png', 'logo': 'logo.svg'}.get(key, default)

        class FakeConfig:
            site_dir = str(site)
            docs_dir = str(docs)
            site_name = "Test Site"
            site_description = "Test description"
            site_url = None
            config_file_path = ''
            extra = {}
            theme = FakeTheme()

        with patch.object(build_mod, '_generate_cache_manifest'):
            _generate_pwa_manifest_and_precache(FakeConfig(), Files([]), Mock(homepage=None), None)

        manifest = json.loads((site / "manifest.json").read_text())
        icons = {icon['src']: icon for icon in manifest['icons']}

        assert icons['favicon.png']['sizes'] == '48x48'
        assert icons['favicon.png']['type'] == 'image/png'
        assert icons['logo.svg']['sizes'] == '128x64'
        assert icons['logo.svg']['type'] == 'image/svg+xml'


class TestPrepareBuildMdxConfigs:
    """Mermaid fence injection must not mutate the original mdx_configs dict."""

    def test_works_on_deep_copy_of_mdx_configs(self, tmp_path, monkeypatch):
        from docsforge.build import _prepare_build

        cfg = _load_config(tmp_path)
        original = {
            'pymdownx.superfences': {
                'custom_fences': [{'name': 'existing'}],
            },
        }
        cfg['mdx_configs'] = original

        planner = Mock()
        planner.should_full_rebuild.return_value = False
        planner.invalidate = Mock()

        cfg.plugins = Mock()
        cfg.plugins.on_config.return_value = cfg
        cfg.plugins.on_pre_build = Mock()

        config_path = tmp_path / "docsforge.yml"
        config, _, _ = _prepare_build(cfg, planner, config_path, "theme_sig", None)

        # Original object must be untouched.
        assert original == {
            'pymdownx.superfences': {
                'custom_fences': [{'name': 'existing'}],
            },
        }
        # A new copy should have been installed on the config.
        assert config['mdx_configs'] is not original
        fences = config['mdx_configs']['pymdownx.superfences']['custom_fences']
        assert any(fence.get('name') == 'mermaid' for fence in fences)
