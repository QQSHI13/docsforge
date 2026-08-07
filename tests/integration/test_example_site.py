"""Build the official example site (examples/site/docsforge-demo).

The example must never rot: this test runs a real build and asserts the key
outputs exist. The TikZ/latex steps warn (texlive is not required) and the
privacy plugin fetches external assets over the network — both are tolerated
by the build.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from docsforge.build import build
from docsforge.config_base import load_config

pytestmark = pytest.mark.slow

DEMO_DIR = (
    Path(__file__).resolve().parents[2] / "examples" / "site" / "docsforge-demo"
)


def test_example_site_builds(tmp_path, monkeypatch):
    config_file = DEMO_DIR / "docsforge.yml"
    if not config_file.exists():
        pytest.skip("example site not present")

    monkeypatch.chdir(DEMO_DIR)
    cfg = load_config(config_file=str(config_file))
    cfg.plugins.on_startup(command="build", dirty=True)
    try:
        build(cfg, dirty=True)
    finally:
        cfg.plugins.on_shutdown()

    site = DEMO_DIR / "site"
    assert (site / "index.html").is_file()
    assert (site / "blog" / "index.html").is_file()
    assert (site / "tags" / "index.html").is_file()
    assert (site / "sw.js").is_file()
    assert (site / "cache-manifest.json").is_file()
    # The custom_dir override (overrides/main.html announce banner) rendered.
    assert "the official example site" in (site / "index.html").read_text(
        encoding="utf-8", errors="ignore"
    )
