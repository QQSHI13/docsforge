"""Unit tests for config loading and validation (docsforge.config_base / config_defaults)."""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

from docsforge.config_base import Config, ValidationError, load_config
from docsforge.config_options import Hooks, IpAddress, Type


def _write_config(root: Path, body: str) -> Path:
    # DocsDir validator requires docs_dir to exist on disk.
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs" / "index.md").write_text("# Home\n")
    cfg = root / "docsforge.yml"
    cfg.write_text(textwrap.dedent(body).strip() + "\n")
    return cfg


class TestLoadConfig:
    def test_minimal_config(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path, """
            site_name: Minimal
        """)
        cfg = load_config()
        assert cfg["site_name"] == "Minimal"
        assert cfg["docs_dir"].endswith("docs")
        assert cfg["site_dir"].endswith("site")
        assert cfg["use_directory_urls"] is True

    def test_explicit_config_path(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cfg_path = _write_config(tmp_path, """
            site_name: Explicit
        """)
        cfg = load_config(config_file=str(cfg_path))
        assert cfg["site_name"] == "Explicit"

    def test_kwargs_override_defaults(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path, "site_name: T\n")
        cfg = load_config(site_dir="out")
        assert cfg["site_dir"].endswith("out")

    def test_none_kwargs_are_dropped(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path, "site_name: T\nsite_dir: site\n")
        # passing site_dir=None must NOT override the file's value
        cfg = load_config(site_dir=None)
        assert cfg["site_dir"].endswith("site")


class TestDefaults:
    def test_markdown_extensions_default_has_31(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path, "site_name: T\n")
        cfg = load_config()
        exts = cfg["markdown_extensions"]
        # The advertised zero-config default
        assert len(exts) >= 31
        assert "pymdownx.superfences" in exts
        assert "pymdownx.snippets" in exts
        assert "admonition" in exts

    def test_builtin_extensions_present(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path, "site_name: T\n")
        cfg = load_config()
        for b in ("toc", "tables", "fenced_code"):
            assert b in cfg["markdown_extensions"]

    def test_privacy_default_true(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path, "site_name: T\n")
        assert load_config()["privacy"] is True

    def test_dev_addr_default(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path, "site_name: T\n")
        host, port = load_config()["dev_addr"]
        assert host == "127.0.0.1"
        assert port == 8000


class TestValidation:
    def test_invalid_yaml_raises(self, tmp_path, monkeypatch):
        from docsforge.exceptions import DocsForgeException

        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path, "site_name: : : bad\n")
        with pytest.raises(DocsForgeException):
            load_config()

    def test_missing_site_name_errors(self, tmp_path, monkeypatch):
        from docsforge.exceptions import DocsForgeException

        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path, "docs_dir: docs\n")
        with pytest.raises(DocsForgeException):
            load_config()

    def test_config_file_path_cannot_be_set(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path, "site_name: T\nconfig_file_path: evil\n")
        with pytest.raises(Exception):
            load_config()


class TestEnvTag:
    def test_env_tag_substitution(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("MY_DESC", "from env")
        _write_config(tmp_path, """
            site_name: T
            site_description: !ENV MY_DESC
        """)
        cfg = load_config()
        assert cfg["site_description"] == "from env"

    def test_env_tag_default_when_unset(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("NOPE_VAR", raising=False)
        _write_config(tmp_path, """
            site_name: T
            site_description: !ENV [NOPE_VAR, fallback]
        """)
        cfg = load_config()
        assert cfg["site_description"] == "fallback"


class TestIpAddress:
    def test_valid_port(self):
        value = IpAddress(default="127.0.0.1:8000").run_validation("127.0.0.1:8000")
        assert value.port == 8000

    def test_port_too_large_rejected(self):
        with pytest.raises(ValidationError):
            IpAddress().run_validation("127.0.0.1:70000")

    def test_negative_port_rejected(self):
        with pytest.raises(ValidationError):
            IpAddress().run_validation("127.0.0.1:-1")


class TestOptionallyRequired:
    def test_explicit_required_false_is_respected(self):
        class _Schema(Config):
            optional = Type(str, required=False)
            required = Type(str)

        cfg = _Schema()
        failed, _ = cfg.validate()
        assert len(failed) == 1
        assert failed[0][0] == "required"


class TestValidate:
    def test_collects_all_validation_errors(self):
        class _Schema(Config):
            one = Type(str)
            two = Type(str)

        cfg = _Schema()
        failed, _ = cfg.validate()
        assert len(failed) == 2
        assert {key for key, _ in failed} == {"one", "two"}


class TestHooks:
    def test_hook_name_colliding_with_stdlib_does_not_clobber_sys_modules(self, tmp_path):
        # The raw user-supplied hook name must never become a sys.modules key,
        # otherwise a hook named e.g. 'os' would overwrite the stdlib module.
        hook_file = tmp_path / "hook_script.py"
        hook_file.write_text("x = 1\n")
        real_os = sys.modules["os"]
        module = Hooks("plugins")._load_hook("os", str(hook_file))
        assert module.x == 1
        assert sys.modules["os"] is real_os

    def test_hook_is_not_registered_under_raw_name(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "myhook.py").write_text(
            "def on_page_markdown(markdown, **kwargs):\n    return markdown\n"
        )
        _write_config(tmp_path, """
            site_name: T
            hooks:
              - myhook.py
        """)
        cfg = load_config()
        # The hook still becomes a plugin under its user-facing name...
        assert "myhook.py" in cfg["plugins"]
        # ...but the module itself gets a safe internal name, not the raw path.
        assert cfg["plugins"]["myhook.py"].__name__.startswith("_docsforge_hook_")
        assert "myhook.py" not in sys.modules
