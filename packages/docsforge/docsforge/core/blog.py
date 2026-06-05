"""Blog plugin - post authoring, archives, categories, authors."""

from __future__ import annotations

import logging
import os
import posixpath
import re
import yaml

from collections.abc import Callable
from copy import copy
from datetime import date, datetime, time, timezone
from html.parser import HTMLParser
from jinja2 import pass_context
from jinja2.runtime import Context
from markdown import Markdown
from markdown.treeprocessors import Treeprocessor
from math import ceil
from paginate import Page as Pagination
from pymdownx.slugs import slugify
from re import Match
from shutil import rmtree
from typing import Dict
from tempfile import mkdtemp
from urllib.parse import urlparse
from xml.etree.ElementTree import Element
from yaml import SafeLoader

from docsforge import copy_file, get_relative_url
from docsforge.config_base import BaseConfigOption, Config, ValidationError
from docsforge.config_defaults import DocsForgeConfig
from docsforge.config_options import Choice, Deprecated, DictOfItems, ListOfItems, Optional, SubConfig, T, Type
from docsforge.core.meta import MetaPlugin
from docsforge.core.search import void
from docsforge.exceptions import PluginError
from docsforge.files import File, Files, InclusionLevel
from docsforge.meta import YAML_RE
from docsforge.nav import Link, Navigation, Section, _add_parent_links, _data_to_navigation
from docsforge.pages import Page, _RelativePathTreeprocessor
from docsforge.core.plugin_base import BasePlugin, event_priority
from docsforge.structure import StructureItem
from docsforge.toc import AnchorLink, TableOfContents, get_toc

# -----------------------------------------------------------------------------
# Classes
# -----------------------------------------------------------------------------

# Date dictionary
class DateDict(Dict[str, datetime]):

    # Initialize date dictionary
    def __init__(self, data: dict):
        super().__init__(data)

        # Ensure presence of `date.created`
        self.created: datetime = data["created"]

    # Allow attribute access
    def __getattr__(self, name: str):
        if name in self:
            return self[name]

# -----------------------------------------------------------------------------

# Post date option
class PostDate(BaseConfigOption[DateDict]):

    # Initialize post dates
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # Normalize the supported types for post dates to datetime
    def pre_validation(self, config: Config, key_name: str):

        # If the date points to a scalar value, convert it to a dictionary, as
        # we want to allow the author to specify custom and arbitrary dates for
        # posts. Currently, only the `created` date is mandatory, because it's
        # needed to sort posts for views.
        if not isinstance(config[key_name], dict):
            config[key_name] = { "created": config[key_name] }

        # Convert all date values to datetime
        for key, value in config[key_name].items():

            # Handle datetime - since datetime is a subclass of date, we need
            # to check it first, or we lose the time - see https://t.ly/-KG9N
            if isinstance(value, datetime):
                # Set timezone to UTC if not set
                if value.tzinfo is None:
                    config[key_name][key] = value.replace(tzinfo=timezone.utc)
                continue;


            # Handle date - we set 00:00:00 as the default time, if the author
            # only supplied a date, and convert it to datetime in UTC
            if isinstance(value, date):
                config[key_name][key] = datetime.combine(value, time()).replace(tzinfo=timezone.utc)

        # Initialize date dictionary
        config[key_name] = DateDict(config[key_name])

    # Ensure each date value is of type datetime
    def run_validation(self, value: DateDict):
        for key in value:
            if not isinstance(value[key], datetime):
                raise ValidationError(
                    f"Expected type: {date} or {datetime} "
                    f"but received: {type(value[key])}"
                )

        # Ensure presence of `date.created`
        if not value.created:
            raise ValidationError(
                "Expected 'created' date when using dictionary syntax"
            )

        # Return date dictionary
        return value

# -----------------------------------------------------------------------------

# Post links option
class PostLinks(BaseConfigOption[Navigation]):

    # Create navigation from structured items - we don't need to provide a
    # configuration object to the function, because it will not be used
    def run_validation(self, value: object):
        items = _data_to_navigation(value, Files([]), None)
        _add_parent_links(items)

        # Return navigation
        return Navigation(items, [])

# -----------------------------------------------------------------------------

# Unique list of items
class UniqueListOfItems(ListOfItems[T]):

    # Ensure that each item is unique
    def run_validation(self, value: object):
        data = super().run_validation(value)
        return list(dict.fromkeys(data))


#-----------------------------------------------------------------------------
# From structure/config.py
#-----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Classes
# -----------------------------------------------------------------------------

# Post configuration
class PostConfig(Config):
    authors = UniqueListOfItems(Type(str), default = [])
    categories = UniqueListOfItems(Type(str), default = [])
    date = PostDate()
    draft = Optional(Type(bool))
    pin = Type(bool, default = False)
    links = Optional(PostLinks())
    readtime = Optional(Type(int))
    slug = Optional(Type(str))


#-----------------------------------------------------------------------------
# From structure/markdown.py
#-----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Classes
# -----------------------------------------------------------------------------

# Excerpt tree processor
class ExcerptTreeprocessor(Treeprocessor):

    # Initialize excerpt tree processor
    def __init__(self, page: Page, base: Page | None = None):
        self.page = page
        self.base = base

    # Transform HTML after Markdown processing
    def run(self, root: Element):
        assert self.base
        main = True

        # We're only interested in anchors, which is why we continue when the
        # link does not start with an anchor tag
        for el in root.iter("a"):
            anchor = el.get("href")
            if not anchor.startswith("#"):
                continue

            # The main headline should link to the post page, not to a specific
            # anchor, which is why we remove the anchor in that case
            path = get_relative_url(self.page.url, self.base.url)
            if main:
                el.set("href", path)
            else:
                el.set("href", path + anchor)

            # Main headline has been seen
            main = False


#-----------------------------------------------------------------------------
# From author.py
#-----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Classes
# -----------------------------------------------------------------------------

# Author
class Author(Config):
    name = Type(str)
    description = Type(str)
    avatar = Type(str)
    slug = Optional(Type(str))
    url = Optional(Type(str))

# -----------------------------------------------------------------------------

# Authors
class Authors(Config):
    authors = DictOfItems(SubConfig(Author), default = {})


#-----------------------------------------------------------------------------
# From config.py
#-----------------------------------------------------------------------------

# Sort views by name
def view_name(view: View):
    return view.name


# -----------------------------------------------------------------------------
# Classes
# -----------------------------------------------------------------------------

# Blog plugin configuration
class BlogConfig(Config):
    enabled = Type(bool, default = True)

    # Settings for blog
    blog_dir = Type(str, default = "blog")
    blog_toc = Type(bool, default = False)

    # Settings for posts
    post_dir = Type(str, default = "{blog}/posts")
    post_date_format = Type(str, default = "long")
    post_url_date_format = Type(str, default = "yyyy/MM/dd")
    post_url_format = Type(str, default = "{date}/{slug}")
    post_url_max_categories = Type(int, default = 1)
    post_slugify = Type(Callable, default = slugify(case = "lower"))
    post_slugify_separator = Type(str, default = "-")
    post_excerpt = Choice(["optional", "required"], default = "optional")
    post_excerpt_max_authors = Type(int, default = 1)
    post_excerpt_max_categories = Type(int, default = 5)
    post_excerpt_separator = Type(str, default = "<!-- more -->")
    post_readtime = Type(bool, default = True)
    post_readtime_words_per_minute = Type(int, default = 265)

    # Settings for archive
    archive = Type(bool, default = True)
    archive_name = Type(str, default = "blog.archive")
    archive_date_format = Type(str, default = "yyyy")
    archive_url_date_format = Type(str, default = "yyyy")
    archive_url_format = Type(str, default = "archive/{date}")
    archive_pagination = Optional(Type(bool))
    archive_pagination_per_page = Optional(Type(int))
    archive_toc = Optional(Type(bool))

    # Settings for categories
    categories = Type(bool, default = True)
    categories_name = Type(str, default = "blog.categories")
    categories_url_format = Type(str, default = "category/{slug}")
    categories_slugify = Type(Callable, default = slugify(case = "lower"))
    categories_slugify_separator = Type(str, default = "-")
    categories_sort_by = Type(Callable, default = view_name)
    categories_sort_reverse = Type(bool, default = False)
    categories_allowed = Type(list, default = [])
    categories_pagination = Optional(Type(bool))
    categories_pagination_per_page = Optional(Type(int))
    categories_toc = Optional(Type(bool))

    # Settings for authors
    authors = Type(bool, default = True)
    authors_file = Type(str, default = "{blog}/.authors.yml")
    authors_profiles = Type(bool, default = False)
    authors_profiles_name = Type(str, default = "blog.authors")
    authors_profiles_url_format = Type(str, default = "author/{slug}")
    authors_profiles_pagination = Optional(Type(bool))
    authors_profiles_pagination_per_page = Optional(Type(int))
    authors_profiles_toc = Optional(Type(bool))

    # Settings for pagination
    pagination = Type(bool, default = True)
    pagination_per_page = Type(int, default = 10)
    pagination_url_format = Type(str, default = "page/{page}")
    pagination_format = Type(str, default = "~2~")
    pagination_if_single_page = Type(bool, default = False)
    pagination_keep_content = Type(bool, default = False)

    # Settings for drafts
    draft = Type(bool, default = False)
    draft_on_serve = Type(bool, default = True)
    draft_if_future_date = Type(bool, default = False)

    # Deprecated settings
    pagination_template = Deprecated(moved_to = "pagination_format")


#-----------------------------------------------------------------------------
# From readtime/parser.py
#-----------------------------------------------------------------------------

# TODO: Refactor the `void` set into a common module and import it from there
# and not from the search plugin.

# -----------------------------------------------------------------------------
# Classes
# -----------------------------------------------------------------------------

# Readtime parser
class ReadtimeParser(HTMLParser):

    # Initialize parser
    def __init__(self):
        super().__init__(convert_charrefs = True)

        # Tags to skip
        self.skip = set([
            "object",                  # Objects
            "script",                  # Scripts
            "style",                   # Styles
            "svg"                      # SVGs
        ])

        # Current context
        self.context = []

        # Keep track of text and images
        self.text   = []
        self.images = 0

    # Called at the start of every HTML tag
    def handle_starttag(self, tag, attrs):
        # Collect images
        if tag == "img":
            self.images += 1

        # Ignore self-closing tags
        if tag not in void:
            # Add tag to context
            self.context.append(tag)

    # Called for the text contents of each tag
    def handle_data(self, data):
        # Collect text if not inside skip context
        if not self.skip.intersection(self.context):
            self.text.append(data)

    # Called at the end of every HTML tag
    def handle_endtag(self, tag):
        if self.context and self.context[-1] == tag:
            # Remove tag from context
            self.context.pop()


#-----------------------------------------------------------------------------
# From readtime/__init__.py
#-----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------

# Compute readtime - we first used the original readtime library, but the list
# of dependencies it brings with it increased the size of the Docker image by
# 20 MB (packed), which is an increase of 50%. For this reason, we adapt the
# original readtime algorithm to our needs - see https://t.ly/fPZ7L
def readtime(html: str, words_per_minute: int):
    parser = ReadtimeParser()
    parser.feed(html)
    parser.close()

    # Extract words from text and compute readtime in seconds
    words = len(re.split(r"\W+", "".join(parser.text)))
    seconds = ceil(words / words_per_minute * 60)

    # Account for additional images
    delta = 12
    for _ in range(parser.images):
        seconds += delta
        if delta > 3: delta -= 1

    # Return readtime in minutes
    return ceil(seconds / 60)


#-----------------------------------------------------------------------------
# From structure/__init__.py
#-----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Classes
# -----------------------------------------------------------------------------

# Post
class Post(Page):

    # Initialize post - posts are never listed in the navigation, which is why
    # they will never include a title that was manually set, so we can omit it
    def __init__(self, file: File, config: DocsForgeConfig):
        super().__init__(None, file, config)

        # Resolve path relative to docs directory
        docs = os.path.relpath(config.docs_dir)
        path = os.path.relpath(file.abs_src_path, docs)

        # Read contents and metadata immediately
        with open(file.abs_src_path, encoding = "utf-8-sig") as f:
            self.markdown = f.read()

            # Sadly, MkDocs swallows any exceptions that occur during parsing.
            # Since we want to provide the best possible user experience, we
            # need to catch errors early and display them nicely. We decided to
            # drop support for MkDocs' MultiMarkdown syntax, because it is not
            # correctly implemented anyway. When using MultiMarkdown syntax, all
            # date formats are returned as strings and list are not properly
            # supported. Thus, we just use the relevants parts of `get_data`.
            match: Match = YAML_RE.match(self.markdown)
            if not match:
                raise PluginError(
                    f"Error reading metadata of post '{path}' in '{docs}':\n"
                    f"Expected metadata to be defined but found nothing"
                )

            # Extract metadata and parse as YAML
            try:
                self.meta = yaml.load(match.group(1), SafeLoader) or {}
                self.markdown = self.markdown[match.end():].lstrip("\n")

            # The post's metadata could not be parsed because of a syntax error,
            # which we display to the author with a nice error message
            except Exception as e:
                raise PluginError(
                    f"Error reading metadata of post '{path}' in '{docs}':\n"
                    f"{e}"
                )

            # Hack: if the meta plugin is registered, we need to move the call
            # to `on_page_markdown` here, because we need to merge the metadata
            # of the post with the metadata of any meta files prior to creating
            # the post configuration. To our current knowledge, it's the only
            # way to allow posts to receive metadata from meta files, because
            # posts must be loaded prior to constructing the navigation in
            # `on_files` but the meta plugin first runs in `on_page_markdown`.
            plugin: MetaPlugin = config.plugins.get("material/meta")
            if plugin:
                plugin.on_page_markdown(
                    self.markdown, page = self, config = config, files = None
                )

        # Initialize post configuration, but remove all keys that this plugin
        # doesn't care about, or they will be reported as invalid configuration
        self.config: PostConfig = PostConfig(file.abs_src_path)
        self.config.load_dict({
            key: self.meta[key] for key in (
                set(self.meta.keys()) &
                set(self.config.keys())
            )
        })

        # Validate configuration and throw if errors occurred
        errors, warnings = self.config.validate()
        for _, w in warnings:
            log.warning(w)
        for k, e in errors:
            raise PluginError(
                f"Error reading metadata '{k}' of post '{path}' in '{docs}':\n"
                f"{e}"
            )

        # Excerpts are subsets of posts that are used in pages like archive and
        # category views. They are not rendered as standalone pages, but are
        # rendered in the context of a view. Each post has a dedicated excerpt
        # instance which is reused when rendering views.
        self.excerpt: Excerpt = None

        # Initialize authors and actegories
        self.authors: list[Author] = []
        self.categories: list[Category] = []

        # Ensure template is set or use default
        self.meta.setdefault("template", "blog-post.html")

        # Ensure template hides navigation
        self.meta["hide"] = self.meta.get("hide", [])
        if "navigation" not in self.meta["hide"]:
            self.meta["hide"].append("navigation")

    # The contents and metadata were already read in the constructor (and not
    # in `read_source` as for pages), so this function must be set to a no-op
    def read_source(self, config: DocsForgeConfig):
        pass

# -----------------------------------------------------------------------------

# Excerpt
class Excerpt(Page):

    # Initialize an excerpt for the given post - we create the Markdown parser
    # when intitializing the excerpt in order to improve rendering performance
    # for excerpts, as they are reused across several different views, because
    # posts might be referenced from multiple different locations
    def __init__(self, post: Post, config: DocsForgeConfig, files: Files):
        self.file = copy(post.file)
        self.post = post

        # Set canonical URL, or we can't print excerpts when debugging the
        # blog plugin, as the `abs_url` property would be missing
        self._set_canonical_url(config.site_url)

        # Initialize configuration and metadata
        self.config = post.config
        self.meta   = post.meta

        # Initialize authors and categories - note that views usually contain
        # subsets of those lists, which is why we need to manage them here
        self.authors: list[Author] = []
        self.categories: list[Category] = []

        # Initialize content after separator - allow template authors to render
        # posts inline or to provide a link to the post's page
        self.more = None

        # Initialize parser - note that we need to patch the configuration,
        # more specifically the table of contents extension
        config = _patch(config)
        self.md = Markdown(
            extensions = config.markdown_extensions,
            extension_configs = config.mdx_configs,
        )

        # Register excerpt tree processor - this processor resolves anchors to
        # posts from within views, so they point to the correct location
        self.md.treeprocessors.register(
            ExcerptTreeprocessor(post),
            "excerpt",
            0
        )

        # Register relative path tree processor - this processor resolves links
        # to other pages and assets, and is used by MkDocs itself
        self.md.treeprocessors.register(
            _RelativePathTreeprocessor(self.file, files, config),
            "relpath",
            1
        )

    # Render an excerpt of the post on the given page - note that this is not
    # thread-safe because excerpts are shared across views, as it cuts down on
    # the cost of initialization. However, if in the future, we decide to render
    # posts and views concurrently, we must change this behavior.
    def render(self, page: Page, separator: str):
        self.file.url = page.url

        # Retrieve excerpt tree processor and set page as base
        at = self.md.treeprocessors.get_index_for_name("excerpt")
        processor: ExcerptTreeprocessor = self.md.treeprocessors[at]
        processor.base = page

        # Ensure that the excerpt includes a title in its content, since the
        # title is linked to the post when rendering - see https://t.ly/5Gg2F
        self.markdown = self.post.markdown
        if not self.post._title_from_render:
            self.markdown = "\n\n".join([f"# {self.post.title}", self.markdown])

        # Convert Markdown to HTML and extract excerpt
        self.content = self.md.convert(self.markdown)
        self.content, *more = self.content.split(separator, 1)
        if more:
            self.more = more[0]

        # Extract table of contents and reset post URL - if we wouldn't reset
        # the excerpt URL, linking to the excerpt from the view would not work
        self.toc = get_toc(getattr(self.md, "toc_tokens", []))
        self.file.url = self.post.url

# -----------------------------------------------------------------------------

# View
class View(Page):

    # Parent view
    parent: View | Section

    # Initialize view
    def __init__(self, name: str | None, file: File, config: DocsForgeConfig):
        super().__init__(None, file, config)

        # Initialize name of the view - note that views never pass a title to
        # the parent constructor, so the author can always override the title
        # that is used for rendering. However, for some purposes, like for
        # example sorting, we need something to compare.
        self.name = name

        # Initialize posts and views
        self.posts: list[Post] = []
        self.views: list[View] = []

        # Initialize pages for pagination
        self.pages: list[View] = []

    # Set necessary metadata
    def read_source(self, config: DocsForgeConfig):
        super().read_source(config)

        # Ensure template is set or use default
        self.meta.setdefault("template", "blog.html")

# -----------------------------------------------------------------------------

# Archive view
class Archive(View):
    pass

# -----------------------------------------------------------------------------

# Category view
class Category(View):
    pass

# -----------------------------------------------------------------------------

# Profile view
class Profile(View):
    pass

# -----------------------------------------------------------------------------

# Reference
class Reference(Link):

    # Initialize reference - this is essentially a crossover of pages and links,
    # as it inherits the metadata of the page and allows for anchors
    def __init__(self, title: str, url: str):
        super().__init__(title, url)
        self.meta = {}

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------

# Patch configuration
def _patch(config: DocsForgeConfig):
    config = copy(config)

    # Copy parts of configuration that needs to be patched
    config.validation          = copy(config.validation)
    config.validation.links    = copy(config.validation.links)
    config.markdown_extensions = copy(config.markdown_extensions)
    config.mdx_configs         = copy(config.mdx_configs)

    # Make sure that the author did not add another instance of the table of
    # contents extension to the configuration, as this leads to weird behavior
    if "markdown.extensions.toc" in config.markdown_extensions:
        config.markdown_extensions.remove("markdown.extensions.toc")

    # In order to render excerpts for posts, we need to make sure that the
    # table of contents extension is appropriately configured
    config.mdx_configs["toc"] = {
        **config.mdx_configs.get("toc", {}),
        **{
            "anchorlink": True,        # Render headline as clickable
            "baselevel": 2,            # Render h1 as h2 and so forth
            "permalink": False,        # Remove permalinks
            "toc_depth": 2             # Remove everything below h2
        }
    }

    # Additionally, we disable link validation when rendering excerpts, because
    # invalid links have already been reported when rendering the page
    links = config.validation.links
    links.not_found = logging.DEBUG
    links.absolute_links = logging.DEBUG
    links.unrecognized_links = logging.DEBUG

    # Return patched configuration
    return config

# -----------------------------------------------------------------------------
# Data
# -----------------------------------------------------------------------------

# Set up logging
log = logging.getLogger("mkdocs.material.blog")



# -----------------------------------------------------------------------------
# Classes
# -----------------------------------------------------------------------------

# Blog plugin
class BlogPlugin(BasePlugin[BlogConfig]):
    supports_multiple_instances = True

    # Initialize plugin
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Initialize incremental builds
        self.is_serve = False
        self.is_dirty = False

        # Initialize temporary directory
        self.temp_dir = mkdtemp()

    # Determine whether we're serving the site
    def on_startup(self, *, command, dirty):
        self.is_serve = command == "serve"
        self.is_dirty = dirty

    # Initialize authors and set defaults
    def on_config(self, config):
        if not self.config.enabled:
            return

        # Initialize entrypoint
        self.blog: View

        # Initialize and resolve authors, if enabled
        if self.config.authors:
            self.authors = self._resolve_authors(config)

        # By default, drafts are rendered when the documentation is served,
        # but not when it is built, for a better user experience
        if self.is_serve and self.config.draft_on_serve:
            self.config.draft = True

    # Resolve and load posts and generate views (run later) - we want to allow
    # other plugins to add generated posts or views, so we run this plugin as
    # late as possible. We also need to remove the posts from the navigation
    # before navigation is constructed, as the entrypoint should be considered
    # to be the active page for each post. The URLs of posts are computed before
    # Markdown processing, so that when linking to and from posts, behavior is
    # exactly the same as with regular documentation pages. We create all pages
    # related to posts as part of this plugin, so we control the entire process.
    @event_priority(-50)
    def on_files(self, files, *, config):
        if not self.config.enabled:
            return

        # Resolve path to entrypoint and site directory
        root = posixpath.normpath(self.config.blog_dir)
        site = config.site_dir

        # Compute and normalize path to posts directory
        path = self.config.post_dir.format(blog = root)
        path = posixpath.normpath(path)

        # Adjust destination paths for media files
        for file in files.media_files():
            if not file.src_uri.startswith(path):
                continue

            # We need to adjust destination paths for assets to remove the
            # purely functional posts directory prefix when building
            file.dest_uri      = file.dest_uri.replace(path, root)
            file.abs_dest_path = os.path.join(site, file.dest_path)
            file.url           = file.url.replace(path, root)

        # Resolve entrypoint and posts sorted by descending date - if the posts
        # directory or entrypoint do not exist, they are automatically created
        self.blog = self._resolve(files, config)
        self.blog.posts = sorted(
            self._resolve_posts(files, config),
            key = lambda post: (
                post.config.pin,
                post.config.date.created
            ),
            reverse = True
        )

        # Generate views for archive
        if self.config.archive:
            views = self._generate_archive(config, files)
            self.blog.views.extend(views)

        # Generate views for categories
        if self.config.categories:
            views = self._generate_categories(config, files)

            # We always sort the list of categories by name first, so that any
            # custom sorting function that returns the same value for two items
            # returns them in a predictable and logical order, because sorting
            # in Python is stable, i.e., order of equal items is preserved
            self.blog.views.extend(sorted(
                sorted(views, key = view_name),
                key     = self.config.categories_sort_by,
                reverse = self.config.categories_sort_reverse
            ))

        # Generate views for profiles
        if self.config.authors_profiles:
            views = self._generate_profiles(config, files)
            self.blog.views.extend(views)

        # Generate pages for views
        for view in self._resolve_views(self.blog):
            if self._config_pagination(view):
                for page in self._generate_pages(view, config, files):
                    view.pages.append(page)

        # Ensure that entrypoint is always included in navigation
        self.blog.file.inclusion = InclusionLevel.INCLUDED

    # Attach posts and views to navigation (run later) - again, we allow other
    # plugins to alter the navigation before we start to attach posts and views
    # generated by this plugin at the correct locations in the navigation. Also,
    # we make sure to correct links to the parent and siblings of each page.
    @event_priority(-50)
    def on_nav(self, nav, *, config, files):
        if not self.config.enabled:
            return

        # If we're not building a standalone blog, the entrypoint will always
        # have a parent when it is included in the navigation. The parent is
        # essential to correctly resolve the location where the archive and
        # category views are attached. If the entrypoint doesn't have a parent,
        # we know that the author did not include it in the navigation, so we
        # explicitly mark it as not included.
        if not self.blog.parent and self.config.blog_dir != ".":
            self.blog.file.inclusion = InclusionLevel.NOT_IN_NAV

        # Attach posts to entrypoint without adding them to the navigation, so
        # that the entrypoint is considered to be the active page for each post
        self._attach(self.blog, [None, *reversed(self.blog.posts), None])
        for post in self.blog.posts:
            post.file.inclusion = InclusionLevel.NOT_IN_NAV

        # Revert temporary exclusion of views from navigation
        for view in self._resolve_views(self.blog):
            view.file.inclusion = self.blog.file.inclusion
            for page in view.pages:
                page.file.inclusion = self.blog.file.inclusion

        # Attach views for archive
        if self.config.archive:
            title = self._translate(self.config.archive_name, config)
            views = [_ for _ in self.blog.views if isinstance(_, Archive)]

            # Attach and link views for archive
            if self.blog.file.inclusion.is_in_nav():
                self._attach_to(self.blog, Section(title, views), nav)

        # Attach views for categories
        if self.config.categories:
            title = self._translate(self.config.categories_name, config)
            views = [_ for _ in self.blog.views if isinstance(_, Category)]

            # Attach and link views for categories, if any
            if self.blog.file.inclusion.is_in_nav() and views:
                self._attach_to(self.blog, Section(title, views), nav)

        # Attach views for profiles
        if self.config.authors_profiles:
            title = self._translate(self.config.authors_profiles_name, config)
            views = [_ for _ in self.blog.views if isinstance(_, Profile)]

            # Attach and link views for categories, if any
            if self.blog.file.inclusion.is_in_nav() and views:
                self._attach_to(self.blog, Section(title, views), nav)

        # Attach pages for views
        for view in self._resolve_views(self.blog):
            if self._config_pagination(view):
                for at in range(1, len(view.pages)):
                    self._attach_at(view.parent, view, view.pages[at])

    # Prepare post for rendering (run later) - allow other plugins to alter
    # the contents or metadata of a post before it is rendered and make sure
    # that the post includes a separator, which is essential for rendering
    # excerpts that should be included in views
    @event_priority(-50)
    def on_page_markdown(self, markdown, *, page, config, files):
        if not self.config.enabled:
            return

        # Skip if page is not a post managed by this instance - this plugin has
        # support for multiple instances, which is why this check is necessary
        if page not in self.blog.posts:
            if not self._config_pagination(page):
                return

            # We set the contents of the view to its title if pagination should
            # not keep the content of the original view on paginated views
            if not self.config.pagination_keep_content:
                view = self._resolve_original(page)
                if view in self._resolve_views(self.blog):

                    # If the current view is paginated, use the rendered title
                    # of the original view in case the author set the title in
                    # the page's contents, or it would be overridden with the
                    # one set in mkdocs.yml, leading to inconsistent headings
                    assert isinstance(view, View)
                    if view != page:
                        name = view._title_from_render or view.title
                        return f"# {name}"

            # Nothing more to be done for views
            return

        # Extract and assign authors to post, if enabled
        if self.config.authors:
            for id in page.config.authors:
                if id not in self.authors:
                    raise PluginError(f"Couldn't find author '{id}'")

                # Append to list of authors
                page.authors.append(self.authors[id])

        # Extract settings for excerpts
        separator      = self.config.post_excerpt_separator
        max_authors    = self.config.post_excerpt_max_authors
        max_categories = self.config.post_excerpt_max_categories

        # Ensure presence of separator and throw, if its absent and required -
        # we append the separator to the end of the contents of the post, if it
        # is not already present, so we can remove footnotes or other content
        # from the excerpt without affecting the content of the excerpt
        if separator not in page.markdown:
            if self.config.post_excerpt == "required":
                docs = os.path.relpath(config.docs_dir)
                path = os.path.relpath(page.file.abs_src_path, docs)
                raise PluginError(
                    f"Couldn't find '{separator}' in post '{path}' in '{docs}'"
                )

        # Create excerpt for post and inherit authors and categories - excerpts
        # can contain a subset of the authors and categories of the post
        page.excerpt            = Excerpt(page, config, files)
        page.excerpt.authors    = page.authors[:max_authors]
        page.excerpt.categories = page.categories[:max_categories]

    # Process posts
    def on_page_content(self, html, *, page, config, files):
        if not self.config.enabled:
            return

        # Skip if page is not a post managed by this instance - this plugin has
        # support for multiple instances, which is why this check is necessary
        if page not in self.blog.posts:
            return

        # Compute readtime of post, if enabled and not explicitly set
        if self.config.post_readtime:
            words_per_minute = self.config.post_readtime_words_per_minute
            if not page.config.readtime:
                page.config.readtime = readtime(html, words_per_minute)

    # Register template filters for plugin
    def on_env(self, env, *, config, files):
        if not self.config.enabled:
            return

        # Transform links to point to posts and pages
        for post in self.blog.posts:
            self._generate_links(post, config, files)

        # Filter for formatting dates related to posts
        def date_filter(date: datetime):
            return self._format_date_for_post(date, config)

        # Fetch URL template filter from environment - the filter might
        # be overridden by other plugins, so we must retrieve and wrap it
        url_filter = env.filters["url"]

        # Patch URL template filter to add support for paginated views, i.e.,
        # that paginated views never link to themselves but to the main vie
        @pass_context
        def url_filter_with_pagination(context: Context, url: str | None):
            page = context["page"]

            # If the current page is a view, check if the URL links to the page
            # itself, and replace it with the URL of the main view
            if isinstance(page, View):
                view = self._resolve_original(page)
                if page.url == url:
                    url = view.url

            # Forward to original template filter
            return url_filter(context, url)

        # Register custom template filters
        env.filters["date"] = date_filter
        env.filters["url"]  = url_filter_with_pagination

    # Prepare view for rendering (run latest) - views are rendered last, as we
    # need to mutate the navigation to account for pagination. The main problem
    # is that we need to replace the view in the navigation, because otherwise
    # the view would not be considered active.
    @event_priority(-100)
    def on_page_context(self, context, *, page, config, nav):
        if not self.config.enabled:
            return

        # Skip if page is not a view managed by this instance - this plugin has
        # support for multiple instances, which is why this check is necessary
        view = self._resolve_original(page)
        if view not in self._resolve_views(self.blog):
            return

        # Render excerpts and prepare pagination
        posts, pagination = self._render(page)

        # Render pagination links
        def pager(args: object):
            return pagination.pager(
                format = self.config.pagination_format,
                show_if_single_page = self.config.pagination_if_single_page,
                **args
            )

        # Assign posts and pagination to context
        context["posts"]      = posts
        context["pagination"] = pager if pagination else None

    # Remove temporary directory on shutdown
    def on_shutdown(self):
        rmtree(self.temp_dir)

    # -------------------------------------------------------------------------

    # Check if the given post is excluded
    def _is_excluded(self, post: Post):
        if self.config.draft:
            return False

        # If a post was not explicitly marked or unmarked as draft, and the
        # date should be taken into account, we automatically mark it as draft
        # if the publishing date is in the future. This, of course, is opt-in
        # and must be explicitly enabled by the author.
        if not isinstance(post.config.draft, bool):
            if self.config.draft_if_future_date:
                return post.config.date.created > datetime.now(timezone.utc)

        # Post might be a draft
        return bool(post.config.draft)

    # -------------------------------------------------------------------------

    # Resolve entrypoint - the entrypoint of the blog must have been created
    # if it did not exist before, and hosts all posts sorted by descending date
    def _resolve(self, files: Files, config: DocsForgeConfig):
        path = os.path.join(self.config.blog_dir, "index.md")
        path = os.path.normpath(path)

        # Create entrypoint, if it does not exist - note that the entrypoint is
        # created in the docs directory, not in the temporary directory
        docs = os.path.relpath(config.docs_dir)
        name = os.path.join(docs, path)
        if not os.path.isfile(name):
            file = self._path_to_file(path, config, temp = False)
            files.append(file)

            # Create file in docs directory
            self._save_to_file(file.abs_src_path, "# Blog\n\n")

        # Create and return entrypoint
        file = files.get_file_from_path(path)
        return View(None, file, config)

    # Resolve post - the caller must make sure that the given file points to an
    # actual post (and not a page), or behavior might be unpredictable
    def _resolve_post(self, file: File, config: DocsForgeConfig):
        post = Post(file, config)

        # Compute path and create a temporary file for path resolution
        path = self._format_path_for_post(post, config)
        temp = self._path_to_file(path, config, temp = False)

        # Replace destination file system path and URL
        file.dest_uri      = temp.dest_uri
        file.abs_dest_path = temp.abs_dest_path
        file.url           = temp.url

        # Replace canonical URL and return post
        post._set_canonical_url(config.site_url)
        return post

    # Resolve posts from directory - traverse all documentation pages and filter
    # and yield those that are located in the posts directory
    def _resolve_posts(self, files: Files, config: DocsForgeConfig):
        path = self.config.post_dir.format(blog = self.config.blog_dir)
        path = os.path.normpath(path)

        # Create posts directory, if it does not exist
        docs = os.path.relpath(config.docs_dir)
        name = os.path.join(docs, path)
        if not os.path.isdir(name):
            os.makedirs(name, exist_ok = True)

        # Filter posts from pages
        for file in files.documentation_pages():
            if not file.src_path.startswith(path):
                continue

            # Temporarily remove post from navigation
            file.inclusion = InclusionLevel.EXCLUDED

            # Resolve post - in order to determine whether a post should be
            # excluded, we must load it and analyze its metadata. All posts
            # marked as drafts are excluded, except for when the author has
            # configured drafts to be included in the navigation.
            post = self._resolve_post(file, config)
            if not self._is_excluded(post):
                yield post

    # Resolve authors - check if there's an authors file at the configured
    # location, and if one was found, load and validate it
    def _resolve_authors(self, config: DocsForgeConfig):
        path = self.config.authors_file.format(blog = self.config.blog_dir)
        path = os.path.normpath(path)

        # Resolve path relative to docs directory
        docs = os.path.relpath(config.docs_dir)
        file = os.path.join(docs, path)

        # If the authors file does not exist, return here
        config: Authors = Authors()
        if not os.path.isfile(file):
            return config.authors

        # Open file and parse as YAML
        with open(file, encoding = "utf-8-sig") as f:
            config.config_file_path = os.path.abspath(file)
            try:
                config.load_dict(yaml.load(f, SafeLoader) or {})

            # The authors file could not be loaded because of a syntax error,
            # which we display to the author with a nice error message
            except Exception as e:
                raise PluginError(
                    f"Error reading authors file '{path}' in '{docs}':\n"
                    f"{e}"
                )

        # Validate authors and throw if errors occurred
        errors, warnings = config.validate()
        for _, w in warnings:
            log.warning(w)
        for _, e in errors:
            raise PluginError(
                f"Error reading authors file '{path}' in '{docs}':\n"
                f"{e}"
            )

        # Return authors
        return config.authors

    # Resolve views of the given view in pre-order
    def _resolve_views(self, view: View):
        yield view

        # Resolve views recursively
        for page in view.views:
            for next in self._resolve_views(page):
                assert isinstance(next, View)
                yield next

    # Resolve siblings of a navigation item
    def _resolve_siblings(self, item: StructureItem, nav: Navigation):
        if isinstance(item.parent, Section):
            return item.parent.children
        else:
            return nav.items

    # Resolve original page or view (e.g. for paginated views)
    def _resolve_original(self, page: Page):
        if isinstance(page, View) and page.pages:
            return page.pages[0]
        else:
            return page

    # -------------------------------------------------------------------------

    # Generate views for archive - analyze posts and generate the necessary
    # views, taking the date format provided by the author into account
    def _generate_archive(self, config: DocsForgeConfig, files: Files):
        for post in self.blog.posts:
            date = post.config.date.created

            # Compute name and path of archive view
            name = self._format_date_for_archive(date, config)
            path = self._format_path_for_archive(post, config)

            # Create file for view, if it does not exist
            file = files.get_file_from_path(path)
            if not file:
                file = self._path_to_file(path, config)
                files.append(file)

                # Create file in temporary directory
                self._save_to_file(file.abs_src_path, f"# {name}")

            # Temporarily remove view from navigation
            file.inclusion = InclusionLevel.EXCLUDED

            # Create and yield view
            if not isinstance(file.page, Archive):
                yield Archive(name, file, config)

            # Assign post to archive
            assert isinstance(file.page, Archive)
            file.page.posts.append(post)

    # Generate views for categories - analyze posts and generate the necessary
    # views, taking the allowed categories as set by the author into account
    def _generate_categories(self, config: DocsForgeConfig, files: Files):
        for post in self.blog.posts:
            for name in post.config.categories:
                path = self._format_path_for_category(name)

                # Ensure category is in non-empty allow list
                categories = self.config.categories_allowed or [name]
                if name not in categories:
                    docs = os.path.relpath(config.docs_dir)
                    path = os.path.relpath(post.file.abs_src_path, docs)
                    raise PluginError(
                        f"Error reading categories of post '{path}' in "
                        f"'{docs}': category '{name}' not in allow list"
                    )

                # Create file for view, if it does not exist
                file = files.get_file_from_path(path)
                if not file:
                    file = self._path_to_file(path, config)
                    files.append(file)

                    # Create file in temporary directory
                    self._save_to_file(file.abs_src_path, f"# {name}")

                # Temporarily remove view from navigation
                file.inclusion = InclusionLevel.EXCLUDED

                # Create and yield view
                if not isinstance(file.page, Category):
                    yield Category(name, file, config)

                # Assign post to category and vice versa
                assert isinstance(file.page, Category)
                file.page.posts.append(post)
                post.categories.append(file.page)

    # Generate views for profiles - analyze posts and generate the necessary
    # views to provide a profile page for each author listing all posts
    def _generate_profiles(self, config: DocsForgeConfig, files: Files):
        for post in self.blog.posts:
            for id in post.config.authors:
                author = self.authors[id]
                path = self._format_path_for_profile(id, author)

                # Create file for view, if it does not exist
                file = files.get_file_from_path(path)
                if not file:
                    file = self._path_to_file(path, config)
                    files.append(file)

                    # Create file in temporary directory
                    self._save_to_file(file.abs_src_path, f"# {author.name}")

                # Temporarily remove view from navigation and assign profile
                # URL to author, if not explicitly set
                file.inclusion = InclusionLevel.EXCLUDED
                if not author.url:
                    author.url = file.url

                # Create and yield view
                if not isinstance(file.page, Profile):
                    yield Profile(author.name, file, config)

                # Assign post to profile
                assert isinstance(file.page, Profile)
                file.page.posts.append(post)

    # Generate pages for pagination - analyze view and generate the necessary
    # pages, creating a chain of views for simple rendering and replacement
    def _generate_pages(self, view: View, config: DocsForgeConfig, files: Files):
        yield view

        # Compute pagination boundaries and create pages - pages are internally
        # handled as copies of a view, as they map to the same source location
        step = self._config_pagination_per_page(view)
        for at in range(step, len(view.posts), step):
            path = self._format_path_for_pagination(view, 1 + at // step)

            # Create file for view, if it does not exist
            file = files.get_file_from_path(path)
            if not file:
                file = self._path_to_file(path, config)
                files.append(file)

                # Copy file to temporary directory
                copy_file(view.file.abs_src_path, file.abs_src_path)

            # Temporarily remove view from navigation
            file.inclusion = InclusionLevel.EXCLUDED

            # Create and yield view
            if not isinstance(file.page, View):
                yield view.__class__(None, file, config)

            # Assign pages and posts to view
            assert isinstance(file.page, View)
            file.page.pages = view.pages
            file.page.posts = view.posts

    # Generate links from the given post to other posts, pages, and sections -
    # this can only be done once all posts and pages have been parsed
    def _generate_links(self, post: Post, config: DocsForgeConfig, files: Files):
        if not post.config.links:
            return

        # Resolve path relative to docs directory for error reporting
        docs = os.path.relpath(config.docs_dir)
        path = os.path.relpath(post.file.abs_src_path, docs)

        # Find all links to pages and replace them with references - while all
        # internal links are processed, external links remain as they are
        for link in _find_links(post.config.links.items):
            url = urlparse(link.url)
            if url.scheme:
                continue

            # Resolve file for link, and throw if the file could not be found -
            # authors can link to other pages, as well as to assets or files of
            # any kind, but it is essential that the file that is linked to is
            # found, so errors are actually catched and reported
            file = files.get_file_from_path(url.path)
            if not file:
                log.warning(
                    f"Error reading metadata of post '{path}' in '{docs}':\n"
                    f"Couldn't find file for link '{url.path}'"
                )
                continue

            # If the file linked to is not a page, but an asset or any other
            # file, we resolve the destination URL and continue
            if not isinstance(file.page, Page):
                link.url = file.url
                continue

            # Cast link to reference
            link.__class__ = Reference
            assert isinstance(link, Reference)

            # Assign page title, URL and metadata to link
            link.title = link.title or file.page.title
            link.url   = file.page.url
            link.meta  = copy(file.page.meta)

            # If the link has no fragment, we can continue - if it does, we
            # need to find the matching anchor in the table of contents
            if not url.fragment:
                continue

            # If we're running under dirty reload, MkDocs will reset all pages,
            # so it's not possible to resolve anchor links. Thus, the only way
            # to make this work is to skip the entire process of anchor link
            # resolution in case of a dirty reload.
            if self.is_dirty:
                continue

            # Resolve anchor for fragment, and throw if the anchor could not be
            # found - authors can link to any anchor in the table of contents
            anchor = _find_anchor(file.page.toc, url.fragment)
            if not anchor:
                log.warning(
                    f"Error reading metadata of post '{path}' in '{docs}':\n"
                    f"Couldn't find anchor '{url.fragment}' in '{url.path}'"
                )

                # Restore link to original state
                link.url = url.geturl()
                continue

            # Append anchor to URL and set subtitle
            link.url += f"#{anchor.id}"
            link.meta["subtitle"] = anchor.title

    # -------------------------------------------------------------------------

    # Attach a list of pages to each other and to the given parent item without
    # explicitly adding them to the navigation, which can be done by the caller
    def _attach(self, parent: StructureItem, pages: list[Page]):
        for tail, page, head in zip(pages, pages[1:], pages[2:]):

            # Link page to parent and siblings
            page.parent        = parent
            page.previous_page = tail
            page.next_page     = head

            # If the page is a view, we know that we generated it and need to
            # link its siblings back to the view
            if isinstance(page, View):
                view = self._resolve_original(page)
                if tail: tail.next_page     = view
                if head: head.previous_page = view

    # Attach a page to the given parent and link it to the previous and next
    # page of the given host - this is exclusively used for paginated views
    def _attach_at(self, parent: StructureItem, host: Page, page: Page):
        self._attach(parent, [host.previous_page, page, host.next_page])

    # Attach a section as a sibling to the given view, make sure its pages are
    # part of the navigation, and ensure all pages are linked correctly
    def _attach_to(self, view: View, section: Section, nav: Navigation):
        section.parent = view.parent

        # Resolve siblings, which are the children of the parent section, or
        # the top-level list of navigation items if the view is at the root of
        # the project, and append the given section to it. It's currently not
        # possible to chose the position of a section.
        items = self._resolve_siblings(view, nav)
        items.append(section)

        # Find last sibling that is a page, skipping sections, as we need to
        # append the given section after all other pages
        tail = next(item for item in reversed(items) if isinstance(item, Page))
        head = tail.next_page

        # Attach section to navigation and pages to each other
        nav.pages.extend(section.children)
        self._attach(section, [tail, *section.children, head])

    # -------------------------------------------------------------------------

    # Render excerpts and pagination for the given view
    def _render(self, view: View):
        posts, pagination = view.posts, None

        # Create pagination, if enabled
        if self._config_pagination(view):
            at = view.pages.index(view)

            # Compute pagination boundaries
            step = self._config_pagination_per_page(view)
            p, q = at * step, at * step + step

            # Extract posts in pagination boundaries
            posts = view.posts[p:q]
            pagination = self._render_pagination(view, (p, q))

        # Render excerpts for selected posts
        posts = [
            self._render_post(post.excerpt, view)
                for post in posts if post.excerpt
        ]

        # Return posts and pagination
        return posts, pagination

    # Render excerpt in the context of the given view
    def _render_post(self, excerpt: Excerpt, view: View):
        excerpt.render(view, self.config.post_excerpt_separator)

        # Attach top-level table of contents item to view if it should be added
        # and both, the view and excerpt contain table of contents items
        toc = self._config_toc(view)
        if toc and excerpt.toc.items and view.toc.items:
            view.toc.items[0].children.append(excerpt.toc.items[0])

        # Return excerpt
        return excerpt

    # Create pagination for the given view and range
    def _render_pagination(self, view: View, range: tuple[int, int]):
        p, q = range

        # Create URL from the given page to another page
        def url_maker(n: int):
            return get_relative_url(view.pages[n - 1].url, view.url)

        # Return pagination
        return Pagination(
            view.posts, page = q // (q - p),
            items_per_page = q - p,
            url_maker = url_maker
        )

    # -------------------------------------------------------------------------

    # Retrieve configuration value or return default
    def _config(self, key: str, default: any):
        return default if self.config[key] is None else self.config[key]

    # Retrieve configuration value for table of contents
    def _config_toc(self, view: View):
        default = self.config.blog_toc
        if isinstance(view, Archive):
            return self._config("archive_toc", default)
        if isinstance(view, Category):
            return self._config("categories_toc", default)
        if isinstance(view, Profile):
            return self._config("authors_profiles_toc", default)
        else:
            return default

    # Retrieve configuration value for pagination
    def _config_pagination(self, view: View):
        default = self.config.pagination
        if isinstance(view, Archive):
            return self._config("archive_pagination", default)
        if isinstance(view, Category):
            return self._config("categories_pagination", default)
        if isinstance(view, Profile):
            return self._config("authors_profiles_pagination", default)
        else:
            return default

    # Retrieve configuration value for pagination per page
    def _config_pagination_per_page(self, view: View):
        default = self.config.pagination_per_page
        if isinstance(view, Archive):
            return self._config("archive_pagination_per_page", default)
        if isinstance(view, Category):
            return self._config("categories_pagination_per_page", default)
        if isinstance(view, Profile):
            return self._config("authors_profiles_pagination_per_page", default)
        else:
            return default

    # -------------------------------------------------------------------------

    # Format path for post
    def _format_path_for_post(self, post: Post, config: DocsForgeConfig):
        categories = post.config.categories[:self.config.post_url_max_categories]
        categories = [self._slugify_category(name) for name in categories]

        # Replace placeholders in format string
        date = post.config.date.created
        path = self.config.post_url_format.format(
            categories = "/".join(categories),
            date = self._format_date_for_post_url(date, config),
            file = post.file.name,
            slug = post.config.slug or self._slugify_post(post)
        )

        # Normalize path and strip slashes at the beginning and end
        path = posixpath.normpath(path.strip("/"))
        return posixpath.join(self.config.blog_dir, f"{path}.md")

    # Format path for archive
    def _format_path_for_archive(self, post: Post, config: DocsForgeConfig):
        date = post.config.date.created
        path = self.config.archive_url_format.format(
            date = self._format_date_for_archive_url(date, config)
        )

        # Normalize path and strip slashes at the beginning and end
        path = posixpath.normpath(path.strip("/"))
        return posixpath.join(self.config.blog_dir, f"{path}.md")

    # Format path for category
    def _format_path_for_category(self, name: str):
        path = self.config.categories_url_format.format(
            slug = self._slugify_category(name)
        )

        # Normalize path and strip slashes at the beginning and end
        path = posixpath.normpath(path.strip("/"))
        return posixpath.join(self.config.blog_dir, f"{path}.md")

    # Format path for profile
    def _format_path_for_profile(self, id: str, author: Author):
        path = self.config.authors_profiles_url_format.format(
            slug = author.slug or id,
            name = author.name
        )

        # Normalize path and strip slashes at the beginning and end
        path = posixpath.normpath(path.strip("/"))
        return posixpath.join(self.config.blog_dir, f"{path}.md")

    # Format path for pagination
    def _format_path_for_pagination(self, view: View, page: int):
        path = self.config.pagination_url_format.format(
            page = page
        )

        # Compute base path for pagination - if the given view is an index file,
        # we need to pop the file name from the base so it's not part of the URL
        # and we need to append `index` to the path, so the paginated view is
        # also an index page - see https://t.ly/71MKF
        base, _ = posixpath.splitext(view.file.src_uri)
        if view.is_index:
            base = posixpath.dirname(base)
            path = posixpath.join(path, "index")

        # Normalize path and strip slashes at the beginning and end
        path = posixpath.normpath(path.strip("/"))
        return posixpath.join(base, f"{path}.md")

    # -------------------------------------------------------------------------

    # Format date - if the given format string refers to a predefined format,
    # we format the date without a time component in order to keep sane default
    # behavior, since authors will not expect time to be relevant for most posts
    # as by our assumptions - see https://t.ly/Yi7ZC
    def _format_date(self, date: datetime, format: str, config: DocsForgeConfig):
        locale: str = config.theme["language"].replace("-", "_")
        if format in ["full", "long", "medium", "short"]:
            return format_date(date, format = format, locale = locale)
        else:
            return format_datetime(date, format = format, locale = locale)

    # Format date for post
    def _format_date_for_post(self, date: datetime, config: DocsForgeConfig):
        format = self.config.post_date_format
        return self._format_date(date, format, config)

    # Format date for post URL
    def _format_date_for_post_url(self, date: datetime, config: DocsForgeConfig):
        format = self.config.post_url_date_format
        return self._format_date(date, format, config)

    # Format date for archive
    def _format_date_for_archive(self, date: datetime, config: DocsForgeConfig):
        format = self.config.archive_date_format
        return self._format_date(date, format, config)

    # Format date for archive URL
    def _format_date_for_archive_url(self, date: datetime, config: DocsForgeConfig):
        format = self.config.archive_url_date_format
        return self._format_date(date, format, config)

    # -------------------------------------------------------------------------

    # Slugify post title
    def _slugify_post(self, post: Post):
        separator = self.config.post_slugify_separator
        return self.config.post_slugify(post.title, separator)

    # Slugify category
    def _slugify_category(self, name: str):
        separator = self.config.categories_slugify_separator
        return self.config.categories_slugify(name, separator)

    # -------------------------------------------------------------------------

    # Create a file for the given path, which must point to a valid source file,
    # either inside the temporary directory or the docs directory
    def _path_to_file(self, path: str, config: DocsForgeConfig, *, temp = True):
        assert path.endswith(".md")
        file = File(
            path,
            config.docs_dir if not temp else self.temp_dir,
            config.site_dir,
            config.use_directory_urls
        )

        # Hack: mark file as generated, so other plugins don't think it's part
        # of the file system. This is more or less a new quasi-standard that
        # still needs to be adopted by MkDocs, and was introduced by the
        # git-revision-date-localized-plugin - see https://bit.ly/3ZUmdBx
        if temp:
            file.generated_by = "material/blog"

        # Return file
        return file

    # Create a file with the given content on disk
    def _save_to_file(self, path: str, content: str):
        os.makedirs(os.path.dirname(path), exist_ok = True)
        with open(path, "w", encoding = "utf-8") as f:
            f.write(content)

    # -------------------------------------------------------------------------

    # Translate the placeholder referenced by the given key
    def _translate(self, key: str, config: DocsForgeConfig) -> str:
        env = config.theme.get_env()
        template = env.get_template(
            "partials/language.html", globals = { "config": config }
        )

        # Translate placeholder
        return template.module.t(key)

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------

# Find all links in the given list of items
def _find_links(items: list[StructureItem]):
    for item in items:

        # Resolve link
        if isinstance(item, Link):
            yield item

        # Resolve sections recursively
        if isinstance(item, Section):
            for item in _find_links(item.children):
                assert isinstance(item, Link)
                yield item

# Find anchor in table of contents for the given id
def _find_anchor(toc: TableOfContents, id: str):
    for anchor in toc:
        if anchor.id == id:
            return anchor

        # Resolve anchors recursively
        anchor = _find_anchor(anchor.children, id)
        if isinstance(anchor, AnchorLink):
            return anchor

# -----------------------------------------------------------------------------
# Data
# -----------------------------------------------------------------------------

# Set up logging
log = logging.getLogger("mkdocs.material.blog")


#-----------------------------------------------------------------------------
# From __init__.py
#-----------------------------------------------------------------------------

