from __future__ import annotations

import enum
import logging
import posixpath
import re
import threading
import warnings
from collections import OrderedDict
from collections.abc import Callable, Iterator, MutableMapping, Sequence
from typing import TYPE_CHECKING, Any
from urllib.parse import unquote as urlunquote
from urllib.parse import urljoin, urlsplit, urlunsplit

import markdown
import markdown.htmlparser
import markdown.treeprocessors
from markdown.util import AMP_SUBSTITUTE

from docsforge import utils
from docsforge.structure import StructureItem
from docsforge.toc import get_toc
from docsforge.utils import weak_property
from docsforge.utils import get_build_date, get_markdown_title
from docsforge import meta
from docsforge.rendering import get_heading_text

if TYPE_CHECKING:
    from xml.etree import ElementTree as etree

    from docsforge.config_defaults import DocsForgeConfig
    from docsforge.files import File, Files
    from docsforge.toc import TableOfContents


log = logging.getLogger(__name__)


# Module-level cache for Markdown instances per thread
# Each thread gets its own instance to avoid conflicts in parallel builds.
_md_thread_local = threading.local()

# Maximum number of distinct Markdown configurations to keep cached per thread.
_MAX_MD_CACHE_SIZE = 10


def _get_markdown_instance(extensions: list[str], extension_configs: dict) -> markdown.Markdown:
    """Get or create a cached Markdown instance for this thread.

    The instance is reset between uses, and extensions are initialized only once
    per thread, avoiding the expensive re-initialization on every page render.
    The cache is bounded to prevent unbounded growth across many configurations.
    """
    # Create a cache key from the extensions and configs
    ext_key = tuple(extensions)
    # Convert nested dicts to nested tuples for hashability
    def _freeze(obj):
        if isinstance(obj, dict):
            return tuple(sorted((k, _freeze(v)) for k, v in obj.items()))
        if isinstance(obj, list):
            return tuple(_freeze(v) for v in obj)
        return obj
    cfg_key = _freeze(extension_configs)
    cache_key = (ext_key, cfg_key)

    if not hasattr(_md_thread_local, 'instances'):
        _md_thread_local.instances = OrderedDict()

    md = _md_thread_local.instances.get(cache_key)
    if md is None:
        md = markdown.Markdown(extensions=extensions, extension_configs=extension_configs)
        _md_thread_local.instances[cache_key] = md
        if len(_md_thread_local.instances) > _MAX_MD_CACHE_SIZE:
            _md_thread_local.instances.popitem(last=False)
    else:
        _md_thread_local.instances.move_to_end(cache_key)
        md.reset()

    return md


class Page(StructureItem):
    def __init__(self, title: str | None, file: File, config: DocsForgeConfig) -> None:
        super().__init__()
        file.page = self
        self.file = file
        if title is not None:
            self.title = title

        # i18n titles from explicit nav configuration, keyed by locale.
        self.i18n_titles: dict[str, str] = {}

        # Navigation attributes
        self.children = None
        self.previous_page = None
        self.next_page = None
        self.active = False

        self.update_date: str = get_build_date()

        self._set_canonical_url(config.get('site_url', None))
        self._set_edit_url(
            config.get('repo_url', None), config.get('edit_uri'), config.get('edit_uri_template')
        )

        # Placeholders to be filled in later in the build process.
        self.markdown = None
        self._title_from_render: str | None = None
        self.content = None
        self.toc = []  # type: ignore[assignment]
        self.meta = {}

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.title == other.title
            and self.file == other.file
        )

    def __repr__(self):
        name = self.__class__.__name__
        title = f"{self.title!r}" if self.title is not None else '[blank]'
        url = self.abs_url or self.file.url
        return f"{name}(title={title}, url={url!r})"

    markdown: str | None
    """The original Markdown content from the file."""

    content: str | None
    """The rendered Markdown as HTML, this is the contents of the documentation.

    Populated after `.render()`."""

    toc: TableOfContents
    """An iterable object representing the Table of contents for a page. Each item in
    the `toc` is an [`AnchorLink`][docsforge.structure.toc.AnchorLink]."""

    meta: MutableMapping[str, Any]
    """A mapping of the metadata included at the top of the markdown page."""

    @property
    def url(self) -> str:
        """The URL of the page relative to the DocsForge `site_dir`."""
        url = self.file.url
        if url in ('.', './'):
            return ''
        return url

    file: File
    """The documentation [`File`][docsforge.structure.files.File] that the page is being rendered from."""

    abs_url: str | None
    """The absolute URL of the page from the server root as determined by the value
    assigned to the [site_url][] configuration setting. The value includes any
    subdirectory included in the `site_url`, but not the domain. [base_url][] should
    not be used with this variable."""

    canonical_url: str | None
    """The full, canonical URL to the current page as determined by the value assigned
    to the [site_url][] configuration setting. The value includes the domain and any
    subdirectory included in the `site_url`. [base_url][] should not be used with this
    variable."""

    @property
    def active(self) -> bool:
        """When `True`, indicates that this page is the currently viewed page. Defaults to `False`."""
        return self.__active

    @active.setter
    def active(self, value: bool):
        """Set active status of page and ancestors."""
        self.__active = bool(value)
        if self.parent is not None:
            self.parent.active = bool(value)

    @property
    def is_index(self) -> bool:
        return self.file.name == 'index'

    edit_url: str | None
    """The full URL to the source page in the source repository. Typically used to
    provide a link to edit the source page. [base_url][] should not be used with this
    variable."""

    @property
    def is_homepage(self) -> bool:
        """Evaluates to `True` for the homepage of the site and `False` for all other pages."""
        return self.is_top_level and self.is_index and self.file.url in ('.', './', 'index.html')

    previous_page: Page | None
    """The [page][docsforge.structure.pages.Page] object for the previous page or `None`.
    The value will be `None` if the current page is the first item in the site navigation
    or if the current page is not included in the navigation at all."""

    next_page: Page | None
    """The [page][docsforge.structure.pages.Page] object for the next page or `None`.
    The value will be `None` if the current page is the last item in the site navigation
    or if the current page is not included in the navigation at all."""

    children: None = None
    """Pages do not contain children and the attribute is always `None`."""

    is_section: bool = False
    """Indicates that the navigation object is a "section" object. Always `False` for page objects."""

    is_page: bool = True
    """Indicates that the navigation object is a "page" object. Always `True` for page objects."""

    is_link: bool = False
    """Indicates that the navigation object is a "link" object. Always `False` for page objects."""

    def _set_canonical_url(self, base: str | None) -> None:
        if base:
            if not base.endswith('/'):
                base += '/'
            self.canonical_url = canonical_url = urljoin(base, self.url)
            self.abs_url = urlsplit(canonical_url).path
        else:
            self.canonical_url = None
            self.abs_url = None

    def _set_edit_url(
        self,
        repo_url: str | None,
        edit_uri: str | None = None,
        edit_uri_template: str | None = None,
    ) -> None:
        if not edit_uri_template and not edit_uri:
            self.edit_url = None
            return
        src_uri = self.file.edit_uri
        if src_uri is None:
            self.edit_url = None
            return

        if edit_uri_template:
            noext = posixpath.splitext(src_uri)[0]
            file_edit_uri = edit_uri_template.format(path=src_uri, path_noext=noext)
        else:
            if edit_uri is None or not edit_uri.endswith('/'):
                raise ValueError(
                    f"edit_uri must be a string ending with '/', got {edit_uri!r}"
                )
            file_edit_uri = edit_uri + src_uri

        if repo_url:
            # Ensure urljoin behavior is correct
            if not file_edit_uri.startswith(('?', '#')) and not repo_url.endswith('/'):
                repo_url += '/'
        else:
            try:
                parsed_url = urlsplit(file_edit_uri)
                if not parsed_url.scheme or not parsed_url.netloc:
                    log.warning(
                        f"edit_uri: {file_edit_uri!r} is not a valid URL, it should include the http:// (scheme)"
                    )
            except ValueError as e:
                log.warning(f"edit_uri: {file_edit_uri!r} is not a valid URL: {e}")

        self.edit_url = urljoin(repo_url or '', file_edit_uri)

    def read_source(self, config: DocsForgeConfig) -> None:
        source = config.plugins.on_page_read_source(page=self, config=config)
        if source is None:
            try:
                source = self.file.content_string
            except OSError:
                log.error(f'File not found: {self.file.src_path}')
                raise
            except ValueError:
                log.error(f'Encoding error reading file: {self.file.src_path}')
                raise

        self.markdown, self.meta = meta.get_data(source)

    @weak_property
    def title(self) -> str | None:  # type: ignore[override]
        """
        Returns the title for the current page.

        Before calling `read_source()`, this value is empty. It can also be updated by `render()`.

        Checks these in order and uses the first that returns a valid title:

        - value provided on init (passed in from config)
        - value of metadata 'title'
        - content of the first H1 in Markdown content
        - convert filename to title
        """
        if self.markdown is None:
            return None

        if 'title' in self.meta:
            return self.meta['title']

        if self._title_from_render:
            return self._title_from_render
        elif self.content is None:  # Preserve legacy behavior only for edge cases in plugins.
            title_from_md = get_markdown_title(self.markdown)
            if title_from_md is not None:
                return title_from_md

        if self.is_homepage:
            return 'Home'

        title = self.file.name.replace('-', ' ').replace('_', ' ')
        # Capitalize if the filename was all lowercase, otherwise leave it as-is.
        if title.lower() == title:
            title = title.capitalize()
        return title

    def render(self, config: DocsForgeConfig, files: Files) -> None:
        """Convert the Markdown source file to HTML as per the config."""
        if self.markdown is None:
            raise RuntimeError("`markdown` field hasn't been set (via `read_source`)")

        mdx_configs = dict(config['mdx_configs'] or {})

        # Use cached Markdown instance for this thread to avoid re-initializing extensions
        md = _get_markdown_instance(config['markdown_extensions'], mdx_configs)

        raw_html_ext = _RawHTMLPreprocessor()
        raw_html_ext._register(md)

        extract_anchors_ext = _ExtractAnchorsTreeprocessor(self.file, files, config)
        extract_anchors_ext._register(md)

        relative_path_ext = _RelativePathTreeprocessor(self.file, files, config)
        relative_path_ext._register(md)

        extract_title_ext = _ExtractTitleTreeprocessor()
        extract_title_ext._register(md)

        self.content = md.convert(self.markdown)
        self.toc = get_toc(getattr(md, 'toc_tokens', []))
        self._title_from_render = extract_title_ext.title
        self.present_anchor_ids = (
            extract_anchors_ext.present_anchor_ids | raw_html_ext.present_anchor_ids
        )
        self.links_to_anchors = relative_path_ext.links_to_anchors

    present_anchor_ids: set[str] | None = None
    """Anchor IDs that this page contains (can be linked to in this page)."""

    links_to_anchors: dict[File, dict[str, str]] | None = None
    """Resolved relative links with anchors, keyed by target file."""

    link_warnings: list[tuple[int, str]] = []
    """Link validation warnings (level, message), collected during render so
    they can be re-emitted on incremental builds for pages that are not
    re-rendered."""
    """Links to anchors in other files that this page contains.

    The structure is: `{file_that_is_linked_to: {'anchor': 'original_link/to/some_file.md#anchor'}}`.
    Populated after `.render()`.
    """

    def validate_anchor_links(self, *, files: Files, log_level: int) -> None:
        if not self.links_to_anchors:
            return
        existing = {msg for _, msg in self.link_warnings}
        for to_file, links in self.links_to_anchors.items():
            for anchor, original_link in links.items():
                page = to_file.page
                if page is None:
                    continue
                if page.present_anchor_ids is None:  # Page was somehow not rendered.
                    continue
                if anchor in page.present_anchor_ids:
                    continue
                context = ""
                if to_file == self.file:
                    problem = "there is no such anchor on this page"
                    if anchor.startswith('fnref:'):
                        context = " This seems to be a footnote that is never referenced."
                else:
                    problem = f"the doc '{to_file.src_uri}' does not contain an anchor '#{anchor}'"
                message = (
                    f"Doc file '{self.file.src_uri}' contains a link '{original_link}', "
                    f"but {problem}.{context}"
                )
                # Collect instead of logging inline so the problems persist to
                # validation.json (consumed by the VS Code extension) and are
                # re-emitted on incremental builds for pages not re-rendered.
                # Dedupe against warnings restored from the build cache.
                if message not in existing:
                    self.link_warnings.append((log_level, message))
                    existing.add(message)


class _ExtractAnchorsTreeprocessor(markdown.treeprocessors.Treeprocessor):
    def __init__(self, file: File, files: Files, config: DocsForgeConfig) -> None:
        self.present_anchor_ids: set[str] = set()

    def run(self, root: etree.Element) -> None:
        add = self.present_anchor_ids.add
        for element in root.iter():
            if anchor := element.get('id'):
                add(anchor)
            if element.tag == 'a':
                if anchor := element.get('name'):
                    add(anchor)

    def _register(self, md: markdown.Markdown) -> None:
        md.treeprocessors.register(self, "docsforge_extract_anchors", priority=5)  # Same as 'toc'.


class _RelativePathTreeprocessor(markdown.treeprocessors.Treeprocessor):
    def __init__(self, file: File, files: Files, config: DocsForgeConfig) -> None:
        self.file = file
        self.files = files
        self.config = config
        self.links_to_anchors: dict[File, dict[str, str]] = {}

    def run(self, root: etree.Element) -> etree.Element:
        """
        Update urls on anchors and images to make them relative.

        Iterates through the full document tree looking for specific
        tags and then makes them relative based on the site navigation
        """
        for element in root.iter():
            if element.tag == 'a':
                key = 'href'
            elif element.tag == 'img':
                key = 'src'
            else:
                continue

            url = element.get(key)
            if url is None:
                continue
            new_url = self.path_to_url(url)
            element.set(key, new_url)

        return root

    @classmethod
    def _target_uri(cls, src_path: str, dest_path: str) -> str:
        return posixpath.normpath(
            posixpath.join(posixpath.dirname(src_path), dest_path).lstrip('/')
        )

    @classmethod
    def _possible_target_uris(
        cls, file: File, path: str, use_directory_urls: bool, suggest_absolute: bool = False
    ) -> Iterator[str]:
        """First yields the resolved file uri for the link, then proceeds to yield guesses for possible mistakes."""
        target_uri = cls._target_uri(file.src_uri, path)
        yield target_uri

        if posixpath.normpath(path) == '.':
            # Explicitly link to current file.
            yield file.src_uri
            return
        tried = {target_uri}

        prefixes = [target_uri, cls._target_uri(file.url, path)]
        if prefixes[0] == prefixes[1]:
            prefixes.pop()

        suffixes: list[Callable[[str], str]] = []
        if use_directory_urls:
            suffixes.append(lambda p: p)
        if not posixpath.splitext(target_uri)[-1]:
            suffixes.append(lambda p: posixpath.join(p, 'index.md'))
            suffixes.append(lambda p: posixpath.join(p, 'README.md'))
        if (
            not target_uri.endswith('.')
            and not path.endswith('.md')
            and (use_directory_urls or not path.endswith('/'))
        ):
            suffixes.append(lambda p: p.removesuffix('.html') + '.md')

        for pref in prefixes:
            for suf in suffixes:
                guess = posixpath.normpath(suf(pref))
                if guess not in tried and not guess.startswith('../'):
                    yield guess
                    tried.add(guess)

    def path_to_url(self, url: str) -> str:
        try:
            scheme, netloc, path, query, anchor = urlsplit(url)
        except ValueError:  # Invalid URL, e.g. invalid IPv6.
            log.log(
                self.config.validation.links.unrecognized_links,
                f"Doc file '{self.file.src_uri}' contains an invalid link '{url}', "
                f"it was left as is.",
            )
            return url

        absolute_link = None
        warning_level, warning = 0, ''

        # Ignore URLs unless they are a relative link to a source file.
        if scheme or netloc:  # External link.
            if scheme and scheme.lower() not in ('http', 'https', 'mailto', 'tel'):
                log.log(
                    self.config.validation.links.unrecognized_links,
                    f"Doc file '{self.file.src_uri}' contains a link with unsupported scheme "
                    f"'{url}', it was escaped to prevent unsafe protocol use.",
                )
                # Neutralize dangerous protocols such as javascript: by escaping the colon.
                return url.replace(':', '%3A', 1)
            return url
        elif url.startswith(('/', '\\')):  # Absolute link.
            absolute_link = self.config.validation.links.absolute_links
            if absolute_link is not _AbsoluteLinksValidationValue.RELATIVE_TO_DOCS:
                warning_level = absolute_link
                warning = f"Doc file '{self.file.src_uri}' contains an absolute link '{url}', it was left as is."
        elif AMP_SUBSTITUTE in url:  # AMP_SUBSTITUTE is used internally by Markdown only for email.
            return url
        elif not path:  # Self-link containing only query or anchor.
            if anchor:
                # Register that the page links to itself with an anchor.
                self.links_to_anchors.setdefault(self.file, {}).setdefault(anchor, url)
            return url

        path = urlunquote(path)
        # Determine the filepath of the target.
        possible_target_uris = self._possible_target_uris(
            self.file, path, self.config.use_directory_urls
        )

        if warning:
            # For absolute path (already has a warning), the primary lookup path should be preserved as a tip option.
            target_uri = url
            target_file = None
        else:
            # Validate that the target exists in files collection.
            target_uri = next(possible_target_uris)
            target_file = self.files.get_file_from_path(target_uri)

        if target_file is None and not warning:
            # Primary lookup path had no match, definitely produce a warning, just choose which one.
            if not posixpath.splitext(path)[-1] and absolute_link is None:
                # No '.' in the last part of a path indicates path does not point to a file.
                warning_level = self.config.validation.links.unrecognized_links
                warning = (
                    f"Doc file '{self.file.src_uri}' contains an unrecognized relative link '{url}', "
                    f"it was left as is."
                )
            else:
                target = f" '{target_uri}'" if target_uri != url.lstrip('/') else ""
                warning_level = self.config.validation.links.not_found
                warning = (
                    f"Doc file '{self.file.src_uri}' contains a link '{url}', "
                    f"but the target{target} is not found among documentation files."
                )
            log.debug(f"target_file is None for url={url}, target_uri={target_uri}")
            log.debug(f"warning={warning}")

        if warning:
            if self.file.inclusion.is_excluded():
                warning_level = min(logging.INFO, warning_level)

            # There was no match, so try to guess what other file could've been intended.
            if warning_level > logging.DEBUG:
                suggest_url = ''
                for path in possible_target_uris:
                    if self.files.get_file_from_path(path) is not None:
                        if anchor and path == self.file.src_uri:
                            path = ''
                        elif absolute_link is _AbsoluteLinksValidationValue.RELATIVE_TO_DOCS:
                            path = '/' + path
                        else:
                            path = utils.get_relative_url(self.file.src_uri, path)
                        suggest_url = urlunsplit(('', '', path, query, anchor))
                        break
                else:
                    if '@' in url and '.' in url and '/' not in url:
                        suggest_url = f'mailto:{url}'
                if suggest_url:
                    warning += f" Did you mean '{suggest_url}'?"
            # Collect instead of logging inline so the validation pass can
            # re-emit the same warning on later incremental builds (pages that
            # are not re-rendered keep their warnings in the build cache).
            page = getattr(self.file, "page", None)
            if page is not None:
                page.link_warnings.append((warning_level, warning))
            else:
                log.log(warning_level, warning)
            return url

        assert target_uri is not None
        assert target_file is not None
        if anchor:
            # Register that this page links to the target file with an anchor.
            self.links_to_anchors.setdefault(target_file, {}).setdefault(anchor, url)

        if target_file.inclusion.is_excluded():
            if self.file.inclusion.is_excluded():
                warning_level = logging.DEBUG
            else:
                warning_level = min(logging.INFO, self.config.validation.links.not_found)
            warning = (
                f"Doc file '{self.file.src_uri}' contains a link to "
                f"'{target_uri}' which is excluded from the built site."
            )
            page = getattr(self.file, "page", None)
            if page is not None:
                page.link_warnings.append((warning_level, warning))
            else:
                log.log(warning_level, warning)
        path = utils.get_relative_url(self.file.url, target_file.url)
        return urlunsplit(('', '', path, query, anchor))

    def _register(self, md: markdown.Markdown) -> None:
        md.treeprocessors.register(self, "relpath", 0)


# Inline code spans (`...` or ``...``) may contain literal HTML that must not be
# treated as real HTML/anchors. This regex matches Markdown code spans.
_CODE_SPAN_RE = re.compile(r'(?<!\\)(`+)(.*?)(?<!`)\1(?!`)', re.DOTALL)


def _mask_code_spans(text: str) -> str:
    """Replace Markdown code spans with spaces so HTML inside them is ignored."""
    return _CODE_SPAN_RE.sub(lambda m: ' ' * len(m.group(0)), text)


class _RawHTMLPreprocessor(markdown.preprocessors.Preprocessor):
    def __init__(self) -> None:
        super().__init__()
        self.present_anchor_ids: set[str] = set()

    def run(self, lines: list[str]) -> list[str]:
        parser = _HTMLHandler()
        # Mask code spans before parsing so raw HTML inside them is not extracted.
        parser.feed(_mask_code_spans('\n'.join(lines)))
        parser.close()
        self.present_anchor_ids = parser.present_anchor_ids
        return lines

    def _register(self, md: markdown.Markdown) -> None:
        md.preprocessors.register(
            self,
            "docsforge_raw_html",
            priority=21,  # Right before 'html_block'.
        )


class _HTMLHandler(markdown.htmlparser.htmlparser.HTMLParser):  # type: ignore[name-defined]
    def __init__(self) -> None:
        super().__init__()
        self.present_anchor_ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: Sequence[tuple[str, str]]) -> None:
        for k, v in attrs:
            if k == 'id' or (k == 'name' and tag == 'a'):
                self.present_anchor_ids.add(v)
        return super().handle_starttag(tag, attrs)


class _ExtractTitleTreeprocessor(markdown.treeprocessors.Treeprocessor):
    title: str | None = None
    md: markdown.Markdown

    def run(self, root: etree.Element) -> etree.Element:
        for el in root:
            if el.tag == 'h1':
                self.title = get_heading_text(el, self.md)
                break
        return root

    def _register(self, md: markdown.Markdown) -> None:
        self.md = md
        md.treeprocessors.register(
            self,
            "docsforge_extract_title",
            priority=1,  # Close to the end.
        )


class _AbsoluteLinksValidationValue(enum.IntEnum):
    RELATIVE_TO_DOCS = -1
