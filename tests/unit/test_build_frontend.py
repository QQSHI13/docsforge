"""Unit tests for build_frontend.py (dependency gate + tree sync)."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "build_frontend", ROOT / "build_frontend.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_frontend"] = module
    spec.loader.exec_module(module)
    return module


bf = _load_script()


class TestSatisfiesRange:
    def test_caret_major(self):
        assert bf.satisfies_range("1.44.0", "^1.44.0")
        assert bf.satisfies_range("1.45.0", "^1.44.0")
        assert not bf.satisfies_range("1.43.9", "^1.44.0")
        assert not bf.satisfies_range("2.0.0", "^1.44.0")

    def test_caret_zero_major(self):
        # ^0.x pins minor: ^0.2.2 := >=0.2.2 <0.3.0
        assert bf.satisfies_range("0.2.2", "^0.2.2")
        assert bf.satisfies_range("0.2.9", "^0.2.2")
        assert not bf.satisfies_range("0.3.0", "^0.2.2")
        assert not bf.satisfies_range("0.2.1", "^0.2.2")
        # ^0.0.x pins everything.
        assert bf.satisfies_range("0.0.3", "^0.0.3")
        assert not bf.satisfies_range("0.0.4", "^0.0.3")

    def test_tilde_and_gte_and_exact(self):
        assert bf.satisfies_range("1.103.5", "~1.103.1")
        assert not bf.satisfies_range("1.104.0", "~1.103.1")
        assert bf.satisfies_range("4.1.0", ">=4.0.2")
        assert not bf.satisfies_range("4.0.1", ">=4.0.2")
        assert bf.satisfies_range("7.0.2", "7.0.2")
        assert not bf.satisfies_range("7.0.3", "7.0.2")

    def test_unknown_operator_is_not_trusted(self):
        assert bf.satisfies_range("1.2.3", "^1.0.0") is True
        assert bf.satisfies_range("1.2.3", "<2.0.0") is False

    def test_garbage_versions_raise(self):
        with pytest.raises(ValueError):
            bf.satisfies_range("not-a-version", "^1.0.0")


class TestCheckDependencies:
    def _stage(self, tmp_path, specs, installed):
        (tmp_path / "package.json").write_text(json.dumps({
            "dependencies": specs,
            "devDependencies": {},
        }))
        nm = tmp_path / "node_modules"
        for name, version in installed.items():
            pkg = nm / name
            pkg.mkdir(parents=True)
            if version is not None:
                (pkg / "package.json").write_text(json.dumps({"version": version}))
        return nm

    def test_satisfied_passes(self, tmp_path, monkeypatch):
        nm = self._stage(tmp_path, {"a": "^1.4.0", "b": "~2.1.0"}, {"a": "1.9.0", "b": "2.1.7"})
        monkeypatch.setattr(bf, "ROOT", tmp_path)
        monkeypatch.setattr(bf, "NODE_MODULES", nm)
        bf.check_dependencies()  # must not raise

    def test_drifted_fails(self, tmp_path, monkeypatch):
        nm = self._stage(tmp_path, {"lucide-static": "^1.44.0"}, {"lucide-static": "1.33.0"})
        monkeypatch.setattr(bf, "ROOT", tmp_path)
        monkeypatch.setattr(bf, "NODE_MODULES", nm)
        with pytest.raises(SystemExit, match="pnpm install"):
            bf.check_dependencies()

    def test_missing_package_fails(self, tmp_path, monkeypatch):
        nm = self._stage(tmp_path, {"mermaid": "^12.0.0"}, {})
        monkeypatch.setattr(bf, "ROOT", tmp_path)
        monkeypatch.setattr(bf, "NODE_MODULES", nm)
        with pytest.raises(SystemExit, match="not installed"):
            bf.check_dependencies()


class TestSyncTree:
    def test_copies_prunes_and_skips(self, tmp_path):
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        (src / "sub").mkdir(parents=True)
        (src / "a.svg").write_text("<svg/>")
        (src / "sub" / "b.svg").write_text("<svg/>")
        (dst / "sub").mkdir(parents=True)
        (dst / "sub" / "b.svg").write_text("<svg/>")
        (dst / "stale.svg").write_text("<svg/>")

        bf._sync_tree(src, dst, "Test")
        assert (dst / "a.svg").is_file()
        assert (dst / "sub" / "b.svg").is_file()
        assert not (dst / "stale.svg").exists()

        # Second run: everything unchanged, nothing rewritten.
        before = {(p, p.stat().st_mtime_ns) for p in dst.rglob("*") if p.is_file()}
        bf._sync_tree(src, dst, "Test")
        after = {(p, p.stat().st_mtime_ns) for p in dst.rglob("*") if p.is_file()}
        assert before == after

    def test_updates_changed_files(self, tmp_path):
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        (src / "a.svg").write_text("<svg>1</svg>")
        bf._sync_tree(src, dst, "Test")
        (src / "a.svg").write_text("<svg>2 much longer content</svg>")
        bf._sync_tree(src, dst, "Test")
        assert (dst / "a.svg").read_text() == "<svg>2 much longer content</svg>"
