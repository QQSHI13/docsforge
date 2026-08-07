"""Unit tests for docsforge.pdf helpers."""
from __future__ import annotations

from pathlib import Path

import pytest

from docsforge.pdf import _is_within, build_pdf


class TestIsWithin:
    def test_path_inside_base(self, tmp_path: Path):
        base = tmp_path / "site"
        local = base / "assets" / "style.css"
        local.parent.mkdir(parents=True)
        local.write_text("body {}")
        assert _is_within(local, base) is True

    def test_path_outside_base(self, tmp_path: Path):
        base = tmp_path / "site"
        outside = tmp_path / "secret.txt"
        outside.write_text("secret")
        assert _is_within(outside, base) is False


class TestBuildPdf:
    def test_build_pdf_fails_without_site_dir(self, tmp_path: Path):
        # No site built -> should return 1 without trying to render.
        docs = tmp_path / "docs"
        docs.mkdir()
        assert build_pdf(str(docs)) == 1
