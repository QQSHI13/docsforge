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

from collections.abc import Iterable, Iterator
from docsforge.plugins.tags.structure.tag import Tag
from docsforge.structure.nav import Link
from docsforge.structure.pages import Page

# -----------------------------------------------------------------------------
# Classes
# -----------------------------------------------------------------------------

class Mapping:
    """
    A mapping between a page or link and a set of tags.

    We use this class to store the mapping between a page or link and a set of
    tags. This is necessary as we don't want to store the tags directly on the
    page or link object, in order not to clutter the internal data structures
    of MkDocs, keeping the plugin as unobtrusive as possible.

    Links are primarily used when integrating with tags from external projects,
    as we can't construct a page object for them as we do for local files.
    """

    def __init__(self, item: Page | Link, *, tags: Iterable[Tag] | None = None):
        """
        Initialize the mapping.

        Tags can be passed upon initialization, but can also be added later on
        using the `add` or `update` method. of the `tags` attribute.

        Arguments:
            item: The page or link.
            tags: The tags associated with the page or link.
        """
        self.item = item
        self.tags = set(tags or [])

    def __repr__(self) -> str:
        """
        Return a printable representation of the mapping.

        Returns:
            Printable representation.
        """
        return f"Mapping({repr(self.item)}, tags={self.tags})"

    def __and__(self, tags: set[Tag]) -> Iterator[Tag]:
        """
        Iterate over the tags featured in the mapping.

        This method expands each tag in the mapping and checks whether it is
        equal to one of the tags in the given set. If so, the tag is yielded.

        Arguments:
            tags: The set of tags.

        Yields:
            The current tag.
        """
        assert isinstance(tags, set)

        # Iterate over expanded tags
        for tag in self.tags:
            if set(tag) & tags:
                yield tag

    # -------------------------------------------------------------------------

    item: Page | Link
    """
    The page or link.
    """

    tags: set[Tag]
    """
    The tags associated with the page or link.
    """
