"""Link/anchor validation must surface on every build, not only the first.

A broken anchor in an *unchanged* linking page used to go unreported on
incremental builds because validation data only existed for pages that were
re-rendered. The build now persists per-page link/anchor data and re-runs
the validation pass over all pages on every build.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

import pytest

from docsforge.build import build
from docsforge.config_base import load_config

pytestmark = pytest.mark.slow


def _build_once(project: Path, caplog) -> list[str]:
    cfg = load_config(config_file=str(project / "docsforge.yml"))
    cfg.plugins.on_startup(command="build", dirty=True)
    with caplog.at_level(logging.WARNING, logger="docsforge"):
        try:
            build(cfg, dirty=True)
        finally:
            cfg.plugins.on_shutdown()
    return [
        r.getMessage()
        for r in caplog.records
        if "does not contain an anchor" in r.getMessage()
    ]


def test_anchor_warning_surfaces_on_incremental_builds(tmp_path, caplog):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.md").write_text("# A\n\n[Section](b.md#section)\n")
    (docs / "b.md").write_text("# B\n\n## Section\n")
    (tmp_path / "docsforge.yml").write_text(
        "site_name: T\nsite_url: https://example.com/\n"
        "theme:\n  name: material\n  font: false\n"
        "validation:\n  links:\n    anchors: warn\n"
    )

    # First build: everything renders, no warnings.
    assert _build_once(tmp_path, caplog) == []

    # Nothing changed: still no warnings.
    assert _build_once(tmp_path, caplog) == []

    # Remove the anchor from b.md. a.md (the linking page) is unchanged and
    # not re-rendered — but the warning must still surface.
    (docs / "b.md").write_text("# B\n")
    warnings = _build_once(tmp_path, caplog)
    assert any("b.md#section" in w and "does not contain an anchor" in w for w in warnings)

    # And again on a no-op rebuild: validation re-runs every build.
    warnings = _build_once(tmp_path, caplog)
    assert any("b.md#section" in w and "does not contain an anchor" in w for w in warnings)
