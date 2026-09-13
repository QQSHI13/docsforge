"""Unit tests for docsforge.meta front-matter parsing."""
from __future__ import annotations

import logging

from docsforge.meta import get_data


class TestYamlFrontMatter:
    def test_parses_with_trailing_newline(self):
        doc, data = get_data("---\ntitle: Hello\n---\n\nBody text")
        assert data == {"title": "Hello"}
        assert doc == "Body text"

    def test_parses_at_eof_without_trailing_newline(self):
        # The closing --- at end-of-file (no trailing newline) must still
        # parse; the doc body after it is empty.
        doc, data = get_data("---\ntitle: Hello\n---")
        assert data == {"title": "Hello"}
        assert doc == ""

    def test_parses_eof_and_keeps_body(self):
        doc, data = get_data("---\ntitle: Hello\n---\nBody")
        assert data == {"title": "Hello"}
        assert doc == "Body"

    def test_yaml_parse_error_logs_warning(self, caplog):
        # A YAML body that fails to parse must not be silently swallowed.
        doc = "---\ntitle: [unclosed\n---\nBody"
        with caplog.at_level(logging.WARNING, logger="docsforge.meta"):
            get_data(doc)
        assert any("Failed to parse YAML" in rec.message for rec in caplog.records)

    def test_multimarkdown_fallback_still_works(self):
        doc, data = get_data("Title: Hello\n\nBody")
        assert data == {"title": "Hello"}
        assert doc == "Body"
