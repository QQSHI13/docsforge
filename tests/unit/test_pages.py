"""Unit tests for docsforge.pages."""
from __future__ import annotations

import textwrap
from collections import OrderedDict
from unittest import mock
from xml.etree import ElementTree as etree

import pytest

from docsforge.config_base import load_config
from docsforge.files import File, Files
from docsforge.pages import Page, _RelativePathTreeprocessor


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

    def test_missing_href_or_src_is_skipped(self, page_config):
        proc = self._processor(page_config)
        root = etree.Element("div")
        a_without_href = etree.SubElement(root, "a")
        img_without_src = etree.SubElement(root, "img")
        a_with_href = etree.SubElement(root, "a")
        a_with_href.set("href", "https://example.com")

        result = proc.run(root)

        assert result is root
        assert a_without_href.get("href") is None
        assert img_without_src.get("src") is None
        assert a_with_href.get("href") == "https://example.com"


class TestExtractTitle:
    def test_breaks_only_after_h1(self, page_config):
        import markdown

        from docsforge.pages import _ExtractTitleTreeprocessor

        md = markdown.Markdown()
        ext = _ExtractTitleTreeprocessor()
        ext._register(md)
        md.convert("<p>intro</p>\n# Title\n# Another\n")
        assert ext.title == "Title"


class TestSetEditUrl:
    def test_edit_uri_must_end_with_slash(self, page_config):
        file = File(
            "page.md", page_config.docs_dir, page_config.site_dir, page_config.use_directory_urls
        )
        page = Page(None, file, page_config)
        with pytest.raises(ValueError, match="edit_uri must be a string ending with '/'"):
            page._set_edit_url(repo_url="https://example.com/repo", edit_uri="edit")

    def test_valid_edit_uri_is_accepted(self, page_config):
        file = File(
            "page.md", page_config.docs_dir, page_config.site_dir, page_config.use_directory_urls
        )
        page = Page(None, file, page_config)
        page._set_edit_url(repo_url="https://example.com/repo", edit_uri="edit/")
        assert page.edit_url == "https://example.com/repo/edit/page.md"


class TestPageInit:
    def test_calls_super_init(self, page_config):
        from docsforge.pages import StructureItem

        file = File(
            "page.md", page_config.docs_dir, page_config.site_dir, page_config.use_directory_urls
        )
        with mock.patch.object(StructureItem, "__init__") as mock_super_init:
            Page(None, file, page_config)
        mock_super_init.assert_called_once_with()


class TestMarkdownCache:
    def test_cache_is_bounded(self):
        from docsforge.pages import _MAX_MD_CACHE_SIZE, _get_markdown_instance, _md_thread_local

        _md_thread_local.instances = OrderedDict()
        for i in range(_MAX_MD_CACHE_SIZE + 5):
            _get_markdown_instance([], {f"cfg_{i}": {}})

        assert len(_md_thread_local.instances) <= _MAX_MD_CACHE_SIZE

    def test_cache_evicts_least_recently_used(self):
        from docsforge.pages import _MAX_MD_CACHE_SIZE, _get_markdown_instance, _md_thread_local

        _md_thread_local.instances = OrderedDict()
        mds = [
            _get_markdown_instance([], {f"cfg_{i}": {}})
            for i in range(_MAX_MD_CACHE_SIZE)
        ]

        # Touch the first entry so it becomes the most recently used.
        _get_markdown_instance([], {"cfg_0": {}})

        # Adding a new entry should evict the second entry, not the first.
        _get_markdown_instance([], {"cfg_new": {}})

        assert mds[0] in _md_thread_local.instances.values()
        assert mds[1] not in _md_thread_local.instances.values()


class TestRawHTMLAnchors:
    def test_code_spans_are_skipped(self):
        from docsforge.pages import _RawHTMLPreprocessor

        ext = _RawHTMLPreprocessor()
        lines = [
            '<a name="real"></a>',
            '`<a name="fake1"></a>`',
            'Text with `<div id="fake2"></div>` inline code.',
            '<div id="also-real"></div>',
        ]
        ext.run(lines)

        assert "real" in ext.present_anchor_ids
        assert "also-real" in ext.present_anchor_ids
        assert "fake1" not in ext.present_anchor_ids
        assert "fake2" not in ext.present_anchor_ids

    def test_multi_backtick_code_spans_are_skipped(self):
        from docsforge.pages import _RawHTMLPreprocessor

        ext = _RawHTMLPreprocessor()
        lines = [
            '``<a name="fake3"></a>``',
            '```<a name="fake4"></a>```',
            "``nested `backticks` inside``",
        ]
        ext.run(lines)

        assert "fake3" not in ext.present_anchor_ids
        assert "fake4" not in ext.present_anchor_ids

    def test_real_raw_html_anchors_are_still_extracted(self):
        from docsforge.pages import _RawHTMLPreprocessor

        ext = _RawHTMLPreprocessor()
        lines = ['<a name="anchor"></a>', '<div id="section"></div>']
        ext.run(lines)

        assert "anchor" in ext.present_anchor_ids
        assert "section" in ext.present_anchor_ids
