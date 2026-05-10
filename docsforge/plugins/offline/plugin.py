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

import os

from docsforge.plugins import BasePlugin, event_priority

from .config import OfflineConfig

# -----------------------------------------------------------------------------
# Classes
# -----------------------------------------------------------------------------

# Offline plugin
class OfflinePlugin(BasePlugin[OfflineConfig]):

    # Set configuration for offline build
    def on_config(self, config):
        if not self.config.enabled:
            return

        # Ensure correct resolution of links when viewing the site from the
        # file system by disabling directory URLs
        config.use_directory_urls = False

        # Append iframe-worker to polyfills/shims
        config.extra["polyfills"] = config.extra.get("polyfills", [])
        if not any("iframe-worker" in url for url in config.extra["polyfills"]):
            script = "https://unpkg.com/iframe-worker/shim"
            config.extra["polyfills"].append(script)

    # Add support for offline search (run latest) - the search index is copied
    # and inlined into a script, so that it can be used without a server
    @event_priority(-100)
    def on_post_build(self, *, config):
        if not self.config.enabled:
            return

        # Ensure presence of search index
        path = os.path.join(config.site_dir, "search")
        file = os.path.join(path, "search_index.json")
        if not os.path.isfile(file):
            return

        # Obtain search index contents
        with open(file, encoding = "utf-8") as f:
            data = f.read()

        # Inline search index contents into script
        file = os.path.join(path, "search_index.js")
        with open(file, "w", encoding = "utf-8") as f:
            f.write(f"var __index = {data}")
