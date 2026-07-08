"""Unit tests for docsforge.pages."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from docsforge.config_base import load_config
from docsforge.files import File, Files
from docsforge.pages import Page, _RelativePathTreeprocessor


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
    return load_config(config_file=str(cfg_path))


@pytest.fixture()
def page_config(tmp_path):
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


class TestRelativePathTreeprocessor:
    def _processor(self, config, src_uri="page.md", files=None):
        file = File(src_uri, config.docs_dir, config.site_dir, config.use_directory_urls)
        return _RelativePathTreeprocessor(file, files or Files([]), config)

    def test_whitelisted_external_schemes_are_preserved(self, page_config):
        proc = self._processor(page_config)
        assert proc.path_to_url("https://example.com") == "https://example.com"
        assert proc.path_to_url("mailto:a@b.com") == "mailto:a@b.com"
        assert proc.path_to_url("tel:+123") == "tel:+123"

    def test_non_whitelisted_scheme_is_escaped(self, page_config):
        proc = self._processor(page_config)
        assert proc.path_to_url("javascript:alert(1)") == "javascript%3Aalert(1)"

    def test_relative_link_suggestion_uses_correct_argument_order(self, page_config, tmp_path, caplog):
        import logging

        # Create a target file in the same directory as the source.
        target = File("dir/target.md", page_config.docs_dir, page_config.site_dir, page_config.use_directory_urls)
        source = File("dir/page.md", page_config.docs_dir, page_config.site_dir, page_config.use_directory_urls)
        real_files = Files([source, target])

        # Make the .md-suffix variant resolve while the primary link does not,
        # forcing the "did you mean" suggestion path.
        class _Files:
            def get_file_from_path(self, path):
                if path == "dir/target.md":
                    return target
                return None

        proc = _RelativePathTreeprocessor(source, _Files(), page_config)
        with caplog.at_level(logging.INFO):
            result = proc.path_to_url("target")
        assert result == "target"  # not found, left as-is
        # The suggestion must be relative from source (dir/page.md) to target
        # (dir/target.md), not the reverse direction.
        assert "Did you mean 'target.md'?" in caplog.text


class TestExtractTitle:
    def test_breaks_only_after_h1(self, page_config):
        from docsforge.pages import _ExtractTitleTreeprocessor
        import markdown

        md = markdown.Markdown()
        ext = _ExtractTitleTreeprocessor()
        ext._register(md)
        md.convert("<p>intro</p>\n# Title\n# Another\n")
        assert ext.title == "Title"
