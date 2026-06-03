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

from docsforge.core.tags.structure.tag import Tag
from docsforge.nav import Link

# -----------------------------------------------------------------------------
# Classes
# -----------------------------------------------------------------------------

class TagReference(Tag):
    """
    A tag reference.

    Tag references are a subclass of tags that can have associated links, which
    is primarily used for linking tags to listings. The first link is used as
    the canonical link, which by default points to the closest listing that
    features the tag. This is considered to be the canonical listing.
    """

    def __init__(self, tag: Tag, links: list[Link] | None = None):
        """
        Initialize the tag reference.

        Arguments:
            tag: The tag.
            links: The links associated with the tag.
        """
        super().__init__(**vars(tag))
        self.links = links or []

    def __repr__(self) -> str:
        """
        Return a printable representation of the tag reference.

        Returns:
            Printable representation.
        """
        return f"TagReference('{self.name}')"

    # -------------------------------------------------------------------------

    links: list[Link]
    """
    The links associated with the tag.
    """

    # -------------------------------------------------------------------------

    @property
    def url(self) -> str | None:
        """
        Return the URL of the tag reference.

        Returns:
            The URL of the tag reference.
        """
        if self.links:
            return self.links[0].url
        else:
            return None
