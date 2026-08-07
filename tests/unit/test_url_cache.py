"""Unit tests for docsforge.url_cache."""
from __future__ import annotations

import pytest

from docsforge.url_cache import _is_local_url, download_url


class TestIsLocalUrl:
    @pytest.mark.parametrize(
        "url",
        [
            "file:///etc/passwd",
            "http://localhost/foo",
            "http://127.0.0.1/foo",
            "http://192.168.1.1/foo",
            "http://10.0.0.1/foo",
            "http://example.local/foo",
        ],
    )
    def test_local_urls_are_rejected(self, url: str):
        assert _is_local_url(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            "http://example.com/foo",
            "https://example.com/foo",
        ],
    )
    def test_public_http_urls_are_allowed(self, url: str):
        assert _is_local_url(url) is False

    def test_download_url_rejects_file_scheme(self):
        with pytest.raises(ValueError):
            download_url("file:///etc/passwd")
