"""Meta plugin - merge .meta.yml files into page front matter.

Always enabled. Supports directory-level metadata via `.meta.yml` files.
"""

from __future__ import annotations

import logging
import os
import posixpath

from mergedeep import Strategy, merge
from yaml import SafeLoader, load

from docsforge.config_options import Type
from docsforge.config_base import Config
from docsforge.exceptions import PluginError
from docsforge.files import InclusionLevel
from docsforge.core.plugin_base import BasePlugin, event_priority


# Plugin configuration
class MetaConfig(Config):
    enabled = Type(bool, default=True)
    meta_file = Type(str, default=".meta.yml")


class MetaPlugin(BasePlugin[MetaConfig]):
    """Merge meta files into page metadata."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.meta = {}

    def on_files(self, files, *, config):
        if not self.config.enabled:
            return

        docs = os.path.relpath(config.docs_dir)
        for file in files:
            name = posixpath.basename(file.src_uri)
            if name != self.config.meta_file:
                continue

            # Exclude meta file from site output
            file.inclusion = InclusionLevel.EXCLUDED

            # Load YAML meta file
            with open(file.abs_src_path, encoding="utf-8-sig") as f:
                path = file.src_path
                try:
                    self.meta[path] = load(f, SafeLoader)
                except Exception as e:
                    raise PluginError(
                        f"Error reading meta file '{path}' in '{docs}':\n{e}"
                    )

    @event_priority(50)
    def on_page_markdown(self, markdown, *, page, config, files):
        if not self.config.enabled:
            return

        meta = {}
        strategy = Strategy.TYPESAFE_ADDITIVE

        # Merge matching meta files in level-order
        for path, defaults in self.meta.items():
            if not page.file.src_path.startswith(os.path.dirname(path)):
                continue

            page.meta.setdefault("__extends", [])
            if path in page.meta["__extends"]:
                continue

            try:
                merge(meta, defaults, strategy=strategy)
                page.meta["__extends"].append(path)
            except Exception as e:
                docs = os.path.relpath(config.docs_dir)
                raise PluginError(
                    f"Error merging meta file '{path}' in '{docs}':\n{e}"
                )

        # Page metadata takes precedence
        page.meta = merge(meta, page.meta, strategy=strategy)


log = logging.getLogger("docsforge.meta")
