"""Unit tests for the meta plugin (docsforge.core.meta).

Meta files (*.meta.yml) merged into page metadata in level-order.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from docsforge.core.meta import MetaPlugin


def _make_plugin(tmp_path: Path) -> MetaPlugin:
    plugin = MetaPlugin()
    plugin.load_config({})
    return plugin


class TestMetaPlugin:
    def test_loads_yaml_meta_file(self, tmp_path):
        plugin = _make_plugin(tmp_path)
        meta_path = tmp_path / "docs" / ".meta.yml"
        meta_path.parent.mkdir()
        meta_path.write_text("author: QQ\n")
        # Simulate a files collection with one meta file
        from types import SimpleNamespace

        f = SimpleNamespace(
            src_uri=".meta.yml",
            src_path=".meta.yml",
            abs_src_path=str(meta_path),
        )
        plugin.on_files([f], config=SimpleNamespace(docs_dir=str(tmp_path / "docs")))
        assert any("author" in m for m in plugin.meta.values())

    def test_disabled_skips_processing(self, tmp_path):
        from types import SimpleNamespace

        plugin = MetaPlugin()
        plugin.load_config({"enabled": False})
        assert plugin.on_files([], config=SimpleNamespace(docs_dir=str(tmp_path))) is None

    def test_corrupt_meta_raises_plugin_error(self, tmp_path):
        from docsforge.exceptions import PluginError
        from types import SimpleNamespace

        meta_path = tmp_path / ".meta.yml"
        meta_path.write_text(": : not yaml : :\n")
        plugin = _make_plugin(tmp_path)
        f = SimpleNamespace(src_uri=".meta.yml", src_path=".meta.yml", abs_src_path=str(meta_path))
        with pytest.raises(PluginError):
            plugin.on_files([f], config=SimpleNamespace(docs_dir=str(tmp_path)))
