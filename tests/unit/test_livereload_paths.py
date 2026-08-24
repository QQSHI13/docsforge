"""Unit tests for request-path containment in the live-reload server.

The dev server maps request paths onto the filesystem, so `_resolve_within_root`
is the single security boundary between a URL and an `open()` call. These tests
pin that boundary: nothing a client can send may resolve outside the site root.

CodeQL flags this call site as `py/path-injection` (alert #4, dismissed as a
false positive, re-raised as #13 when unrelated edits shifted the line numbers).
The rule cannot see that normalization happens before the join, so the finding
is expected; these tests are what actually establishes the guard holds.
"""
from __future__ import annotations

import os

from docsforge.livereload import LiveReloadServer


def _make_server(root, mount_path="/"):
    # bind_and_activate=False -> no real socket/port needed.
    return LiveReloadServer(
        builder=lambda: None,
        host="127.0.0.1",
        port=0,
        root=str(root),
        mount_path=mount_path,
    )


class TestResolveWithinRoot:
    """Every path a client can send must resolve inside the root, or be rejected."""

    def test_plain_file_resolves(self, tmp_path):
        site = tmp_path / "site"
        site.mkdir()
        (site / "index.html").write_text("ok")

        server = _make_server(site)
        resolved = server._resolve_within_root("index.html")

        assert resolved == os.path.realpath(str(site / "index.html"))

    def test_nested_file_resolves(self, tmp_path):
        site = tmp_path / "site"
        (site / "sub").mkdir(parents=True)
        (site / "sub" / "page.html").write_text("ok")

        server = _make_server(site)
        resolved = server._resolve_within_root("sub/page.html")

        assert resolved == os.path.realpath(str(site / "sub" / "page.html"))

    def test_root_itself_resolves(self, tmp_path):
        site = tmp_path / "site"
        site.mkdir()

        server = _make_server(site)

        assert server._resolve_within_root("") == os.path.realpath(str(site))

    def test_traversal_never_escapes_the_root(self, tmp_path):
        """`..` segments are collapsed against the leading slash, never escape.

        The secret file sits next to the site root, which is the realistic
        layout: a project directory containing both `site/` and source files.
        """
        site = tmp_path / "site"
        site.mkdir()
        (tmp_path / "secret.txt").write_text("PWNED")

        server = _make_server(site)
        base = os.path.realpath(str(site))

        attacks = [
            "../secret.txt",
            "../../secret.txt",
            "./../secret.txt",
            "/../secret.txt",
            "foo/../../secret.txt",
            "subdir/../../secret.txt",
            "../" * 20 + "etc/passwd",
            "..",
            "../",
        ]
        for attack in attacks:
            resolved = server._resolve_within_root(attack)
            assert resolved is None or resolved == base or resolved.startswith(base + os.sep), (
                f"{attack!r} escaped the root: {resolved}"
            )
            # Whatever it resolved to, it must not be the secret.
            assert resolved != os.path.realpath(str(tmp_path / "secret.txt"))

    def test_encoded_traversal_is_not_decoded_into_an_escape(self, tmp_path):
        """Percent-encoded dots stay literal - they must not become `..`."""
        site = tmp_path / "site"
        site.mkdir()
        (tmp_path / "secret.txt").write_text("PWNED")

        server = _make_server(site)
        base = os.path.realpath(str(site))

        for attack in ("..%2fsecret.txt", "%2e%2e/secret.txt", "....//secret.txt"):
            resolved = server._resolve_within_root(attack)
            assert resolved is None or resolved.startswith(base + os.sep), (
                f"{attack!r} escaped the root: {resolved}"
            )

    def test_sibling_directory_sharing_the_root_prefix_is_rejected(self, tmp_path):
        """`/sitezz` must not pass a containment check against root `/site`.

        This is why the guard compares against `root + os.sep` rather than
        using a bare `startswith(root)`.
        """
        site = tmp_path / "site"
        site.mkdir()
        sibling = tmp_path / "sitezz"
        sibling.mkdir()
        (sibling / "x.txt").write_text("SIBLING")

        server = _make_server(site)
        base = os.path.realpath(str(site))
        resolved = server._resolve_within_root("../sitezz/x.txt")

        assert resolved is None or resolved.startswith(base + os.sep)
        assert resolved != os.path.realpath(str(sibling / "x.txt"))

    def test_symlink_pointing_outside_the_root_is_rejected(self, tmp_path):
        """realpath resolves symlinks, so an escaping link must be caught."""
        site = tmp_path / "site"
        site.mkdir()
        secret = tmp_path / "secret.txt"
        secret.write_text("PWNED")

        link = site / "link.txt"
        try:
            os.symlink(str(secret), str(link))
        except OSError:  # pragma: no cover - Windows without developer mode
            return

        server = _make_server(site)

        assert server._resolve_within_root("link.txt") is None

    def test_absolute_path_cannot_hijack_the_join(self, tmp_path):
        """A leading slash must not make os.path.join discard the root."""
        site = tmp_path / "site"
        site.mkdir()

        server = _make_server(site)
        base = os.path.realpath(str(site))
        resolved = server._resolve_within_root("/etc/passwd")

        assert resolved is None or resolved.startswith(base + os.sep)
        assert resolved != "/etc/passwd"
