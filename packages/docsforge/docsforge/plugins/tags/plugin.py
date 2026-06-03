# Copyright (c) 2016-2025 Martin Donath <martin.donath@squidfunk.com>
# Copyright (c) 2026 QQ (Cyrus)
#
# This file is part of DocsForge.
#
# DocsForge is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# DocsForge is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with DocsForge.  If not, see <https://www.gnu.org/licenses/>.



# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

from __future__ import annotations

import logging
import os
import re

from jinja2 import Environment
from docsforge.filter_config import FileFilter
from docsforge.config_defaults import DocsForgeConfig
from docsforge.exceptions import PluginError
from docsforge.plugins import BasePlugin, event_priority
from docsforge.pages import Page
from docsforge.templates import TemplateContext

from .config import TagsConfig
from .renderer import Renderer
from .structure.listing.manager import ListingManager
from .structure.mapping.manager import MappingManager
from .structure.mapping.storage import MappingStorage

# -----------------------------------------------------------------------------
# Classes
# -----------------------------------------------------------------------------

class TagsPlugin(BasePlugin[TagsConfig]):
    """
    A tags plugin.

    This plugin collects tags from the front matter of pages, and builds a tag
    structure from them. The tag structure can be used to render listings on
    pages, or to just create a site-wide tags index and export all tags and
    mappings to a JSON file for consumption in another project.
    """

    supports_multiple_instances = True
    """
    This plugin supports multiple instances.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the plugin.
        """
        super().__init__(*args, **kwargs)

        # Initialize incremental builds
        self.is_serve = False

        # Initialize mapping and listing managers
        self.mappings = None
        self.listings = None

    # -------------------------------------------------------------------------

    mappings: MappingManager
    """
    Mapping manager.
    """

    listings: ListingManager
    """
    Listing manager.
    """

    filter: FileFilter
    """
    File filter.
    """

    # -------------------------------------------------------------------------

    def on_startup(self, *, command, **kwargs) -> None:
        """
        Determine whether we're serving the site.

        Arguments:
            command: The command that is being executed.
            dirty: Whether dirty builds are enabled.
        """
        self.is_serve = command == "serve"

    def on_config(self, config: DocsForgeConfig) -> None:
        """
        Create mapping and listing managers.
        """

        # Retrieve toc depth, so we know the maximum level at which we can add
        # items to the table of contents - Python Markdown allows to set the
        # toc depth as a range, e.g. `2-6`, so we need to account for that as
        # well. We need this information for generating listings.
        depth = config.mdx_configs.get("toc", {}).get("toc_depth", 6)
        if not isinstance(depth, int) and "-" in depth:
            _, depth = depth.split("-")

        # Initialize mapping and listing managers
        self.mappings = MappingManager(self.config)
        self.listings = ListingManager(self.config, int(depth))

        # Initialize file filter - the file filter is used to include or exclude
        # entire subsections of the documentation, allowing for using multiple
        # instances of the plugin alongside each other. This can be necessary
        # when creating multiple, potentially conflicting listings.
        self.filter = FileFilter(self.config.filters)

        # Ensure presence of attribute lists extension
        for extension in config.markdown_extensions:
            if isinstance(extension, str) and extension.endswith("attr_list"):
                break
        else:
            config.markdown_extensions.append("attr_list")

        # If the author only wants to extract and export mappings, we allow to
        # disable the rendering of all tags and listings with a single setting
        if self.config.export_only:
            self.config.tags = False
            self.config.listings = False

        # By default, shadow tags are rendered when the documentation is served,
        # but not when it is built, for a better user experience
        if self.is_serve and self.config.shadow_on_serve:
            self.config.shadow = True

    @event_priority(-50)
    def on_page_markdown(
        self, markdown: str, *, page: Page, config: DocsForgeConfig, **kwargs
    ) -> str:
        """
        Collect tags and listings from page.

        Priority: -50 (run later)

        Arguments:
            markdown: The page's Markdown.
            page: The page.
            config: The MkDocs configuration.

        Returns:
            The page's Markdown with injection points.
        """
        if not self.config.enabled:
            return

        # Skip if page should not be considered
        if not self.filter(page.file):
            return

        # Handle deprecation of `tags_file` setting
        if self.config.tags_file:
            markdown = self._handle_deprecated_tags_file(page, markdown)

        # Handle deprecation of `tags_extra_files` setting
        if self.config.tags_extra_files:
            markdown = self._handle_deprecated_tags_extra_files(page, markdown)

        # Collect tags from page
        try:
            self.mappings.add(page, markdown)

        # Raise exception if tags could not be read
        except Exception as e:
            docs = os.path.relpath(config.docs_dir)
            path = os.path.relpath(page.file.abs_src_path, docs)
            raise PluginError(
                    f"Error reading tags of page '{path}' in '{docs}':\n"
                    f"{e}"
                )

        # Collect listings from page
        return self.listings.add(page, markdown)

    @event_priority(100)
    def on_env(
        self, env: Environment, *, config: DocsForgeConfig, **kwargs
    ) -> None:
        """
        Populate listings.

        Priority: 100 (run earliest)

        Arguments:
            env: The Jinja environment.
            config: The MkDocs configuration.
        """
        if not self.config.enabled:
            return

        # Populate and render all listings
        self.listings.populate_all(self.mappings, Renderer(env, config))

        # Export mappings to file, if enabled
        if self.config.export:
            path = os.path.join(config.site_dir, self.config.export_file)
            path = os.path.normpath(path)

            # Serialize mappings and save to file
            storage = MappingStorage(self.config)
            storage.save(path, self.mappings)

    def on_page_context(
        self, context: TemplateContext, *, page: Page, **kwargs
    ) -> None:
        """
        Add tag references to page context.

        Arguments:
            context: The template context.
            page: The page.
        """
        if not self.config.enabled:
            return

        # Skip if page should not be considered
        if not self.filter(page.file):
            return

        # Skip if tags should not be built
        if not self.config.tags:
            return

        # Retrieve tags references for page
        mapping = self.mappings.get(page)
        if mapping:
            tags = self.config.tags_name_variable
            if tags not in context:
                context[tags] = list(self.listings & mapping)

    # -------------------------------------------------------------------------

    def _handle_deprecated_tags_file(
        self, page: Page, markdown: str
    ) -> str:
        """
        Handle deprecation of `tags_file` setting.

        Arguments:
            page: The page.
        """
        directive = self.config.listings_directive
        if page.file.src_uri != self.config.tags_file:
            return markdown

        # Try to find the legacy tags marker and replace with directive
        if "[TAGS]" in markdown:
            markdown = markdown.replace(
                "[TAGS]", f"<!-- {directive} -->"
            )

        # Try to find the directive and add it if not present
        pattern = r"<!--\s+{directive}".format(directive = directive)
        if not re.search(pattern, markdown):
            markdown += f"\n<!-- {directive} -->"

        # Return markdown
        return markdown

    def _handle_deprecated_tags_extra_files(
        self, page: Page, markdown: str
    ) -> str:
        """
        Handle deprecation of `tags_extra_files` setting.

        Arguments:
            page: The page.
        """
        directive = self.config.listings_directive
        if page.file.src_uri not in self.config.tags_extra_files:
            return markdown

        # Compute tags to render on page
        tags = self.config.tags_extra_files[page.file.src_uri]
        if tags:
            directive += f" {{ include: [{', '.join(tags)}] }}"

        # Try to find the legacy tags marker and replace with directive
        if "[TAGS]" in markdown:
            markdown = markdown.replace(
                "[TAGS]", f"<!-- {directive} -->"
            )

        # Try to find the directive and add it if not present
        pattern = r"<!--\s+{directive}".format(directive = re.escape(directive))
        if not re.search(pattern, markdown):
            markdown += f"\n<!-- {directive} -->"

        # Return markdown
        return markdown

# -----------------------------------------------------------------------------
# Data
# -----------------------------------------------------------------------------

# Set up logging
log = logging.getLogger("mkdocs.material.plugins.tags")
