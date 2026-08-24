"""Info plugin - always enabled, shows debug info during build.

The archive creation feature is disabled; this plugin just provides
configuration scaffolding and debug utilities.
"""

from __future__ import annotations

import logging

from docsforge.config_base import Config
from docsforge.config_options import Type
from docsforge.core.plugin_base import BasePlugin


# Plugin configuration
class InfoConfig(Config):
    enabled = Type(bool, default=True)
    enabled_on_serve = Type(bool, default=False)
    archive = Type(bool, default=True)
    archive_stop_on_violation = Type(bool, default=True)


# Exclusion patterns for archive (not currently used)
def _get_exclusion_patterns():
    """Regex patterns for excluding files/directories from archive."""
    return [
        r"/__pycache__/",
        r"/\.DS_Store$",
        r"/[^/]+\.zip$",
        r"/[^/]*\.cache($|/)",
        r"/\.vscode/",
        r"/\.vs/",
        r"/\.idea/",
    ]


class InfoPlugin(BasePlugin[InfoConfig]):
    """Always-on info plugin. Archive creation disabled."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_serve = False
        self.exclusion_patterns = []
        self.excluded_entries = []

    def on_startup(self, *, command, dirty):
        self.is_serve = command == "serve"

    def on_config(self, config):
        """Skip archive creation - just enable info features."""
        return


log = logging.getLogger("docsforge.info")
