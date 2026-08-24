"""Material Icons emoji extension for DocsForge.

Provides :material-icon-name: syntax using vendored SVG icons.
Based on Material for MkDocs' emoji extension.
"""

from __future__ import annotations

import functools
import os
from glob import iglob
from inspect import getfile
from xml.etree.ElementTree import Element

from markdown import Markdown
from pymdownx import emoji, twemoji_db

import docsforge

# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------

def twemoji(options: object, md: Markdown):
    """Create twemoji index with Material icons."""
    paths = options.get("custom_icons", [])[:]
    return _load_twemoji_index(tuple(paths))


def to_svg(
    index: str, shortname: str, alias: str, uc: str | None, alt: str,
    title: str, category: str, options: object, md: Markdown
):
    """Create emoji or icon element."""
    if not uc:
        icons = md.inlinePatterns["emoji"].emoji_index["emoji"]

        # Create and return element to host icon
        el = Element("span", {"class": options.get("classes", index)})
        el.text = md.htmlStash.store(_load(icons[shortname]["path"]))
        return el

    # Unicode emoji: serve from the vendored twemoji assets so no CDN is
    # referenced. Fall back to pymdownx only for codepoints missing from the
    # vendored set.
    file = _find_twemoji_svg(uc)
    if file is None:
        return emoji.to_svg(
            index, shortname, alias, uc, alt, title, category, options, md
        )

    el = Element("span", {"class": options.get("classes", index)})
    el.text = md.htmlStash.store(_load(file))
    return el


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

@functools.cache
def _load(file: str):
    """Load icon SVG content."""
    with open(file, encoding="utf-8") as f:
        return f.read()


@functools.cache
def _find_twemoji_svg(uc: str):
    """Return the vendored twemoji SVG file for a unicode codepoint string.

    `uc` uses the twemoji filename convention (dash-separated codepoints,
    e.g. `1f468-200d-1f4bb`). Returns None when the codepoint is not part
    of the vendored set.
    """
    path = os.path.join(_twemoji_dir(), f"{uc}.svg")
    return path if os.path.isfile(path) else None


@functools.cache
def _twemoji_dir() -> str:
    """Return the directory of the vendored twemoji SVG assets."""
    root = os.path.dirname(getfile(docsforge))
    return os.path.join(root, "templates", "assets", "emoji", "twemoji")


@functools.cache
def _load_twemoji_index(paths):
    """Load twemoji index and add Material icons."""
    index = {
        "name": "twemoji",
        "emoji": twemoji_db.emoji.copy(),
        "aliases": twemoji_db.aliases
    }

    # Compute path to theme root and traverse all icon directories
    root = os.path.dirname(getfile(docsforge))
    root = os.path.join(root, "templates", ".icons")

    for path in [*paths, root]:
        base = os.path.normpath(path)
        if not os.path.exists(base):
            continue

        # Index icons provided by the theme and via custom icons
        glob = os.path.join(base, "**", "*.svg")
        glob = iglob(os.path.normpath(glob), recursive=True)
        for file in glob:
            icon = file[len(base) + 1:-4].replace(os.path.sep, "-")

            # Add icon to index
            name = f":{icon}:"
            if not any(name in index[key] for key in ["emoji", "aliases"]):
                index["emoji"][name] = {"name": name, "path": file}

    return index
