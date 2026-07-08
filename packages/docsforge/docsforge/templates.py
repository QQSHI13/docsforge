from __future__ import annotations

import re
from collections.abc import Sequence
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    import datetime

from markupsafe import Markup


# Allowed characters for icon names used in Jinja include/import paths.
# Disallows path traversal sequences (..), absolute paths, and special chars.
_ICON_NAME_RE = re.compile(r'^[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*\Z')

try:
    from jinja2 import pass_context as contextfilter
except ImportError:
    from jinja2 import contextfilter  # type: ignore  # noqa: PGH003

if TYPE_CHECKING:
    from docsforge.config_options import ExtraScriptValue
    from docsforge.config_defaults import DocsForgeConfig
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
    return normalize_url(str(value), base=context['base_url'])


@contextfilter
def script_tag_filter(context: TemplateContext, extra_script: ExtraScriptValue) -> str:
    """Converts an ExtraScript value to an HTML <script> tag line."""
    html = '<script src="{0}"'
    if not isinstance(extra_script, str):
        if extra_script.type:
            html += ' type="{1.type}"'
        if extra_script.defer:
            html += ' defer'
        if extra_script.async_:
            html += ' async'
    html += '></script>'
    return Markup(html).format(url_filter(context, str(extra_script)), extra_script)  # noqa: S704


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
