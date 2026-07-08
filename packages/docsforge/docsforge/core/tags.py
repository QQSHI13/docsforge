"""Tags plugin - tag-based navigation and filtering."""

from __future__ import annotations

from docsforge import get_relative_url
from docsforge.config_base import BaseConfigOption, Config, ValidationError
from docsforge.config_defaults import DocsForgeConfig
from docsforge.config_options import DictOfItems, Deprecated, Optional, Type
from docsforge.exceptions import PluginError
from docsforge.filter_config import FileFilter, FilterConfig
from docsforge.nav import Link
from docsforge.pages import Page
from docsforge.core.plugin_base import BasePlugin, event_priority
from docsforge.templates import TemplateContext
from docsforge.toc import AnchorLink
from collections.abc import Callable, Iterable, Iterator
from functools import total_ordering
from jinja2 import Environment
from pymdownx.slugs import slugify
from re import Match
from typing import Iterator, Set, Tuple
from urllib.parse import urlparse
import json
import logging
import os
import posixpath
import re
import yaml

# ------------------------------------------------------------------------------
class Mapping:
    """A mapping between an item (page or link) and its tags."""

    def __init__(self, item: Page | Link, tags: Iterable[Tag] | None = None):
        self.page = item
        self.item = item
        self.tags: set[Tag] = set(tags or [])

    @property
    def title(self) -> str:
        return self.page.title or ""

    def __repr__(self):
        return f"Mapping({self.page.url!r})"

# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------

# Return tag name for sorting
def tag_name(tag: Tag, *args):
    return tag.name

# Return casefolded tag name for sorting
def tag_name_casefold(tag: Tag, *args):
    return tag.name.casefold()

# -----------------------------------------------------------------------------

# Return item title for sorting
def item_title(mapping: Mapping):
    # Note that this must be coerced to a string, as the title might be sourced
    # from metadata, which can be of any type - see https://t.ly/1AXyo
    return str(mapping.item.title)

# Return item URL for sorting
def item_url(mapping: Mapping):
    return mapping.item.url


# -------------------------------------------------------------------------
# Classes
# -------------------------------------------------------------------------

@total_ordering
class Tag:
    """
    A tag.

    Tags can be used to categorize pages and group them into a tag structure.
    """

    def __init__(
        self, name: str, *, parent: Tag | None = None, hidden = False
    ):
        self.name = name
        self.parent = parent
        self.hidden = hidden

    def __repr__(self) -> str:
        return f"Tag('{self.name}')"

    def __str__(self) -> str:
        return self.name

    def __hash__(self) -> int:
        return hash(self.name)

    def __iter__(self) -> Iterator[Tag]:
        tag = self
        while tag:
            yield tag
            tag = tag.parent

    def __contains__(self, other: Tag) -> bool:
        assert isinstance(other, Tag)
        return any(tag == other for tag in self)

    def __eq__(self, other: Tag) -> bool:
        assert isinstance(other, Tag)
        return self.name == other.name

    def __lt__(self, other: Tag) -> bool:
        assert isinstance(other, Tag)
        return self.name < other.name

    # -------------------------------------------------------------------------

    name: str
    """The tag name."""

    parent: Tag | None
    """The parent tag."""

    hidden: bool
    """Whether the tag is hidden."""


class TagSet(BaseConfigOption[Set[Tag]]):
    """A set of tags."""

    def __init__(self, allowed = None, *args, **kwargs):
        self._allowed = allowed
        super().__init__(*args, **kwargs)

    @property
    def _repr_fields(self):
        return ("allowed",)

    def run_validation(self, value: object) -> Set[Tag]:
        if not isinstance(value, list):
            raise ValidationError(f"Expected a list of tags, but got: {value}")

        # Enforce allow list, if configured
        if self._allowed is not None:
            for tag in value:
                if tag not in self._allowed:
                    raise ValidationError(
                        f"Tag '{tag}' is not allowed. Allowed tags: {self._allowed}"
                    )

        return set(value)

    def pre_validation(self, config: Config, key_name: str):
        return config.get(key_name, set())

    def post_validation(self, config: Config, key_name: str, value: Set[Tag]):
        return value


# Tags plugin configuration
class TagsConfig(Config):
    enabled = Type(bool, default = True)
    tags = Type(bool, default = True)
    tags_file = Optional(Type(str))
    tags_extra_files = Optional(Type(DictOfItems(Type(list))))
    tags_slugify = Type(Callable, default = slugify())
    tags_hierarchy = Type(bool, default = False)
    tags_hierarchy_separator = Type(str, default = "/")
    tags_allowed = Optional(Type(list))
    tags_name_variable = Type(str, default = "tags")
    listings = Type(bool, default = True)
    listings_tags_template = Type(str, default = "tags.html")
    listings_toc_template = Type(str, default = "toc.html")
    listings_directive = Type(str, default = "material/tags")
    listings_directive_map = Type(dict, default = {
        "tags": "listings_tags_template",
        "toc": "listings_toc_template",
    })
    listings_sort_by = Optional(Type(Callable))
    listings_sort_reverse = Type(bool, default = False)
    listings_tags_sort_by = Type(Callable, default = tag_name)
    listings_tags_sort_reverse = Type(bool, default = False)
    listings_shuffle = Optional(Type(int))
    listings_limit = Optional(Type(int))
    listings_pagination = Type(int, default = 10)
    listings_pagination_keep_content = Type(bool, default = True)
    listings_more = Type(bool, default = True)
    listings_page_separator = Type(str, default = "<!-- more -->")
    shadow = Type(bool, default = False)
    shadow_tags = Optional(Type(list))
    shadow_tags_prefix = Optional(Type(str))
    shadow_tags_suffix = Optional(Type(str))
    shadow_on_serve = Type(bool, default = True)
    shadow_page_limit = Optional(Type(int))
    tags_sort_by = Optional(Type(Callable))
    tags_sort_reverse = Type(bool, default = False)
    tags_slugify_format = Type(str, default = '{slug}')
    tags_slugify_separator = Type(str, default = '-')
    export = Type(bool, default = False)
    export_file = Type(str, default = "tags.json")
    export_json_encoder = Optional(Type(str))
    export_json_indent = Optional(Type(int))
    export_json_sort_keys = Type(bool, default = False)
    export_json_ensure_ascii = Type(bool, default = True)
    export_json_separators = Optional(Type(Tuple[str, str]))
    export_only = Type(bool, default = False)
    filters = Optional(Type(FilterConfig))
    filter_on_serve = Type(bool, default = False)
    filter_on_build = Type(bool, default = True)
    listings_layout = Type(str, default = "default")
    listings_toc = Type(bool, default = True)
    listings_map = Type(dict, default = {})
    sort_by = Deprecated(message = "Use 'listings_sort_by' instead")
    sort_reverse = Deprecated(message = "Use 'listings_sort_reverse' instead")


#-----------------------------------------------------------------------------
# ListingConfig class
#-----------------------------------------------------------------------------

class ListingConfig(Config):
    """Configuration for a single listing instance."""
    shadow = Type(bool, default = False)
    layout = Type(str, default = "default")
    toc = Type(bool, default = True)


#-----------------------------------------------------------------------------
# Listing class
#-----------------------------------------------------------------------------

@total_ordering
class Listing:
    """A listing - a collection of tags with pages."""

    def __init__(self, page, id, config):
        self.page = page
        self.id = id
        self.config = config
        self.tags: dict = {}

    def add(self, mapping, hidden=False):
        """Add a mapping (tag + page) to this listing."""
        for tag in mapping.tags:
            if tag not in self.tags:
                self.tags[tag] = []
            self.tags[tag].append(mapping)

    def __and__(self, mapping):
        """Return tags that are in both this listing and the mapping."""
        return [tag for tag in mapping.tags if tag in self.tags]

    def __contains__(self, tag):
        return tag in self.tags

    def __lt__(self, other):
        return self.id < other.id

    def __eq__(self, other):
        return isinstance(other, Listing) and self.id == other.id

    def __hash__(self):
        return hash(self.id)

    def __iter__(self) -> Iterator[ListingTree]:
        """
        Iterate over the listing trees of this listing.

        Yields:
            The current listing tree.
        """
        return iter(self.tags.values())


#-----------------------------------------------------------------------------
# From tags/structure/listing/manager/__init__.py
#-----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Classes
# -----------------------------------------------------------------------------

class ListingManager:
    """
    A listing manager.

    The listing manager collects all listings from the Markdown of pages, then
    populates them with mappings, and renders them. Furthermore, the listing
    manager allows to obtain tag references for a given mapping, which are
    tags annotated with links to listings.
    """

    def __init__(self, config: TagsConfig, depth: int = 6):
        """
        Initialize the listing manager.

        Arguments:
            config: The configuration.
        """
        self.config = config
        self.data = set()
        self.depth = depth

    def __repr__(self) -> str:
        """
        Return a printable representation of the listing manager.

        Returns:
            Printable representation.
        """
        return _print(self)

    def __iter__(self) -> Iterator[Listing]:
        """
        Iterate over listings.

        Yields:
            The current listing.
        """
        return iter(self.data)

    def __and__(self, mapping: Mapping) -> Iterator[TagReference]:
        """
        Iterate over the tag references for the mapping.

        Arguments:
            mapping: The mapping.

        Yields:
            The current tag reference.
        """
        assert isinstance(mapping, Mapping)

        # Iterate over sorted tags and associate tags with listings - note that
        # we sort the listings for the mapping by closeness, so that the first
        # listing in the list is the closest one to the page or link the
        # mapping is associated with
        listings = self.closest(mapping)
        for tag in self._sort_tags(mapping.tags):
            ref = TagReference(tag)

            # Iterate over listings and add links
            for listing in listings:
                if tag in listing & mapping:
                    value = listing.page.url or "."

                    # Compute URL for link - make sure to remove fragments, as
                    # they may be present in links extracted from remote tags.
                    # Additionally, we need to fallback to `.` if the URL is
                    # empty (= homepage) or the links will be incorrect.
                    url = urlparse(value, allow_fragments = False)
                    url = url._replace(fragment = self._slugify(tag))

                    # Add listing link to tag reference
                    ref.links.append(
                        Link(listing.page.title, url.geturl())
                    )

            # Yield tag reference
            yield ref

    # -------------------------------------------------------------------------

    config: TagsConfig
    """
    The configuration.
    """

    data: set[Listing]
    """
    The listings.
    """

    depth: int
    """
    Table of contents maximum depth.
    """

    # -------------------------------------------------------------------------

    def add(self, page: Page, markdown: str) -> str:
        """
        Add page.

        This method is called by the tags plugin to retrieve all listings of a
        page. It will parse the page's Markdown and add injections points into
        the page's Markdown, which will be replaced by the renderer with the
        actual listing later on.

        Note that this method is intended to be called with the page during the
        `on_page_markdown` event, as it modifies the page's Markdown. Moreover,
        the Markdown must be explicitly passed, as we could otherwise run into
        inconsistencies when other plugins modify the Markdown.

        Arguments:
            page: The page.
            markdown: The page's Markdown.

        Returns:
            The page's Markdown with injection points.
        """
        assert isinstance(markdown, str)

        # Replace callback
        def replace(match: Match) -> str:
            config = self._resolve(page, match.group(2))

            # Compute listing identifier - as the author might include multiple
            # listings on a single page, we must make sure that the identifier
            # is unique, so we use the page source file path and the position
            # of the match within the page as an identifier.
            id = f"{page.file.src_uri}:{match.start()}-{match.end()}"

            # Replace whitespaces in the identifier that we computed, or we
            # can't just prefix it with "#" - see https://t.ly/U_hfp
            id = id.replace(" ", "-")
            self.data.add(Listing(page, id, config))

            # Replace directive with hx headline if listings are enabled, or
            # remove the listing entirely from the page and table of contents
            if self.config.listings:
                return "#" * self.depth + f" {id}/name {{ #{id}/slug }}"
            else:
                return

        # Hack: replace directive with an hx headline to mark the injection
        # point for the anchor links we will generate after parsing all pages.
        # By using an hx headline, we can make sure that the injection point
        # will always be a child of the preceding headline.
        directive = self.config.listings_directive
        return re.sub(
            r"(<!--\s*?{directive}(.*?)\s*-->)".format(directive = directive),
            replace, markdown, flags = re.I | re.M | re.S
        )

    def closest(self, mapping: Mapping) -> list[Listing]:
        """
        Get listings for the mapping ordered by closeness.

        Listings are sorted by closeness to the given page, i.e. the number of
        common path components. This is useful for hierarchical listings, where
        the tags of a page point to the closest listing featuring the tag, with
        the option to show all listings featuring that tag.

        Arguments:
            mapping: The mapping.

        Returns:
            The listings.
        """

        # Retrieve listings featuring tags of mapping
        listings: list[Listing] = []
        for listing in self.data:
            if any(listing & mapping):
                listings.append(listing)

        # Ranking callback
        def rank(listing: Listing) -> int:
            path = posixpath.commonpath([mapping.item.url, listing.page.url])
            return len(path)

        # Return listings ordered by closeness to mapping
        return sorted(listings, key = rank, reverse = True)

    def populate(
        self, listing: Listing, mappings: Iterable[Mapping], renderer: Renderer
    ) -> None:
        """
        Populate listing with tags featured in the mappings.

        Arguments:
            listing: The listing.
            mappings: The mappings.
            renderer: The renderer.
        """
        page = listing.page
        assert isinstance(page.content, str)

        # Add mappings to listing, passing shadow tags configuration
        for mapping in mappings:
            listing.add(mapping, hidden = listing.config.shadow)

        # Sort listings and tags - we can only do this after all mappings have
        # been added to the listing, because the tags inside the mappings do
        # not have a proper order yet, and we need to order them as specified
        # in the listing configuration.
        listing.tags = self._sort_listing_tags(listing.tags)

        # Render tags for listing headlines - the listing configuration allows
        # tp specify a custom layout, so we resolve the template for tags here
        name = f"{listing.config.layout}-tag.html"
        for tree in listing:
            tree.content = renderer.render(page, name, tag = tree.tag)

            # Sort mappings and subtrees of  listing tree
            tree.mappings = self._sort_listing(tree.mappings)
            tree.children = self._sort_listing_tags(tree.children)

        # Replace callback
        def replace(match: Match) -> str:
            hx = match.group()

            # Populate listing with anchor links to tags
            anchors = populate(listing, self._slugify)
            if not anchors:
                return ''

            # Get reference to first tag in listing
            head = next(iter(anchors.values()))

            # Replace hx with actual level of listing and listing ids with
            # placeholders to create a format string for the headline
            hx = re.sub(
                r"<(/?)h{}\b".format(self.depth),
                r"<\g<1>h{}".format(head.level), hx
            )
            hx = re.sub(
                r"{id}\/(\w+)".format(id = listing.id),
                r"{\1}", hx, flags = re.I | re.M
            )

            # Render listing headlines
            for tree in listing:
                tree.content = hx.format(
                    slug = anchors[tree.tag].id,
                    name = tree.content
                )

            # Render listing - the listing configuration allows to specify a
            # custom layout, so we resolve the template for listings here
            name = f"{listing.config.layout}-listing.html"
            return "\n".join([
                renderer.render(page, name, listing = tree)
                    for tree in listing.tags.values()
            ])

        # Hack: replace hx headlines (injection points) we added when parsing
        # the page's Markdown with the actual listing content. Additionally,
        # replace anchor links in the table of contents with the hierarchy
        # generated from mapping over the listing, or remove them.
        page.content = re.sub(
            r"<h{x}[^>]+{id}.*?</h{x}>".format(
                id = f"{listing.id}/slug", x = self.depth
            ),
            replace, page.content, flags = re.I | re.M
        )

    def populate_all(
        self, mappings: Iterable[Mapping], renderer: Renderer
    ) -> None:
        """
        Populate all listings with tags featured in the mappings.

        This method is called by the tags plugin to populate all listings with
        the given mappings. It will also remove the injection points from the
        page's Markdown. Note that this method is intended to be called during
        the `on_env` event, after all pages have been rendered.

        Arguments:
            mappings: The mappings.
            renderer: The renderer.
        """
        for listing in self.data:
            self.populate(listing, mappings, renderer)

    # -------------------------------------------------------------------------

    def _resolve(self, page: Page, args: str) -> ListingConfig:
        """
        Resolve listing configuration.

        Arguments:
            page: The page the listing in embedded in.
            args: The arguments, as parsed from Markdown.

        Returns:
            The listing configuration.
        """
        data = yaml.safe_load(args)
        path = page.file.abs_src_path

        # Try to resolve available listing configuration
        if isinstance(data, str):
            config = self.config.listings_map.get(data, None)
            if not config:
                keys = ", ".join(self.config.listings_map.keys())
                raise PluginError(
                    f"Couldn't find listing configuration: {data}. Available "
                    f"configurations: {keys}"
                )

        # Otherwise, handle inline listing configuration
        else:
            config = ListingConfig(config_file_path = path)
            config.load_dict(data or {})

            # Validate listing configuration
            errors, warnings = config.validate()
            for _, w in warnings:
                path = os.path.relpath(path)
                log.warning(
                    f"Error reading listing configuration in '{path}':\n"
                    f"{w}"
                )
            for _, e in errors:
                path = os.path.relpath(path)
                raise PluginError(
                    f"Error reading listing configuration in '{path}':\n"
                    f"{e}"
                )

        # Inherit shadow tags configuration, unless explicitly set
        if not isinstance(config.shadow, bool):
            config.shadow = self.config.shadow

        # Inherit layout configuration, unless explicitly set
        if not isinstance(config.layout, str):
            config.layout = self.config.listings_layout

        # Inherit table of contents configuration, unless explicitly set
        if not isinstance(config.toc, bool):
            config.toc = self.config.listings_toc

        # Return listing configuration
        return config

    # -------------------------------------------------------------------------

    def _slugify(self, tag: Tag) -> str:
        """
        Slugify tag.

        If the tag hierarchy setting is enabled, the tag is expanded into a
        hierarchy of tags, all of which are then slugified and joined with the
        configured separator. Otherwise, the tag is slugified directly. This is
        necessary to keep the tag hierarchy in the slug.

        Arguments:
            tag: The tag.

        Returns:
            The slug.
        """
        slugify = self.config.tags_slugify
        tags = [tag.name]

        # Compute tag hierarchy, if configured
        hierarchy = self.config.tags_hierarchy_separator
        if self.config.tags_hierarchy:
            tags = tag.name.split(hierarchy)

        # Slugify tag hierarchy and join with separator
        separator = self.config.tags_slugify_separator
        return self.config.tags_slugify_format.format(
            slug = hierarchy.join(slugify(name, separator) for name in tags)
        )

    # -------------------------------------------------------------------------

    def _sort_listing(
        self, mappings: Iterable[Mapping]
    ) -> list[Mapping]:
        """
        Sort listing.

        When sorting a listing, we sort the mappings of the listing, which is
        why the caller must pass the mappings of the listing. That way, we can
        keep this implementation to be purely functional, without having to
        mutate the listing, which makes testing simpler.

        Arguments:
            mappings: The mappings.

        Returns:
            The sorted mappings.
        """
        return sorted(
            mappings,
            key = self.config.listings_sort_by,
            reverse = self.config.listings_sort_reverse
        )

    def _sort_listing_tags(
        self, children: dict[Tag, ListingTree]
    ) -> dict[Tag, ListingTree]:
        """
        Sort listing tags.

        When sorting a listing's tags, we sort the immediate subtrees of the
        listing, which is why the caller must pass the children of the listing.
        That way, we can keep this implementation to be purely functional,
        without having to mutate the listing.

        Arguments:
            children: The listing trees, each of which associated with a tag.

        Returns:
            The sorted listing trees.
        """
        return dict(sorted(
            children.items(),
            key = lambda item: self.config.listings_tags_sort_by(*item),
            reverse = self.config.listings_tags_sort_reverse
        ))

    def _sort_tags(
        self, tags: Iterable[Tag]
    ) -> list[Tag]:
        """
        Sort tags.

        Arguments:
            tags: The tags.

        Returns:
            The sorted tags.
        """
        return sorted(
            tags,
            key = self.config.tags_sort_by,
            reverse = self.config.tags_sort_reverse
        )

# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------

def _print(manager: ListingManager, indent: int = 0) -> str:
    """
    Return a printable representation of a listing manager.

    Arguments:
        manager: The listing manager.
        indent: The indentation level.

    Returns:
        Printable representation.
    """
    lines: list[str] = []
    lines.append(" " * indent + f"ListingManager()")

    # Print listings
    for listing in manager:
        lines.append(" " * (indent + 2) + repr(listing))

    # Concatenate everything
    return "\n".join(lines)

# -----------------------------------------------------------------------------
# Data
# -----------------------------------------------------------------------------

# Set up logging
log = logging.getLogger("mkdocs.material.plugins.tags")


#-----------------------------------------------------------------------------
# From tags/structure/listing/manager/toc.py
#-----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Typings
# -----------------------------------------------------------------------------

Slugify = Callable[[Tag], str]
"""
Slugify function.

Arguments:
    tag: The tag.

Returns:
    The slugified tag.
"""

# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------

def populate(listing: Listing, slugify: Slugify) -> dict[Tag, AnchorLink]:
    """
    Populate the table of contents of the page the listing is embedded.

    Arguments:
        listing: The listing.
        slugify: Slugify function.

    Returns:
        The mapping of tags to anchor links.
    """
    anchors: dict[Tag, AnchorLink] = {}

    # Find injection point for listing
    host, at = find(listing)
    if at == -1:
        return anchors

    # Create anchor links
    for tree in listing:

        # Iterate over expanded tags
        for i, tag in enumerate(reversed([*tree.tag])):
            if tag not in anchors:
                level = host.level + 1 + i

                # Create anchor link
                anchors[tag] = AnchorLink(tag.name, slugify(tag), level)
                if not tag.parent:
                    continue

                # Relate anchor link to parent
                anchors[tag.parent].children.append(anchors[tag])

    # Filter top-level anchor links and insert them into the page
    children = [anchors[tag] for tag in anchors if not tag.parent]
    if listing.config.toc:
        host.children[at:at + 1] = children
    else:
        host.children.pop(at)

    # Return mapping of tags to anchor links
    return anchors

# -----------------------------------------------------------------------------

def find(listing: Listing) -> tuple[AnchorLink | None, int]:
    """
    Find anchor link for the given listing.

    This function traverses the table of contents of the given page and returns
    the anchor's parent and index of the anchor with the given identifier. If
    the anchor is on the root level, and the anchor we're looking for is an
    injection point, an anchor to host the tags is created and returned.

    Arguments:
        lising: The listing.

    Returns:
        The anchor and index.
    """
    page = listing.page

    # Traverse table of contents
    stack = list(page.toc)
    while stack:
        anchor = stack.pop()

        # Traverse children
        for i, child in enumerate(anchor.children):
            if child.id.startswith(listing.id):
                return anchor, i

            # Add child to stack
            stack.append(child)

    # Check if anchor is on the root level
    for i, anchor in enumerate(page.toc):
        if anchor.id.startswith(listing.id):

            # Create anchor link
            host = AnchorLink(page.title, page.url, 1)
            host.children = page.toc.items
            return host, i

    # Anchor could not be found
    return None, -1


#-----------------------------------------------------------------------------
# From tags/structure/listing/tree/__init__.py
#-----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Classes
# -----------------------------------------------------------------------------

@total_ordering
class ListingTree:
    """
    A listing tree.

    Listing trees are a tree structure that represent the hierarchy of tags
    and mappings. Each tree node is a tag, and each tag can have multiple
    mappings. Additionally, each tree can have subtrees, which are typically
    called nested tags.

    This is an internal data structure that is used to render listings. It is
    also the immediate structure that is passed to the template.
    """

    def __init__(self, tag: Tag):
        """
        Initialize the listing tree.

        Arguments:
            tag: The tag.
        """
        self.tag = tag
        self.content = None
        self.mappings = []
        self.children = {}

    def __repr__(self) -> str:
        """
        Return a printable representation of the listing tree.

        Returns:
            Printable representation.
        """
        return _print(self)

    def __hash__(self) -> int:
        """
        Return the hash of the listing tree.

        Returns:
            The hash.
        """
        return hash(self.tag)

    def __iter__(self) -> Iterator[ListingTree]:
        """
        Iterate over subtrees of the listing tree.

        Yields:
            The current subtree.
        """
        return iter(self.children.values())

    def __eq__(self, other: ListingTree) -> bool:
        """
        Check if the listing tree is equal to another listing tree.

        Arguments:
            other: The other listing tree to check.

        Returns:
            Whether the listing trees are equal.
        """
        assert isinstance(other, ListingTree)
        return self.tag == other.tag

    def __lt__(self, other: ListingTree) -> bool:
        """
        Check if the listing tree is less than another listing tree.

        Arguments:
            other: The other listing tree to check.

        Returns:
            Whether the listing tree is less than the other listing tree.
        """
        assert isinstance(other, ListingTree)
        return self.tag < other.tag

    # -------------------------------------------------------------------------

    tag: Tag
    """
    The tag.
    """

    content: str | None
    """
    The rendered content of the listing tree.

    This attribute holds the result of rendering the `tag.html` template, which
    is the rendered tag as displayed in the listing. It is essential that this
    is done for all tags (and nested tags) before rendering the tree, as the
    rendering process of the listing tree relies on this attribute.
    """

    mappings: list[Mapping]
    """
    The mappings associated with the tag.
    """

    children: dict[Tag, ListingTree]
    """
    The subtrees of the listing tree.
    """

# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------

def _print(tree: ListingTree, indent: int = 0) -> str:
    """
    Return a printable representation of a listing tree.

    Arguments:
        tree: The listing tree.
        indent: The indentation level.

    Returns:
        Printable representation.
    """
    lines: list[str] = []
    lines.append(" " * indent + f"ListingTree({repr(tree.tag)})")

    # Print mappings
    for mapping in tree.mappings:
        lines.append(" " * (indent + 2) + repr(mapping))

    # Print subtrees
    for child in tree.children.values():
        lines.append(_print(child, indent + 2))

    # Concatenate everything
    return "\n".join(lines)


#-----------------------------------------------------------------------------
# From tags/structure/mapping/manager/__init__.py
#-----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Classes
# -----------------------------------------------------------------------------

class MappingManager:
    """
    A mapping manager.

    The mapping manager is responsible for collecting all tags from the front
    matter of pages, and for building a tag structure from them, nothing more.
    """

    def __init__(self, config: TagsConfig):
        """
        Initialize the mapping manager.

        Arguments:
            config: The configuration.
        """
        self.config = config
        self.format = TagSet(allowed = self.config.tags_allowed)
        self.data = {}

    def __repr__(self) -> str:
        """
        Return a printable representation of the mapping manager.

        Returns:
            Printable representation.
        """
        return _print(self)

    def __iter__(self) -> Iterator[Mapping]:
        """
        Iterate over mappings.

        Yields:
            The current mapping.
        """
        return iter(self.data.values())

    # -------------------------------------------------------------------------

    config: TagsConfig
    """
    The configuration.
    """

    format: TagSet
    """
    The mapping format.

    This is the validator that is used to check if tags are valid, including
    the tags in the front matter of pages, as well as the tags defined in the
    configuration. Numbers and booleans are always converted to strings before
    creating tags, and the allow list is checked as well, if given.
    """

    data: dict[str, Mapping]
    """
    The mappings.
    """

    # -------------------------------------------------------------------------

    def add(self, page: Page, markdown: str) -> Mapping | None:
        """
        Add page.

        This method is called by the tags plugin to retrieve all tags of a page.
        It extracts all tags from the front matter of the given page, and adds
        them to the mapping. If no tags are found, no mapping is created and
        nothing is returned.

        Note that this method is intended to be called with the page during the
        `on_page_markdown` event, as it reads the front matter of a page. Also,
        the Markdown must be explicitly passed, as we could otherwise run into
        inconsistencies when other plugins modify the Markdown.

        Arguments:
            page: The page.
            markdown: The page's Markdown.

        Returns:
            The mapping or nothing.
        """
        assert isinstance(markdown, str)

        # Return nothing if page doesn't have tags
        tags = self.config.tags_name_variable
        if not page.meta.get(tags, []):
            return

        # Create mapping and associate with page
        mapping = Mapping(page)
        self.data[page.url] = mapping

        # Retrieve and validate tags, and add to mapping
        for tag in self.format.validate(page.meta[tags]):
            # Normalize non-string tags before configuring
            if not isinstance(tag, (str, Tag)):
                tag = str(tag)

            # Convert string tags to Tag objects
            if isinstance(tag, str):
                tag = Tag(name=tag)
            mapping.tags.add(self._configure(tag))

        # Return mapping
        return mapping

    def get(self, page: Page) -> Mapping | None:
        """
        Get mapping for page, if any.

        Arguments:
            page: The page.

        Returns:
            The mapping or nothing.
        """
        if page.url in self.data:
            return self.data[page.url]

    # -------------------------------------------------------------------------

    def _configure(self, tag: Tag) -> Tag:
        """
        Configure tag.

        This method is called by the mapping manager to configure a tag for the
        the tag structure. Depending on the configuration, the tag is expanded
        into a hierarchy of tags, and can be marked as hidden if it is a shadow
        tag, hiding it from mappings and listings when rendering.

        Arguments:
            tag: The tag.

        Returns:
            The configured tag.
        """
        if self.config.tags_hierarchy:
            return self._configure_hierarchy(tag)
        else:
            return self._configure_shadow(tag, tag.name)

    def _configure_hierarchy(self, tag: Tag) -> Tag:
        """
        Configure hierarchical tag.

        Note that shadow tags that occur as part of a tag hierarchy propagate
        their hidden state to all of their children.

        Arguments:
            tag: The tag.

        Returns:
            The configured tag.
        """
        separator = self.config.tags_hierarchy_separator
        root, *rest = tag.name.split(separator)

        # Create tag root and hierarchy
        tag = self._configure_shadow(Tag(root), root)
        for name in rest:
            tag = self._configure_shadow(Tag(
                separator.join([tag.name, name]),
                parent = tag, hidden = tag.hidden
            ), name)

        # Return tag
        return tag

    def _configure_shadow(self, tag: Tag, name: str) -> Tag:
        """
        Configure shadow tag.

        Regardless of the configuration, tags are always marked as hidden if
        they're classified as shadow tags, e.g., if their name matches the
        configured shadow prefix or suffix, or if they're part of the list of
        shadow tags. Whether they're displayed is decided before rendering.

        The tag name must be passed separately, as it may be different from the
        tag's name, e.g., when creating a tag hierarchy. In this case, the name
        represents the part that was added to the tag, essentially the suffix.
        The name is checked for shadow prefixes and suffixes.

        Arguments:
            tag: The tag.
            name: The tag name.

        Returns:
            The configured tag.
        """
        if not tag.hidden:
            tag.hidden = tag in (self.config.shadow_tags or [])

        # Check if tag matches shadow prefix, if defined
        if not tag.hidden and self.config.shadow_tags_prefix:
            tag.hidden = name.startswith(self.config.shadow_tags_prefix)

        # Check if tag matches shadow suffix, if defined
        if not tag.hidden and self.config.shadow_tags_suffix:
            tag.hidden = name.endswith(self.config.shadow_tags_suffix)

        # Return tag
        return tag

# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------

def _print(manager: MappingManager, indent: int = 0) -> str:
    """
    Return a printable representation of a mapping manager.

    Arguments:
        manager: The mapping manager.
        indent: The indentation level.

    Returns:
        Printable representation.
    """
    lines: list[str] = []
    lines.append(" " * indent + f"MappingManager()")

    # Print mappings
    for mapping in manager:
        lines.append(" " * (indent + 2) + repr(mapping))

    # Concatenate everything
    return "\n".join(lines)


#-----------------------------------------------------------------------------
# From tags/structure/mapping/storage/__init__.py
#-----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Classes
# -----------------------------------------------------------------------------

class MappingStorage:
    """
    A mapping storage.

    The mapping storage allows to save and load mappings to and from a JSON
    file, which allows for sharing tags across multiple MkDocs projects.
    """

    def __init__(self, config: TagsConfig):
        """
        Initialize the mapping storage.

        Arguments:
            config: The configuration.
        """
        self.config = config

    # -------------------------------------------------------------------------

    config: TagsConfig
    """
    The configuration.
    """

    # -------------------------------------------------------------------------

    def save(self, path: str, mappings: Iterable[Mapping]) -> None:
        """
        Save mappings to file.

        Arguments:
            path: The file path.
            mappings: The mappings.
        """
        path = os.path.abspath(path)
        os.makedirs(os.path.dirname(path), exist_ok = True)

        # Save serialized mappings to file
        with open(path, "w", encoding = "utf-8") as f:
            data = [_mapping_to_json(mapping) for mapping in mappings]
            json.dump(dict(mappings = data), f)

    def load(self, path: str) -> Iterable[Mapping]:
        """
        Load mappings from file.

        Arguments:
            path: The file path.

        Yields:
            The current mapping.
        """
        with open(path, "r", encoding = "utf-8") as f:
            data = json.load(f)

            # Ensure root dictionary
            if not isinstance(data, dict):
                raise ValidationError(
                    f"Expected dictionary, but received: {data}"
                )

            # Ensure mappings are iterable
            mappings = data.get("mappings")
            if not isinstance(mappings, list):
                raise ValidationError(
                    f"Expected list, but received: {mappings}"
                )

            # Create and yield mappings
            for mapping in mappings:
                yield _mapping_from_json(mapping)

# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------

def _mapping_to_json(mapping: Mapping) -> dict:
    """
    Return a serializable representation of a mapping.

    Arguments:
        mapping: The mapping.

    Returns:
        Serializable representation.
    """
    return dict(
        item = _mapping_item_to_json(mapping.item),
        tags = [str(tag) for tag in sorted(mapping.tags)]
    )

def _mapping_item_to_json(item: Page | Link) -> dict:
    """
    Return a serializable representation of a page or link.

    Arguments:
        item: The page or link.

    Returns:
        Serializable representation.
    """
    return dict(url = item.url, title = item.title)

# -------------------------------------------------------------------------

def _mapping_from_json(data: object) -> Mapping:
    """
    Return a mapping from a serialized representation.

    Arguments:
        data: Serialized representation.

    Returns:
        The mapping.
    """
    if not isinstance(data, dict):
        raise ValidationError(
            f"Expected dictionary, but received: {data}"
        )

    # Ensure tags are iterable
    tags = data.get("tags")
    if not isinstance(tags, list):
        raise ValidationError(
            f"Expected list, but received: {tags}"
        )

    # Ensure tags are valid
    for tag in tags:
        if not isinstance(tag, str):
            raise ValidationError(
                f"Expected string, but received: {tag}"
            )

    # Create and return mapping
    return Mapping(
        _mapping_item_from_json(data.get("item")),
        tags = [Tag(tag) for tag in tags]
    )

def _mapping_item_from_json(data: object) -> Link:
    """
    Return a link from a serialized representation.

    When loading a mapping, we must always return a link, as the sources of
    pages might not be available because we're building another project.

    Arguments:
        data: Serialized representation.

    Returns:
        The link.
    """
    if not isinstance(data, dict):
        raise ValidationError(
            f"Expected dictionary, but received: {data}"
        )

    # Ensure item has URL
    url = data.get("url")
    if not isinstance(url, str):
        raise ValidationError(
            f"Expected string, but received: {url}"
        )

    # Ensure item has title
    title = data.get("title")
    if not isinstance(title, str):
        raise ValidationError(
            f"Expected string, but received: {title}"
        )

    # Create and return item
    return Link(title, url)


#-----------------------------------------------------------------------------
# From tags/structure/tag/reference/__init__.py
#-----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Classes
# -----------------------------------------------------------------------------

class TagReference(Tag):
    """
    A tag reference.

    Tag references are a subclass of tags that can have associated links, which
    is primarily used for linking tags to listings. The first link is used as
    the canonical link, which by default points to the closest listing that
    features the tag. This is considered to be the canonical listing.
    """

    def __init__(self, tag: Tag, links: list[Link] | None = None):
        """
        Initialize the tag reference.

        Arguments:
            tag: The tag.
            links: The links associated with the tag.
        """
        super().__init__(**vars(tag))
        self.links = links or []

    def __repr__(self) -> str:
        """
        Return a printable representation of the tag reference.

        Returns:
            Printable representation.
        """
        return f"TagReference('{self.name}')"

    # -------------------------------------------------------------------------

    links: list[Link]
    """
    The links associated with the tag.
    """

    # -------------------------------------------------------------------------

    @property
    def url(self) -> str | None:
        """
        Return the URL of the tag reference.

        Returns:
            The URL of the tag reference.
        """
        if self.links:
            return self.links[0].url
        else:
            return None

#-----------------------------------------------------------------------------
# Renderer class (from renderer/__init__.py)
#-----------------------------------------------------------------------------

class Renderer:
    """
    A renderer for tags and listings.
    """

    def __init__(self, env: Environment, config: DocsForgeConfig):
        self.env = env
        self.config = config

    env: Environment
    config: DocsForgeConfig

    def render(self, page: Page, name: str, **kwargs) -> str:
        path = posixpath.join("fragments", "tags", name)
        path = posixpath.normpath(path)
        template = self.env.get_template(path)
        return template.render(
            config = self.config, page = page,
            base_url = get_relative_url(".", page.url),
            **kwargs
        )


#-----------------------------------------------------------------------------
# TagsPlugin class (from plugin.py)
#-----------------------------------------------------------------------------

class TagsPlugin(BasePlugin[TagsConfig]):
    """
    A tags plugin.

    This plugin collects tags from the front matter of pages, and builds a tag
    structure from them.
    """

    supports_multiple_instances = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_serve = False
        self.mappings = None
        self.listings = None

    mappings: MappingManager
    listings: ListingManager
    filter: FileFilter

    def on_startup(self, *, command, **kwargs) -> None:
        self.is_serve = command == "serve"

    def on_config(self, config: DocsForgeConfig) -> None:
        depth = config.mdx_configs.get("toc", {}).get("toc_depth", 6)
        if not isinstance(depth, int) and "-" in str(depth):
            _, depth = str(depth).split("-")

        self.mappings = MappingManager(self.config)
        self.listings = ListingManager(self.config, int(depth))
        self.filter = FileFilter(self.config.filters or FilterConfig())

        for extension in config.markdown_extensions:
            if isinstance(extension, str) and extension.endswith("attr_list"):
                break
        else:
            config.markdown_extensions.append("attr_list")

        if self.config.export_only:
            self.config.tags = False
            self.config.listings = False

        if self.is_serve and self.config.shadow_on_serve:
            self.config.shadow = True

    @event_priority(-50)
    def on_page_markdown(
        self, markdown: str, *, page: Page, config: DocsForgeConfig, **kwargs
    ) -> str:
        if not self.config.enabled:
            return markdown

        if not self.filter(page.file):
            return markdown

        if self.config.tags_file:
            markdown = self._handle_deprecated_tags_file(page, markdown)

        if self.config.tags_extra_files:
            markdown = self._handle_deprecated_tags_extra_files(page, markdown)

        try:
            self.mappings.add(page, markdown)
        except Exception as e:
            docs = os.path.relpath(config.docs_dir)
            path = os.path.relpath(page.file.abs_src_path, docs)
            raise PluginError(
                    f"Error reading tags of page '{path}' in '{docs}':\n"
                    f"{e}"
                )

        return self.listings.add(page, markdown)

    @event_priority(100)
    def on_env(
        self, env: Environment, *, config: DocsForgeConfig, **kwargs
    ) -> None:
        if not self.config.enabled:
            return

        self.listings.populate_all(self.mappings, Renderer(env, config))

        if self.config.export:
            path = os.path.join(config.site_dir, self.config.export_file)
            path = os.path.normpath(path)
            storage = MappingStorage(self.config)
            storage.save(path, self.mappings)

    def on_page_context(
        self, context: TemplateContext, *, page: Page, **kwargs
    ) -> None:
        if not self.config.enabled:
            return

        if not self.filter(page.file):
            return

        if not self.config.tags:
            return

        mapping = self.mappings.get(page)
        if mapping:
            tags = self.config.tags_name_variable
            if tags not in context:
                context[tags] = list(self.listings & mapping)

    def _handle_deprecated_tags_file(
        self, page: Page, markdown: str
    ) -> str:
        directive = self.config.listings_directive
        if page.file.src_uri != self.config.tags_file:
            return markdown

        if "[TAGS]" in markdown:
            markdown = markdown.replace(
                "[TAGS]", f"<!-- {directive} -->"
            )

        pattern = r"<!--\s+{directive}".format(directive = directive)
        if not re.search(pattern, markdown):
            markdown += f"\n<!-- {directive} -->"

        return markdown

    def _handle_deprecated_tags_extra_files(
        self, page: Page, markdown: str
    ) -> str:
        directive = self.config.listings_directive
        if page.file.src_uri not in self.config.tags_extra_files:
            return markdown

        tags = self.config.tags_extra_files[page.file.src_uri]
        if tags:
            directive += f" {{ include: [{', '.join(tags)}] }}"

        if "[TAGS]" in markdown:
            markdown = markdown.replace(
                "[TAGS]", f"<!-- {directive} -->"
            )

        pattern = r"<!--\s+{directive}".format(directive = re.escape(directive))
        if not re.search(pattern, markdown):
            markdown += f"\n<!-- {directive} -->"

        return markdown


log = logging.getLogger("docsforge.tags")
