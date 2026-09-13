"""Unit tests for docsforge.localization translation loading."""
from __future__ import annotations

from docsforge.localization import _get_merged_translations


class TestMergedTranslations:
    """Regression: a missing locales dir must not raise IOError (babel-version dependent)."""

    def test_missing_locales_dir_returns_none(self, tmp_path):
        from babel.core import Locale

        theme_dir = tmp_path / "theme"
        theme_dir.mkdir()
        result = _get_merged_translations([str(theme_dir)], "locales", Locale.parse("de"))
        assert result is None

    def test_missing_dir_among_multiple_dirs_ignored(self, tmp_path):
        from babel.core import Locale

        existing = tmp_path / "exists"
        existing.mkdir()
        result = _get_merged_translations(
            [str(existing), str(tmp_path / "missing")], "locales", Locale.parse("de")
        )
        assert result is None
