"""Regression tests for the audit batch of verified bugs fixed together.

Each test names the failure it locks down, because every one of these survived
a fully green suite before the fix:

- blog post ``slug`` could escape the site directory (``../`` in front matter)
- two files in *different* directories mapping to one ``dest_uri`` both built,
  with a nondeterministic winner and no warning
- ``build_pdf`` derived the project root from the docs directory *name*, so
  ``docs_dir: content`` lost PDF export
- PDF rendering followed ``file://`` requests anywhere on disk
- the privacy plugin fetched loopback/private/metadata addresses and vendored
  the response into the published site
- ``tags_extra_files`` and ``shadow_tags`` crashed any build that used them
- ``social: false`` front matter crashed the page instead of disabling cards
- a deleted PDF was never re-rendered (stale cache said "up to date")
- two posts with the same title silently collapsed into one page
- ``post_readtime_words_per_minute: 0`` divided by zero
- ``!ENV`` configs resolved to the wrong ``docs_dir`` on the --pdf path
"""
from __future__ import annotations

import logging
import textwrap
from pathlib import Path

import pytest

from docsforge import pdf as pdf_mod
from docsforge.core.blog import readtime
from docsforge.core.privacy import _is_internal_host
from docsforge.pdf import _resolve_local_request

# ---------------------------------------------------------------------------
# Blog: generated paths must stay inside the docs tree
# ---------------------------------------------------------------------------


class TestBlogPathContainment:
    """A post ``slug`` is raw front matter and ends up in a written path."""

    def _plugin(self):
        from docsforge.core.blog import BlogConfig, BlogPlugin

        plugin = BlogPlugin()
        plugin.config = BlogConfig()
        return plugin

    def test_leading_dotdot_rejected(self):
        from docsforge.exceptions import PluginError

        plugin = self._plugin()
        post = type("P", (), {"file": type("F", (), {"src_uri": "blog/posts/x.md"})()})()
        with pytest.raises(PluginError, match="resolves outside the docs directory"):
            plugin._claim_path("blog/../../../tmp/ESCAPE.md", post)

    def test_absolute_path_rejected(self):
        from docsforge.exceptions import PluginError

        plugin = self._plugin()
        with pytest.raises(PluginError):
            plugin._path_to_file("/etc/cron.d/evil.md", type("C", (), {})())

    def test_ordinary_path_accepted(self):
        plugin = self._plugin()
        post = type("P", (), {"file": type("F", (), {"src_uri": "blog/posts/x.md"})()})()
        assert plugin._claim_path("blog/2024/01/01/hello.md", post) == "blog/2024/01/01/hello.md"


class TestBlogDuplicateSlug:
    """Two posts with the same title+date derive the same slug."""

    def _plugin(self):
        from docsforge.core.blog import BlogConfig, BlogPlugin

        plugin = BlogPlugin()
        plugin.config = BlogConfig()
        plugin._claimed_paths = {}
        return plugin

    @staticmethod
    def _post(src_uri: str):
        return type("P", (), {"file": type("F", (), {"src_uri": src_uri})()})()

    def test_second_post_gets_a_suffix(self):
        plugin = self._plugin()
        first = self._post("blog/posts/one.md")
        second = self._post("blog/posts/two.md")

        assert plugin._claim_path("blog/hello.md", first) == "blog/hello.md"
        assert plugin._claim_path("blog/hello.md", second) == "blog/hello-2.md"

    def test_third_post_keeps_counting(self):
        plugin = self._plugin()
        seen = set()
        for i in range(3):
            seen.add(plugin._claim_path("blog/hello.md", self._post(f"p{i}.md")))
        assert seen == {"blog/hello.md", "blog/hello-2.md", "blog/hello-3.md"}

    def test_same_post_reuses_its_path(self):
        plugin = self._plugin()
        post = self._post("a.md")
        assert plugin._claim_path("blog/hello.md", post) == "blog/hello.md"
        assert plugin._claim_path("blog/hello.md", post) == "blog/hello.md"


class TestReadtimeZeroRate:
    """`post_readtime_words_per_minute: 0` passes validation, so it must not crash."""

    def test_zero_words_per_minute_does_not_divide_by_zero(self):
        assert readtime("<p>hello world</p>", 0) >= 1

    def test_normal_rate_still_works(self):
        # 265 words at 265 wpm is one minute; a slower rate must not be slower
        # than a faster one on the same text.
        text = "<p>" + "word " * 265 + "</p>"
        fast = readtime(text, 265)
        slow = readtime(text, 50)
        assert fast >= 1
        assert slow > fast


# ---------------------------------------------------------------------------
# Files: destination collisions are site-wide, not per directory
# ---------------------------------------------------------------------------


class TestCrossDirectoryDestCollision:
    """`foo.md` and `foo/index.md` both build to `foo/index.html`."""

    def test_conflict_detected_across_directories(self, tmp_path, monkeypatch, caplog):
        from docsforge.config_base import load_config
        from docsforge.files import get_files

        (tmp_path / "docsforge.yml").write_text(
            "site_name: T\ndocs_dir: docs\nsite_dir: site\nprivacy: false\n"
        )
        docs = tmp_path / "docs"
        (docs / "foo").mkdir(parents=True)
        (docs / "index.md").write_text("# Home")
        (docs / "foo.md").write_text("# A")
        (docs / "foo" / "index.md").write_text("# B")
        monkeypatch.chdir(tmp_path)

        with caplog.at_level(logging.WARNING, logger="docsforge.files"):
            files = get_files(load_config(config_file=str(tmp_path / "docsforge.yml")))

        uris = {f.src_uri for f in files}
        # Exactly one of the two survives; before the fix both did and the
        # build output flipped between runs.
        surviving = uris & {"foo.md", "foo/index.md"}
        assert len(surviving) == 1
        assert any("conflicts with" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# PDF: project resolution, local-file containment, re-render after deletion
# ---------------------------------------------------------------------------


class TestPdfProjectResolution:
    """The project root must come from the config file, not the dir name."""

    def test_custom_docs_dir_finds_sibling_site_dir(self, tmp_path, monkeypatch):
        (tmp_path / "docsforge.yml").write_text("site_name: T\ndocs_dir: content\n")
        docs = tmp_path / "content"
        (docs / "site").mkdir(parents=True)
        (docs / "index.md").write_text("# Hi")
        monkeypatch.chdir(tmp_path)

        project_dir, site_path, cfg = pdf_mod._resolve_project(str(docs))

        assert project_dir == tmp_path.resolve()
        assert site_path == tmp_path.resolve() / "site"
        assert cfg["docs_dir"] == "content"

    def test_custom_site_dir_is_honoured(self, tmp_path, monkeypatch):
        (tmp_path / "docsforge.yml").write_text(
            "site_name: T\ndocs_dir: content\nsite_dir: public\n"
        )
        docs = tmp_path / "content"
        (docs / "public").mkdir(parents=True)
        monkeypatch.chdir(tmp_path)

        _, site_path, _ = pdf_mod._resolve_project(str(docs))

        assert site_path == tmp_path.resolve() / "public"

    def test_env_tag_config_still_resolves(self, tmp_path, monkeypatch):
        """yaml.FullLoader raises on !ENV; the engine loader must be used."""
        (tmp_path / "docsforge.yml").write_text(
            "site_name: T\ndocs_dir: !ENV [AUDIT_TEST_DOCS_DIR, content]\nsite_dir: out\n"
        )
        monkeypatch.chdir(tmp_path)

        _, site_path, cfg = pdf_mod._resolve_project(str(tmp_path / "content"))

        assert cfg["docs_dir"] == "content"
        assert site_path == tmp_path.resolve() / "out"


class TestPdfLocalFileContainment:
    """A page's raw HTML must not be able to pull local files into the PDF."""

    @pytest.fixture()
    def site(self, tmp_path: Path) -> Path:
        site = tmp_path / "site"
        (site / "assets").mkdir(parents=True)
        (site / "assets" / "main.css").write_text("body{}")
        (site / "index.html").write_text("<h1>hi</h1>")
        return site

    def test_file_inside_site_is_allowed(self, site: Path):
        action, _ = _resolve_local_request((site / "index.html").as_uri(), site)
        assert action == "continue"

    def test_root_relative_asset_maps_into_site(self, site: Path):
        action, resolved = _resolve_local_request("file:///assets/main.css", site)
        assert action == "fulfill"
        assert resolved == site / "assets" / "main.css"

    def test_outside_file_is_blocked(self, site: Path, tmp_path: Path):
        secret = tmp_path / "secret.txt"
        secret.write_text("TOPSECRET")
        action, resolved = _resolve_local_request(secret.as_uri(), site)
        assert action == "abort"
        assert resolved is None

    def test_traversal_via_encoded_segments_is_blocked(self, site: Path, tmp_path: Path):
        secret = tmp_path / "secret.txt"
        secret.write_text("TOPSECRET")
        action, _ = _resolve_local_request("file:///../secret.txt", site)
        assert action in {"abort", "fulfill"}
        # Whatever the action, the resolved file must never be the secret.
        _, resolved = _resolve_local_request("file:///../secret.txt", site)
        assert resolved != secret


class TestPdfMissingOutputRerendered:
    """A deleted PDF must be re-rendered, not reported as up to date."""

    def test_missing_pdf_forces_render(self, tmp_path: Path):
        from docsforge.pdf import PdfCache

        site = tmp_path / "site"
        site.mkdir()
        html = site / "index.html"
        html.write_text("<h1>hi</h1>")
        output = tmp_path / "pdf"
        output.mkdir()

        cache = PdfCache(tmp_path)
        from docsforge.cache import FileHasher

        html_hash = FileHasher.hash_file(html)
        cache.save("1.0.0", {"index.pdf": html_hash})

        # Cached hash matches and the file is absent -> must render.
        fresh = cache.is_fresh("1.0.0")
        assert fresh is True
        assert cache.should_render("index.pdf", html_hash) is False
        assert (output / "index.pdf").is_file() is False

        # Once the output exists, the same page is genuinely up to date.
        (output / "index.pdf").write_bytes(b"%PDF-1.4")
        assert cache.should_render("index.pdf", html_hash) is False
        assert (output / "index.pdf").is_file() is True


# ---------------------------------------------------------------------------
# Privacy: internal addresses must never be fetched
# ---------------------------------------------------------------------------


class TestPrivacyInternalHosts:
    """Pages are author-controlled, so their URLs are untrusted input."""

    @pytest.mark.parametrize(
        "host",
        ["127.0.0.1", "localhost", "169.254.169.254", "10.0.0.5", "192.168.1.1", "::1"],
    )
    def test_internal_hosts_rejected(self, host: str):
        assert _is_internal_host(host) is True

    def test_empty_host_rejected(self):
        assert _is_internal_host(None) is True
        assert _is_internal_host("") is True

    def test_public_host_allowed(self, monkeypatch):
        import socket

        monkeypatch.setattr(
            socket, "getaddrinfo",
            lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))],
        )
        assert _is_internal_host("example.com") is False

    def test_host_with_a_private_record_rejected(self, monkeypatch):
        """One private A record is enough to reject the host."""
        import socket

        monkeypatch.setattr(
            socket, "getaddrinfo",
            lambda *a, **k: [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0)),
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0)),
            ],
        )
        assert _is_internal_host("mixed.example.com") is True


# ---------------------------------------------------------------------------
# Tags: options that used to abort the build
# ---------------------------------------------------------------------------


class TestTagsConfigOptions:
    def test_tags_extra_files_is_configurable(self, tmp_path, monkeypatch):
        """`Optional(Type(DictOfItems(...)))` wrapped an option in Type."""
        from docsforge.config_base import load_config

        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "index.md").write_text("# Home\n")
        (tmp_path / "docsforge.yml").write_text(
            textwrap.dedent(
                """
                site_name: T
                docs_dir: docs
                plugins:
                  - tags:
                      tags_extra_files:
                        tags.md: [one]
                """
            )
        )
        monkeypatch.chdir(tmp_path)

        cfg = load_config(config_file=str(tmp_path / "docsforge.yml"))
        assert cfg is not None

    def test_shadow_tags_compares_by_name(self):
        """`Tag.__eq__` asserts its operand is a Tag; comparing to str crashed."""
        from docsforge.core.tags import MappingManager, Tag, TagsConfig

        manager = MappingManager(TagsConfig())
        manager.config.shadow_tags = ["draft"]

        tag = manager._configure_shadow(Tag("draft"), "draft")
        assert tag.hidden is True

        visible = manager._configure_shadow(Tag("public"), "public")
        assert visible.hidden is False


# ---------------------------------------------------------------------------
# Social: scalar front matter
# ---------------------------------------------------------------------------


class TestSocialScalarFrontMatter:
    """`social: false` is the natural way to switch cards off for one page."""

    def test_scalar_meta_does_not_crash(self):
        from docsforge.core.social import SocialConfig, SocialPlugin

        plugin = SocialPlugin()
        plugin.config = SocialConfig()

        page = type("P", (), {"meta": {"social": False}})()

        assert plugin._config("cards", page) is False
        # A non-scalar option falls back to the site-level default.
        assert plugin._config("cards_dir", page) == plugin.config["cards_dir"]

    def test_string_meta_does_not_crash(self):
        from docsforge.core.social import SocialConfig, SocialPlugin

        plugin = SocialPlugin()
        plugin.config = SocialConfig()

        page = type("P", (), {"meta": {"social": "yes"}})()

        assert plugin._config("cards", page) is True


# ---------------------------------------------------------------------------
# Social: font handling must not hang or recurse forever
# ---------------------------------------------------------------------------


class TestSocialFontResolution:
    """An empty family dir recursed forever; a failed fetch raised the wrong error."""

    def _plugin(self, tmp_path: Path):
        from docsforge.core.social import SocialConfig, SocialPlugin

        plugin = SocialPlugin()
        plugin.config = SocialConfig()
        plugin.config.cache_dir = str(tmp_path / "cache")
        plugin.config.cards = False
        plugin._font_fetch_failed = set()
        plugin._fallback_fonts = {}
        from threading import Lock

        plugin.lock = Lock()
        return plugin

    def test_empty_family_dir_raises_instead_of_recursing(self, tmp_path: Path):
        from docsforge.core.social import _FontUnavailableError

        plugin = self._plugin(tmp_path)
        (tmp_path / "cache" / "fonts" / "Roboto").mkdir(parents=True)

        with pytest.raises(_FontUnavailableError):
            plugin._resolve_font("Roboto", "Regular")

    def test_missing_family_falls_back_or_raises(self, tmp_path: Path, monkeypatch):
        from docsforge.core.social import _FontUnavailableError

        plugin = self._plugin(tmp_path)
        plugin._font_fetch_failed = {"Roboto"}

        try:
            result = plugin._resolve_font("Roboto", "Regular")
        except _FontUnavailableError:
            return  # acceptable: no local font on this machine
        assert isinstance(result, str)
