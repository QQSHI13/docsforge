"""Compatibility shim for utils - re-exports from flattened utility modules."""

from __future__ import annotations

import functools
import logging
import os
import posixpath
import re
import shutil
import warnings
from bisect import insort  # noqa: F401 - legacy re-export
from collections import defaultdict
from collections.abc import Collection, Iterable
from datetime import datetime, timezone
from importlib.metadata import EntryPoint, entry_points
from pathlib import PurePath
from typing import TYPE_CHECKING, TypeVar
from urllib.parse import urlsplit

from docsforge import exceptions
from docsforge.weak_property import weak_property  # noqa: F401 - legacy re-export
from docsforge.yaml_utils import get_yaml_loader, yaml_load  # noqa: F401 - legacy re-export
from docsforge.tikz import compile_tikz_files  # noqa: F401 - legacy re-export

if TYPE_CHECKING:
    from docsforge.pages import Page

T = TypeVar('T')

log = logging.getLogger(__name__)

markdown_extensions = (
    '.markdown',
    '.mdown',
    '.mkdn',
    '.mkd',
    '.md',
)

class DuplicateFilter:
    """Avoid logging duplicate messages."""

    def __init__(self) -> None:
        self.msgs: set[str] = set()

    def __call__(self, record: logging.LogRecord) -> bool:
        rv = record.msg not in self.msgs
        self.msgs.add(record.msg)
        return rv

class CountHandler(logging.NullHandler):
    """Counts all logged messages >= level."""

    def __init__(self, **kwargs) -> None:
        self.counts: dict[int, int] = defaultdict(int)
        super().__init__(**kwargs)

    def handle(self, record):
        rv = self.filter(record)
        if rv:
            # Use levelno for keys so they can be sorted later
            self.counts[record.levelno] += 1
        return rv

    def get_counts(self) -> list[tuple[str, int]]:
        return [(logging.getLevelName(k), v) for k, v in sorted(self.counts.items(), reverse=True)]


def get_build_timestamp(*, pages: Collection[Page] | None = None) -> int:
    """
    Returns the number of seconds since the epoch for the latest updated page.

    In reality this is just today's date because that's how pages' update time is populated.
    """
    if pages:
        # Lexicographic comparison is OK for ISO date.
        date_string = max(p.update_date for p in pages)
        dt = datetime.fromisoformat(date_string).replace(tzinfo=timezone.utc)
    else:
        dt = get_build_datetime()
    return int(dt.timestamp())


def get_build_datetime() -> datetime:
    """Returns the current datetime in UTC."""
    return datetime.now(tz=timezone.utc)


def get_build_date() -> str:
    """Returns the displayable date string."""
    return get_build_datetime().strftime('%Y-%m-%d')


@functools.cache
def get_themes() -> dict[str, str]:
    """Return a dict of all installed themes as {name: title}."""
    themes = {}
    for entry in entry_points(group='docsforge.themes'):
        themes[entry.name] = entry.value
    return themes


def get_theme_names() -> list[str]:
    """Return a list of all installed theme names."""
    return list(get_themes().keys())


def get_theme_dir(name):
    """Return the path to the named theme directory."""
    from importlib.resources import files
    return files('docsforge.themes') / name


def normalize_url(path, page=None, base=''):
    """Normalize a URL to be relative to the given base."""
    if path.startswith(('http://', 'https://', 'mailto:', 'tel:', 'data:')):
        return path
    if page is not None:
        return posixpath.relpath(path, base)
    return path


def get_relative_url(current, target):
    """Return the relative path from current to target."""
    if target.startswith(('http://', 'https://', 'mailto:', 'tel:', 'data:')):
        return target
    if current == target:
        return '.'
    current = current.rsplit('/', 1)[0]
    rel = posixpath.relpath(target, current)
    if rel.startswith('.'):
        return rel
    return './' + rel


def is_error_template(template_name):
    """Check if a template is an error template."""
    return template_name in ('404.html', '500.html')


def write_file(content, path):
    """Write content to a file, creating parent directories if needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(content)


def copy_file(source_path, output_path):
    """Copy source_path to output_path, making sure any parent directories exist."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    shutil.copy2(source_path, output_path)


def clean_directory(path):
    """Remove all files in a directory, but keep the directory itself."""
    if not os.path.exists(path):
        return
    for entry in os.listdir(path):
        entry_path = os.path.join(path, entry)
        if os.path.isdir(entry_path):
            shutil.rmtree(entry_path)
        else:
            os.remove(entry_path)


def reduce_list(data_set: Iterable[T]) -> list[T]:
    """Reduce duplicate items in a list and preserve order."""
    return list(dict.fromkeys(data_set))


def nest_paths(paths):
    """Nest a list of paths into a tree structure."""
    result = {}
    for path in sorted(paths):
        current = result
        for part in path.split('/'):
            current = current.setdefault(part, {})
    return result


def get_markdown_title(markdown_text):
    """Extract the first H1 heading from markdown text."""
    for line in markdown_text.split('\n'):
        if line.startswith('# '):
            return line[2:].strip()
    return None


def get_url_path(path, use_directory_urls=True):
    """Convert a file path to a URL path."""
    if use_directory_urls:
        if path.endswith('/index.md'):
            return path[:-len('index.md')]
        if path.endswith('.md'):
            return path[:-3] + '/'
    return path


def get_static_url(path, use_directory_urls=True):
    """Get the URL for a static file."""
    if use_directory_urls:
        return path
    return path
