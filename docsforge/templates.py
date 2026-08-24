from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

from markupsafe import Markup

if TYPE_CHECKING:
    import datetime


# Content-hash segment injected by the asset build.  Templates refer to stable
# logical names (e.g. ``stylesheets/main.min.css``) and the manifest maps them
# to the concrete hashed filename on disk.
_ASSET_HASH_SEGMENT_RE = re.compile(r"\.[a-f0-9]{8,}(?=\.min\.[^.]+$)")


# Allowed characters for icon names used in Jinja include/import paths.
# Disallows path traversal sequences (..), absolute paths, and special chars.
_ICON_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*\Z")

try:
    from jinja2 import pass_context as contextfilter
except ImportError:
    from jinja2 import contextfilter  # type: ignore[attr-defined]

if TYPE_CHECKING:
    from docsforge.config_defaults import DocsForgeConfig
    from docsforge.config_options import ExtraScriptValue
    from docsforge.files import File
    from docsforge.nav import Navigation
    from docsforge.pages import Page


class TemplateContext(TypedDict):
    nav: Navigation
    pages: Sequence[File]
    base_url: str
    extra_css: Sequence[str]  # Do not use, prefer `config.extra_css`.
    extra_javascript: Sequence[str]  # Do not use, prefer `config.extra_javascript`.
    docsforge_version: str
    build_date_utc: datetime.datetime
    config: DocsForgeConfig
    page: Page | None


@contextfilter
def url_filter(context: TemplateContext, value: str) -> str:
    """A Template filter to normalize URLs."""
    from docsforge.utils import normalize_url
    return normalize_url(str(value), base=context["base_url"])


@contextfilter
def script_tag_filter(context: TemplateContext, extra_script: ExtraScriptValue) -> str:
    """Converts an ExtraScript value to an HTML <script> tag line."""
    html = '<script src="{0}"'
    if not isinstance(extra_script, str):
        if extra_script.type:
            html += ' type="{1.type}"'
        if extra_script.defer:
            html += " defer"
        if extra_script.async_:
            html += " async"
    html += "></script>"
    return Markup(html).format(url_filter(context, str(extra_script)), extra_script)


def validate_icon_name(value: str | None) -> str | None:
    """Validate an icon name for use in Jinja include/import paths.

    Returns the icon name if it only contains safe path characters
    (alphanumeric, underscore, hyphen, forward slash) and does not allow
    path traversal, absolute paths, or empty path components. Returns None
    for invalid names so templates can skip rendering them gracefully.
    """
    if value is None:
        return None
    name = str(value).strip()
    return name if _ICON_NAME_RE.match(name) else None


# Material palette name -> CSS hex color, mirroring --md-primary-fg-color in
# assets/stylesheets/palette.min.css. `theme.palette.primary` holds a palette
# *name* ("teal"), which is not a valid CSS color, so anywhere a real color is
# required -- the theme-color meta tag, the PWA manifest -- it has to be mapped
# through here first. `white`/`black` resolve --md-hue at its default of 225.
PRIMARY_COLORS: dict[str, str] = {
    "red": "#ef5552",
    "pink": "#e92063",
    "purple": "#ab47bd",
    "deep-purple": "#7e56c2",
    "indigo": "#4051b5",
    "blue": "#2094f3",
    "light-blue": "#02a6f2",
    "cyan": "#00bdd6",
    "teal": "#009485",
    "green": "#4cae4f",
    "light-green": "#8bc34b",
    "lime": "#cbdc38",
    "yellow": "#ffec3d",
    "amber": "#ffc105",
    "orange": "#ffa724",
    "deep-orange": "#ff6e42",
    "brown": "#795649",
    "grey": "#757575",
    "blue-grey": "#546d78",
    "white": "#ffffff",
    "black": "#14151a",
}

DEFAULT_PRIMARY_COLOR = PRIMARY_COLORS["indigo"]

# Values users may supply instead of a palette name: hex literals and CSS color
# functions are already valid colors and pass through untouched.
_CSS_COLOR_RE = re.compile(
    r"^(#[0-9a-fA-F]{3,8}|(rgb|rgba|hsl|hsla|color|lab|lch|oklab|oklch)\(.*\))$"
)


def resolve_theme_color(value: object) -> str:
    """Resolve a ``theme.palette.primary`` value to a usable CSS color.

    Accepts a Material palette name ("teal"), a literal CSS color ("#009485",
    "hsl(174, 100%, 29%)"), or None/garbage. Unknown names fall back to the
    default indigo rather than emitting an invalid color.
    """
    if value is None:
        return DEFAULT_PRIMARY_COLOR
    name = str(value).strip()
    if not name:
        return DEFAULT_PRIMARY_COLOR
    if name in PRIMARY_COLORS:
        return PRIMARY_COLORS[name]
    if _CSS_COLOR_RE.match(name):
        return name
    return DEFAULT_PRIMARY_COLOR


def primary_color_of(palette: object) -> str:
    """Resolve the theme color from a ``theme.palette`` config value.

    ``palette`` may be a mapping, or a list of mappings when light/dark toggles
    are configured (the first entry wins).
    """
    if isinstance(palette, (list, tuple)):
        palette = palette[0] if palette else None
    if isinstance(palette, dict):
        return resolve_theme_color(palette.get("primary"))
    return DEFAULT_PRIMARY_COLOR


def asset_url(value: str, manifest: dict[str, str] | None = None) -> str:
    """Resolve a logical asset path to the concrete site-relative URL.

    When a manifest is supplied (during a real build), the logical name is
    mapped to the hashed filename on disk.  Outside of a build the helper
    falls back to ``assets/<value>`` so templates still render.
    """
    if manifest is not None:
        return manifest.get(value, f"assets/{value}")
    return f"assets/{value}"


def build_asset_manifest(site_dir: str | Path) -> dict[str, str]:
    """Build a logical -> actual path mapping for vendored assets.

    Scans ``<site_dir>/assets`` and strips content-hash segments from filenames
    so templates can refer to stable logical names.  Non-hashed files are mapped
    to themselves.
    """
    manifest: dict[str, str] = {}
    assets_dir = Path(site_dir) / "assets"
    if not assets_dir.is_dir():
        return manifest

    for path in assets_dir.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(assets_dir).as_posix()
        logical = _ASSET_HASH_SEGMENT_RE.sub("", rel)
        manifest[logical] = f"assets/{rel}"

    return manifest


def build_asset_manifest_from_files(files) -> dict[str, str]:
    """Build a logical -> actual path mapping from the static file collection.

    Unlike ``build_asset_manifest``, this uses the planned file collection so
    it captures assets even if they are copied/generated into ``site_dir`` after
    the initial directory scan.  Non-hashed files are omitted because their
    logical and actual names are identical.
    """
    manifest: dict[str, str] = {}
    for file in files:
        dest = getattr(file, "dest_uri", "")
        if not dest or not dest.startswith("assets/"):
            continue
        rel = dest[len("assets/"):]
        logical = _ASSET_HASH_SEGMENT_RE.sub("", rel)
        if logical != rel:
            manifest[logical] = dest
    return manifest
