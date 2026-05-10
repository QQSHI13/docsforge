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

import functools
import docsforge
import os

from glob import iglob
from inspect import getfile
from markdown import Markdown
from pymdownx import emoji, twemoji_db
from xml.etree.ElementTree import Element

# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------

# Create twemoji index
def twemoji(options: object, md: Markdown):
    paths = options.get("custom_icons", [])[:]
    return _load_twemoji_index(tuple(paths))

# Create emoji or icon
def to_svg(
    index: str, shortname: str, alias: str, uc: str | None, alt: str,
    title: str, category: str, options: object, md: Markdown
):
    if not uc:
        icons = md.inlinePatterns["emoji"].emoji_index["emoji"]

        # Create and return element to host icon
        el = Element("span", { "class": options.get("classes", index) })
        el.text = md.htmlStash.store(_load(icons[shortname]["path"]))
        return el

    # Delegate to `pymdownx.emoji` extension
    return emoji.to_svg(
        index, shortname, alias, uc, alt, title, category, options, md
    )

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------

# Load icon
@functools.lru_cache(maxsize = None)
def _load(file: str):
    with open(file, encoding = "utf-8") as f:
        return f.read()

# Load twemoji index and add icons
@functools.lru_cache(maxsize = None)
def _load_twemoji_index(paths):
    index = {
        "name": "twemoji",
        "emoji": twemoji_db.emoji,
        "aliases": twemoji_db.aliases
    }

    # Compute path to theme root and traverse all icon directories
    root = os.path.dirname(getfile(docsforge))
    root = os.path.join(root, "themes", "material", "templates", ".icons")
    for path in [*paths, root]:
        base = os.path.normpath(path)

        # Index icons provided by the theme and via custom icons
        glob = os.path.join(base, "**", "*.svg")
        glob = iglob(os.path.normpath(glob), recursive = True)
        for file in glob:
            icon = file[len(base) + 1:-4].replace(os.path.sep, "-")

            # Add icon to index
            name = f":{icon}:"
            if not any(name in index[key] for key in ["emoji", "aliases"]):
                index["emoji"][name] = { "name": name, "path": file }

    # Return index
    return index
