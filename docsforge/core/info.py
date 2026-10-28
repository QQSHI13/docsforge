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


class InfoPlugin(BasePlugin[InfoConfig]):
    """Always-on info plugin. Archive creation disabled."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_serve = False

    def on_startup(self, *, command, dirty):
        self.is_serve = command == "serve"

    def on_config(self, config):
        """Skip archive creation - just enable info features."""
        return


log = logging.getLogger("docsforge.info")
