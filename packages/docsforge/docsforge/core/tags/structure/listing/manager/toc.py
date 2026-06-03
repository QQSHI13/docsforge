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

from docsforge.core.tags.structure.listing import Listing
from docsforge.core.tags.structure.tag import Tag
from docsforge.pages import Page
from docsforge.toc import AnchorLink
from typing import Callable

# -----------------------------------------------------------------------------
# Typings
# -----------------------------------------------------------------------------

Slugify = Callable[[Tag], str]
"""
Slugify function.

Arguments:
    tag: The tag.

Returns:
    The slugified tag.
"""

# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------

def populate(listing: Listing, slugify: Slugify) -> dict[Tag, AnchorLink]:
    """
    Populate the table of contents of the page the listing is embedded.

    Arguments:
        listing: The listing.
        slugify: Slugify function.

    Returns:
        The mapping of tags to anchor links.
    """
    anchors: dict[Tag, AnchorLink] = {}

    # Find injection point for listing
    host, at = find(listing)
    if at == -1:
        return anchors

    # Create anchor links
    for tree in listing:

        # Iterate over expanded tags
        for i, tag in enumerate(reversed([*tree.tag])):
            if tag not in anchors:
                level = host.level + 1 + i

                # Create anchor link
                anchors[tag] = AnchorLink(tag.name, slugify(tag), level)
                if not tag.parent:
                    continue

                # Relate anchor link to parent
                anchors[tag.parent].children.append(anchors[tag])

    # Filter top-level anchor links and insert them into the page
    children = [anchors[tag] for tag in anchors if not tag.parent]
    if listing.config.toc:
        host.children[at:at + 1] = children
    else:
        host.children.pop(at)

    # Return mapping of tags to anchor links
    return anchors

# -----------------------------------------------------------------------------

def find(listing: Listing) -> tuple[AnchorLink | None, int]:
    """
    Find anchor link for the given listing.

    This function traverses the table of contents of the given page and returns
    the anchor's parent and index of the anchor with the given identifier. If
    the anchor is on the root level, and the anchor we're looking for is an
    injection point, an anchor to host the tags is created and returned.

    Arguments:
        lising: The listing.

    Returns:
        The anchor and index.
    """
    page = listing.page

    # Traverse table of contents
    stack = list(page.toc)
    while stack:
        anchor = stack.pop()

        # Traverse children
        for i, child in enumerate(anchor.children):
            if child.id.startswith(listing.id):
                return anchor, i

            # Add child to stack
            stack.append(child)

    # Check if anchor is on the root level
    for i, anchor in enumerate(page.toc):
        if anchor.id.startswith(listing.id):

            # Create anchor link
            host = AnchorLink(page.title, page.url, 1)
            host.children = page.toc.items
            return host, i

    # Anchor could not be found
    return None, -1
