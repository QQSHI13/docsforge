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

from markdown.treeprocessors import Treeprocessor
from docsforge.pages import Page
from docsforge.utils import get_relative_url
from xml.etree.ElementTree import Element

# -----------------------------------------------------------------------------
# Classes
# -----------------------------------------------------------------------------

# Excerpt tree processor
class ExcerptTreeprocessor(Treeprocessor):

    # Initialize excerpt tree processor
    def __init__(self, page: Page, base: Page | None = None):
        self.page = page
        self.base = base

    # Transform HTML after Markdown processing
    def run(self, root: Element):
        assert self.base
        main = True

        # We're only interested in anchors, which is why we continue when the
        # link does not start with an anchor tag
        for el in root.iter("a"):
            anchor = el.get("href")
            if not anchor.startswith("#"):
                continue

            # The main headline should link to the post page, not to a specific
            # anchor, which is why we remove the anchor in that case
            path = get_relative_url(self.page.url, self.base.url)
            if main:
                el.set("href", path)
            else:
                el.set("href", path + anchor)

            # Main headline has been seen
            main = False
