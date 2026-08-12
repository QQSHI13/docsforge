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


class TestPdfCache:
    """Content-hash caching for PDF export (mirrors the site build cache)."""

    def test_fresh_when_versions_match(self, tmp_path: Path):
        from docsforge.pdf import PdfCache
        cache = PdfCache(tmp_path)
        assert cache.is_fresh("12.5.0") is False  # empty cache
        cache.save("12.5.0", {"blog/index.pdf": "h1"})
        assert cache.is_fresh("12.5.0") is True
        assert cache.is_fresh("12.6.0") is False  # pkg bump
        assert cache.is_fresh(None) is False

    def test_should_render_by_page_hash(self, tmp_path: Path):
        from docsforge.pdf import PdfCache
        cache = PdfCache(tmp_path)
        cache.save("12.5.0", {"blog/index.pdf": "h1"})
        assert cache.should_render("blog/index.pdf", "h1") is False  # up to date
        assert cache.should_render("blog/index.pdf", "h2") is True   # changed
        assert cache.should_render("other.pdf", "h1") is True        # new page

    def test_cache_persists_across_instances(self, tmp_path: Path):
        from docsforge.pdf import PdfCache
        PdfCache(tmp_path).save("12.5.0", {"a.pdf": "h"})
        reloaded = PdfCache(tmp_path)
        assert reloaded.is_fresh("12.5.0") is True
        assert reloaded.should_render("a.pdf", "h") is False

    def test_corrupted_cache_recovers(self, tmp_path: Path):
        from docsforge.pdf import PdfCache
        cache_file = tmp_path / ".docsforge" / "cache" / "pdf.json"
        cache_file.parent.mkdir(parents=True)
        cache_file.write_text("{not json")
        cache = PdfCache(tmp_path)
        assert cache.data == {}
        assert cache.is_fresh("12.5.0") is False

    def test_incremental_skips_only_unchanged_pages(self, tmp_path: Path):
        """A single changed page must not force re-rendering of the others."""
        from docsforge.pdf import PdfCache
        cache = PdfCache(tmp_path)
        cache.save("12.5.0", {"a.pdf": "h1", "b.pdf": "h2"})
        assert cache.should_render("a.pdf", "h1") is False
        assert cache.should_render("b.pdf", "h2") is False
        # one page changes -> only that one needs rendering
        assert cache.should_render("a.pdf", "h1-changed") is True
        assert cache.should_render("b.pdf", "h2") is False
