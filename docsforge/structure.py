"""StructureItem base class for navigation elements."""

from __future__ import annotations

import abc
import threading
from collections.abc import Iterable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from docsforge.nav import Section


# Page currently being rendered on this thread (see set_rendering_page).
# Parallel page builds share one nav tree; without this, a template rendered
# for page A would observe page B's `active` flag while B renders
# concurrently, baking sibling/section highlights from other pages into A's
# output (merged nav, overlapping sticky headers).
_render_page_state = threading.local()


def set_rendering_page(page: StructureItem | None) -> tuple[StructureItem | None, list[StructureItem]]:
    """Mark `page` as the one being rendered on this thread.

    Starts with an empty extra-active list (see mark_rendering_active).
    Returns the previous ``(page, extra)`` pair so nested renders can
    restore it. `None` clears the marker (normal state outside rendering).
    """
    prev = (getattr(_render_page_state, "page", None), getattr(_render_page_state, "extra", []))
    _render_page_state.page = page
    _render_page_state.extra = []
    return prev


def restore_rendering_page(prev: tuple[StructureItem | None, list[StructureItem]]) -> None:
    """Restore a pair previously returned by set_rendering_page."""
    _render_page_state.page, _render_page_state.extra = prev


def mark_rendering_active(item: StructureItem) -> None:
    """Additionally highlight `item` for the page rendering on this thread.

    For locale-nav counterparts: they are distinct objects from the rendering
    page (matched by src_uri, not identity), so the ancestor walk in
    rendering_active cannot see them — hooks register them explicitly.
    No-op outside a page render.
    """
    if getattr(_render_page_state, "page", None) is None:
        return
    extra = getattr(_render_page_state, "extra", None)
    if extra is None:
        return
    if not any(node is item for node in extra):
        extra.append(item)


def rendering_active(item: StructureItem) -> bool | None:
    """Active state of `item` for the page rendering on this thread.

    Returns `None` when no render is in progress — callers then fall back to
    the stored flag. Otherwise `True` only for the rendering page, its
    ancestors, and explicitly marked items (plus their ancestors) — exactly
    what a serial build would observe.
    """
    current = getattr(_render_page_state, "page", None)
    if current is None:
        return None
    if _is_or_ancestor(item, current):
        return True
    return any(
        _is_or_ancestor(item, node)
        for node in getattr(_render_page_state, "extra", [])
    )


def _is_or_ancestor(item: StructureItem, node: StructureItem) -> bool:
    while node is not None:
        if node is item:
            return True
        node = node.parent
    return False


class StructureItem(abc.ABC):
    """An item in DocsForge structure - see concrete subclasses Section, Page or Link."""

    @abc.abstractmethod
    def __init__(self): ...

    parent: Section | None = None
    """The immediate parent of the item in the site navigation. `None` if it's at the top level."""

    @property
    def is_top_level(self) -> bool:
        return self.parent is None

    title: str | None
    is_section: bool = False
    is_page: bool = False
    is_link: bool = False

    @property
    def ancestors(self) -> Iterable[StructureItem]:
        if self.parent is None:
            return []
        return [self.parent, *self.parent.ancestors]

    def _indent_print(self, depth: int = 0) -> str:
        return ("    " * depth) + repr(self)
