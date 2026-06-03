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

import posixpath

from jinja2 import Environment
from docsforge.config_defaults import DocsForgeConfig
from docsforge.pages import Page
from docsforge import get_relative_url

# -----------------------------------------------------------------------------
# Classes
# -----------------------------------------------------------------------------

class Renderer:
    """
    A renderer for tags and listings.

    This class implements a simple tag and listing renderer, leveraging the
    Jinja environment and the MkDocs configuration as provided to plugins.

    Note that the templates must be stored in the `fragments` and not `partials`
    directory, because in order to render tags and listings, we must wait for
    all pages to be read and processed, as we first need to collect all tags
    before we can render listings. Tags induce a graph, not a tree.

    For this reason, we consider the templates to be fragments, as they are
    not implicitly rendered by MkDocs, but explicitly by the plugin.
    """

    def __init__(self, env: Environment, config: DocsForgeConfig):
        """
        Initialize renderer.

        Arguments:
            env: The Jinja environment.
            config: The MkDocs configuration.
        """
        self.env = env
        self.config = config

    # -------------------------------------------------------------------------

    env: Environment
    """
    The Jinja environment.
    """

    config: DocsForgeConfig
    """
    The MkDocs configuration.
    """

    # -------------------------------------------------------------------------

    def render(self, page: Page, name: str, **kwargs) -> str:
        """
        Render a template.

        Templates are resolved from `fragments/tags`, so if you want to override
        templates or provide additional ones place them in this directory.

        Arguments:
            page: The page.
            name: The name of the template.
            kwargs: The template variables.

        Returns:
            The rendered template.
        """
        path = posixpath.join("fragments", "tags", name)
        path = posixpath.normpath(path)

        # Resolve and render template
        template = self.env.get_template(path)
        return template.render(
            config = self.config, page = page,
            base_url = get_relative_url(".", page.url),
            **kwargs
        )
