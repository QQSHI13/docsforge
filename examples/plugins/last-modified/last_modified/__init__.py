"""Last-modified example plugin.

Sets ``page.meta['last_modified']`` from the source file's mtime so it can be
rendered in the page (e.g. in a custom ``partials/source-file.html``).

Shows the common pattern of reading page source metadata in
``on_page_markdown`` (which runs before the meta is finalized) and the use of
a configurable date format.
"""
from __future__ import annotations

import datetime
import os

from docsforge.config_base import Config
from docsforge.config_options import Type
from docsforge.core.plugin_base import BasePlugin


class LastModifiedConfig(Config):
    date_format = Type(str, default="%Y-%m-%d")
    """strftime format for the rendered date."""


class LastModifiedPlugin(BasePlugin[LastModifiedConfig]):
    """Populate ``page.meta['last_modified']`` for every page."""

    def on_page_markdown(self, markdown, *, page, config, files):
        src = getattr(page.file, "abs_src_path", None)
        if not src or not os.path.isfile(src):
            return markdown
        try:
            mtime = os.path.getmtime(src)
        except OSError:
            return markdown
        # UTC then astimezone() gives the machine-local wall clock as an aware
        # datetime, which is what a "last modified" stamp should display.
        stamp = datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc).astimezone()
        page.meta["last_modified"] = stamp.strftime(self.config.date_format)
        return markdown
