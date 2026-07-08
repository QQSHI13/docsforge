"""Unit tests for the blog plugin (docsforge.core.blog)."""
from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest

from docsforge.core.blog import BlogPlugin, PostConfig
from docsforge.exceptions import PluginError
from docsforge.files import File


def _post_config(**kwargs):
    cfg = PostConfig()
    cfg.load_dict({"date": {"created": datetime(2024, 1, 1)}, **kwargs})
    return cfg


class TestPostConfig:
    def test_readtime_zero_is_honored(self):
        config = _post_config(readtime=0)
        errors, _ = config.validate()
        assert not errors
        assert config.readtime == 0

    def test_readtime_none_kept(self):
        config = _post_config()
        errors, _ = config.validate()
        assert not errors
        assert config.readtime is None


class TestMediaPathReplacement:
    @pytest.fixture()
    def make_file(self):
        def _make(src_uri: str):
            return File(
                src_uri,
                src_dir="/docs",
                dest_dir="/site",
                use_directory_urls=True,
            )
        return _make

    def test_replaces_only_leading_prefix(self, make_file):
        path = "blog/posts"
        root = "blog"
        file = make_file("blog/posts/image.png")

        # Mimic the logic in BlogPlugin.on_files for media files
        assert file.src_uri.startswith(path + "/")
        file.dest_uri = root + file.dest_uri[len(path):]
        file.url = file._get_url()

        assert file.dest_uri == "blog/image.png"
        assert file.url == "blog/image.png"

    def test_does_not_replace_similar_prefix(self, make_file):
        path = "blog/posts"
        root = "blog"
        file = make_file("blog/posts-extra/image.png")

        assert not file.src_uri.startswith(path + "/")
        assert file.dest_uri == "blog/posts-extra/image.png"
        assert file.url == "blog/posts-extra/image.png"


class TestPagination:
    @pytest.fixture()
    def plugin(self):
        p = BlogPlugin()
        p.load_config({})
        return p

    def _make_page(self, posts, pages=None, url="blog/"):
        return SimpleNamespace(
            posts=posts,
            pages=pages or [],
            url=url,
            file=SimpleNamespace(src_uri="blog/index.md"),
            toc=SimpleNamespace(items=[]),
        )

    def _make_post(self, number: int):
        excerpt = SimpleNamespace(
            render=lambda _page, _sep: None,
            toc=SimpleNamespace(items=[]),
            number=number,
        )
        return SimpleNamespace(excerpt=excerpt, number=number)

    def test_render_uses_current_page_index(self, plugin):
        posts = [self._make_post(i) for i in range(25)]
        page1 = self._make_page(posts, url="blog/")
        page2 = self._make_page(posts, url="blog/page/2/")
        page3 = self._make_page(posts, url="blog/page/3/")
        page1.pages = page2.pages = page3.pages = [page1, page2, page3]

        rendered, _ = plugin._render(page2)
        assert [e.number for e in rendered] == list(range(10, 20))

    def test_generate_pages_starts_fresh_each_call(self, plugin):
        view = self._make_page([self._make_post(i) for i in range(5)])
        config = SimpleNamespace(docs_dir="/docs", site_dir="/site")
        files = SimpleNamespace(
            get_file_from_path=lambda _path: None,
            append=lambda _file: None,
        )
        # Monkey-patch helpers that need real file I/O
        plugin._path_to_file = lambda path, _cfg: SimpleNamespace(
            src_uri=path,
            abs_src_path=f"/tmp/{path}",
            inclusion=None,
            page=SimpleNamespace(
                __class__=type("View", (), {}),
            ),
        )

        pages1 = list(plugin._generate_pages(view, config, files))
        pages2 = list(plugin._generate_pages(view, config, files))

        assert len(pages1) == len(pages2) == 1
        assert pages1[0] is view


class TestAuthorGuard:
    def test_missing_author_raises_plugin_error(self):
        plugin = BlogPlugin()
        plugin.load_config({})
        plugin.authors = {}
        plugin.blog = SimpleNamespace(posts=[
            SimpleNamespace(
                config=SimpleNamespace(authors=["ghost"]),
                file=SimpleNamespace(abs_src_path="/docs/blog/posts/a.md"),
            )
        ])

        config = SimpleNamespace(docs_dir="/docs")
        with pytest.raises(PluginError):
            list(plugin._generate_profiles(config, None))



