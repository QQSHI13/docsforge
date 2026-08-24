"""Unit tests for cli_core: config-file discovery, optional-dep checks, routing."""
from __future__ import annotations

from docsforge import cli_core


class TestFindConfigFile:
    def test_prefers_yml_over_yaml(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "docsforge.yaml").write_text("site_name: Y\n")
        (tmp_path / "docsforge.yml").write_text("site_name: Y\n")
        found = cli_core.find_config_file()
        assert found is not None
        assert found.name == "docsforge.yml"

    def test_fallback_to_yaml(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "docsforge.yaml").write_text("site_name: Y\n")
        found = cli_core.find_config_file()
        assert found is not None
        assert found.name == "docsforge.yaml"

    def test_returns_none_when_missing(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert cli_core.find_config_file() is None

    def test_explicit_path(self, tmp_path):
        cfg = tmp_path / "custom.yml"
        cfg.write_text("site_name: C\n")
        found = cli_core.find_config_file(str(cfg))
        assert found == cfg


class TestDetectEnvironment:
    def test_no_config(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        env = cli_core.detect_environment()
        assert env["config_found"] is False

    def test_with_config_and_docs(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "index.md").write_text("# H\n")
        (tmp_path / "docsforge.yml").write_text("site_name: T\ndocs_dir: docs\n")
        env = cli_core.detect_environment()
        assert env["config_found"] is True
        assert env["docs_dir_exists"] is True
        assert env["has_index"] is True


class TestCheckOptionalDeps:
    def test_jieba_warning_when_chinese_search_without_jieba(self, tmp_path, caplog):
        cfg = tmp_path / "docsforge.yml"
        cfg.write_text(
            "site_name: T\n"
            "plugins:\n"
            "  - material/search:\n"
            "      jieba_dict: dict.txt\n"
        )
        import logging
        with caplog.at_level(logging.WARNING, logger="docsforge"):
            # Force jieba import to fail by hiding it
            import builtins
            real_import = builtins.__import__

            def fake_import(name, *a, **k):
                if name == "jieba":
                    raise ImportError("simulated")
                return real_import(name, *a, **k)

            builtins.__import__ = fake_import
            try:
                cli_core._check_optional_deps(str(cfg))
            finally:
                builtins.__import__ = real_import
        assert any("docsforge[chinese]" in m for m in caplog.messages)

    def test_silent_on_missing_config(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # Must not raise even though no config exists
        cli_core._check_optional_deps()

    def test_silent_on_bad_yaml(self, tmp_path, caplog):
        cfg = tmp_path / "docsforge.yml"
        cfg.write_text(": : not valid yaml : :\n")
        import logging
        with caplog.at_level(logging.WARNING, logger="docsforge"):
            cli_core._check_optional_deps(str(cfg))
        # best-effort: no crash, no stray warnings about deps
        assert not any("docsforge[" in m for m in caplog.messages)


class TestAutoRouter:
    def test_no_config_not_tty_returns_error(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        assert cli_core.AutoRouter.route() == 1


class TestServeStrictFlag:
    """The --strict flag on `docsforge serve` must propagate through
    DevServer.serve -> serve_module.serve -> load_config(strict=True)."""

    def test_strict_propagates_to_load_config(self, tmp_path, monkeypatch):
        from docsforge.config_base import load_config

        monkeypatch.chdir(tmp_path)
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "index.md").write_text("# h\n")
        (tmp_path / "docsforge.yml").write_text(
            "site_name: T\n"
        "theme: {name: material, palette: [{scheme: default, primary: teal, accent: teal}]}\n"
        "privacy: false\n"
        )
        # load_config accepts strict as a kwarg (the path serve takes)
        cfg = load_config(strict=True)
        assert cfg.strict is True
        cfg2 = load_config(strict=False)
        assert cfg2.strict is False

    def test_devserver_passes_strict_to_serve_module(self, mocker):
        """DevServer.serve(strict=...) must forward strict to serve_module.serve."""
        mocked = mocker.patch("docsforge.serve.serve")
        cli_core.DevServer.serve(strict=True, open_in_browser=False)
        assert mocked.called
        assert mocked.call_args.kwargs.get("strict") is True

    def test_devserver_omits_strict_when_false(self, mocker):
        mocked = mocker.patch("docsforge.serve.serve")
        cli_core.DevServer.serve(strict=False, open_in_browser=False)
        # strict=False is still forwarded; load_config drops None but keeps False
        assert mocked.call_args.kwargs.get("strict") is False


class TestValidatorCheckFullValidation:
    def test_preflight_check_passes_missing_third_party_plugin(self, tmp_path, monkeypatch):
        """The lightweight preflight check used by build/serve must not fail
        on a missing third-party plugin; the real load_config validation runs
        afterwards."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "index.md").write_text("# h\n")
        (tmp_path / "docsforge.yml").write_text(
            "site_name: T\n"
            "plugins:\n"
            "  - plugins.does_not_exist\n"
        )
        # Lightweight check returns 0 so build/serve can proceed to full validation.
        assert cli_core.Validator.check(full_validation=False) == 0

    def test_full_check_fails_missing_third_party_plugin(self, tmp_path, monkeypatch, capsys):
        """docsforge check (full_validation=True) must surface the same
        configuration error that build/serve surface via load_config."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "index.md").write_text("# h\n")
        (tmp_path / "docsforge.yml").write_text(
            "site_name: T\n"
            "plugins:\n"
            "  - plugins.does_not_exist\n"
        )
        assert cli_core.Validator.check(full_validation=True) == 1
        captured = capsys.readouterr()
        assert "CONFIGURATION ERROR" in captured.out
        assert "plugins.does_not_exist" in captured.out
