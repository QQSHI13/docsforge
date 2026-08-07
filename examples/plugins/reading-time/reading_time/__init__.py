"""Reading-time example plugin.

Estimates the reading time for each page from its Markdown source and
exposes it to templates as ``{{ reading_time }}`` (an int, minutes).
"""
from __future__ import annotations

import re

from docsforge.config_base import Config
from docsforge.config_options import Type
from docsforge.core.plugin_base import BasePlugin

_WORD_RE = re.compile(r"\w+")


class ReadingTimeConfig(Config):
    """Configuration read from docsforge.yml."""

    wpm = Type(int, default=200)
    """Words-per-minute used for the estimate."""


class ReadingTimePlugin(BasePlugin[ReadingTimeConfig]):
    """Adds ``reading_time`` to each page's template context."""

    def on_page_context(self, context, *, page, config, nav):
        markdown = getattr(page, "markdown", None) or ""
        words = len(_WORD_RE.findall(markdown))
        # Round up to at least 1 minute so short pages don't show "0 min".
        context["reading_time"] = max(1, round(words / max(1, self.config.wpm)))
