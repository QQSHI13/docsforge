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

import json
import os

from collections.abc import Iterable
from docsforge.plugins.tags.config import TagsConfig
from docsforge.plugins.tags.structure.mapping import Mapping
from docsforge.plugins.tags.structure.tag import Tag
from docsforge.config.base import ValidationError
from docsforge.structure.nav import Link
from docsforge.structure.pages import Page

# -----------------------------------------------------------------------------
# Classes
# -----------------------------------------------------------------------------

class MappingStorage:
    """
    A mapping storage.

    The mapping storage allows to save and load mappings to and from a JSON
    file, which allows for sharing tags across multiple MkDocs projects.
    """

    def __init__(self, config: TagsConfig):
        """
        Initialize the mapping storage.

        Arguments:
            config: The configuration.
        """
        self.config = config

    # -------------------------------------------------------------------------

    config: TagsConfig
    """
    The configuration.
    """

    # -------------------------------------------------------------------------

    def save(self, path: str, mappings: Iterable[Mapping]) -> None:
        """
        Save mappings to file.

        Arguments:
            path: The file path.
            mappings: The mappings.
        """
        path = os.path.abspath(path)
        os.makedirs(os.path.dirname(path), exist_ok = True)

        # Save serialized mappings to file
        with open(path, "w", encoding = "utf-8") as f:
            data = [_mapping_to_json(mapping) for mapping in mappings]
            json.dump(dict(mappings = data), f)

    def load(self, path: str) -> Iterable[Mapping]:
        """
        Load mappings from file.

        Arguments:
            path: The file path.

        Yields:
            The current mapping.
        """
        with open(path, "r", encoding = "utf-8") as f:
            data = json.load(f)

            # Ensure root dictionary
            if not isinstance(data, dict):
                raise ValidationError(
                    f"Expected dictionary, but received: {data}"
                )

            # Ensure mappings are iterable
            mappings = data.get("mappings")
            if not isinstance(mappings, list):
                raise ValidationError(
                    f"Expected list, but received: {mappings}"
                )

            # Create and yield mappings
            for mapping in mappings:
                yield _mapping_from_json(mapping)

# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------

def _mapping_to_json(mapping: Mapping) -> dict:
    """
    Return a serializable representation of a mapping.

    Arguments:
        mapping: The mapping.

    Returns:
        Serializable representation.
    """
    return dict(
        item = _mapping_item_to_json(mapping.item),
        tags = [str(tag) for tag in sorted(mapping.tags)]
    )

def _mapping_item_to_json(item: Page | Link) -> dict:
    """
    Return a serializable representation of a page or link.

    Arguments:
        item: The page or link.

    Returns:
        Serializable representation.
    """
    return dict(url = item.url, title = item.title)

# -------------------------------------------------------------------------

def _mapping_from_json(data: object) -> Mapping:
    """
    Return a mapping from a serialized representation.

    Arguments:
        data: Serialized representation.

    Returns:
        The mapping.
    """
    if not isinstance(data, dict):
        raise ValidationError(
            f"Expected dictionary, but received: {data}"
        )

    # Ensure tags are iterable
    tags = data.get("tags")
    if not isinstance(tags, list):
        raise ValidationError(
            f"Expected list, but received: {tags}"
        )

    # Ensure tags are valid
    for tag in tags:
        if not isinstance(tag, str):
            raise ValidationError(
                f"Expected string, but received: {tag}"
            )

    # Create and return mapping
    return Mapping(
        _mapping_item_from_json(data.get("item")),
        tags = [Tag(tag) for tag in tags]
    )

def _mapping_item_from_json(data: object) -> Link:
    """
    Return a link from a serialized representation.

    When loading a mapping, we must always return a link, as the sources of
    pages might not be available because we're building another project.

    Arguments:
        data: Serialized representation.

    Returns:
        The link.
    """
    if not isinstance(data, dict):
        raise ValidationError(
            f"Expected dictionary, but received: {data}"
        )

    # Ensure item has URL
    url = data.get("url")
    if not isinstance(url, str):
        raise ValidationError(
            f"Expected string, but received: {url}"
        )

    # Ensure item has title
    title = data.get("title")
    if not isinstance(title, str):
        raise ValidationError(
            f"Expected string, but received: {title}"
        )

    # Create and return item
    return Link(title, url)
