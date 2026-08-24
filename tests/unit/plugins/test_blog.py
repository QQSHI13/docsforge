"""Unit tests for the blog plugin (docsforge.core.blog)."""
from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest

from docsforge.core.blog import BlogConfig, BlogPlugin, DateDict, Post, PostConfig, PostDate
from docsforge.exceptions import PluginError
from docsforge.files import File, Files


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


class TestResolvePosts:
    @pytest.fixture()
    def plugin(self):
        p = BlogPlugin()
        p.load_config({})
        return p

    def _make_files(self, tmp_path, *src_uris):
        docs = tmp_path / "docs"
        files = []
        for uri in src_uris:
            path = docs / uri
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "---\ndate:\n  created: 2024-01-01\n---\n\n# Post\n",
                encoding="utf-8",
            )
            files.append(File(uri, str(docs), str(tmp_path / "site"), True))
        return Files(files)

    def _resolve_post_uris(self, plugin, files, tmp_path):
        # Stub out post resolution, as these tests target path filtering only
        plugin._resolve_post = lambda file, _config: file
        plugin._is_excluded = lambda _post: False

        config = SimpleNamespace(
            docs_dir=str(tmp_path / "docs"),
            site_dir=str(tmp_path / "site"),
        )
        return [post.src_uri for post in plugin._resolve_posts(files, config)]

    def test_resolves_posts_in_posts_directory(self, plugin, tmp_path):
        files = self._make_files(
            tmp_path, "blog/posts/a.md", "blog/index.md", "index.md"
        )
        assert self._resolve_post_uris(plugin, files, tmp_path) == [
            "blog/posts/a.md"
        ]

    def test_ignores_pages_with_matching_path_prefix(self, plugin, tmp_path):
        files = self._make_files(
            tmp_path, "blog/posts/a.md", "blog/posts.md", "blog/posts-old/b.md"
        )
        assert self._resolve_post_uris(plugin, files, tmp_path) == [
            "blog/posts/a.md"
        ]

    def test_resolves_posts_with_windows_separators(self, plugin, tmp_path):
        # Simulate Windows, where os.path.normpath converts the path of the
        # posts directory to backslashes, while source URIs always use
        # forward slashes
        plugin.load_config({"post_dir": "{blog}\\posts"})
        files = self._make_files(tmp_path, "blog/posts/a.md")
        assert self._resolve_post_uris(plugin, files, tmp_path) == [
            "blog/posts/a.md"
        ]


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


class TestPostDate:
    def test_truthiness_check_does_not_reject_falsy_datetime(self):
        """A datetime subclass that evaluates to falsy must not be treated as missing."""
        class FalsyDateTime(datetime):
            def __bool__(self):
                return False

        created = FalsyDateTime(2024, 1, 1, tzinfo=datetime.now().tzinfo)
        value = DateDict({"created": created})
        option = PostDate()

        # Before the fix this raised "Expected 'created' date ..." because the
        # code checked `if not value.created`. After the fix it checks `is None`
        # and correctly validates the present (albeit falsy) datetime.
        result = option.run_validation(value)
        assert result is value
        assert result.created is created


class TestPostMetaMarkdown:
    def test_on_page_markdown_return_value_is_assigned(self, tmp_path, mocker):
        """The return value of the meta plugin's on_page_markdown must update self.markdown."""

        class FakeConfig:
            def __init__(self, docs_dir, plugins):
                self.docs_dir = docs_dir
                self.plugins = plugins

            def get(self, key, default=None):
                return getattr(self, key, default)

        docs = tmp_path / "docs"
        docs.mkdir()
        post_file = docs / "posts" / "a.md"
        post_file.parent.mkdir(parents=True, exist_ok=True)
        post_file.write_text(
            "---\ndate:\n  created: 2024-01-01\n---\n\n# Hello\n",
            encoding="utf-8",
        )

        file = File(str(post_file.relative_to(docs)), str(docs), str(tmp_path / "site"), True)
        file.abs_src_path = str(post_file)

        meta_plugin = mocker.MagicMock()
        meta_plugin.on_page_markdown.return_value = "# Modified\n"

        config = FakeConfig(str(docs), {"material/meta": meta_plugin})

        post = Post(file, config)

        meta_plugin.on_page_markdown.assert_called_once_with(
            "# Hello\n", page=post, config=config, files=None
        )
        assert post.markdown == "# Modified\n"


class TestBlogConfigDefaults:
    def test_categories_allowed_defaults_are_isolated(self):
        """Each BlogConfig instance must get its own categories_allowed list."""
        config1 = BlogConfig()
        config2 = BlogConfig()

        # Default should be empty
        assert config1.categories_allowed == []
        assert config2.categories_allowed == []

        # Modifying one config must not affect the other
        config1.categories_allowed.append("news")
        assert config1.categories_allowed == ["news"]
        assert config2.categories_allowed == []
