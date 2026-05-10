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

from collections.abc import Callable
from docsforge.plugins.projects.structure import Project
from watchdog.events import FileSystemEvent, FileSystemEventHandler

# -----------------------------------------------------------------------------
# Classes
# -----------------------------------------------------------------------------

# Project changed
class ProjectChanged(FileSystemEventHandler):

    # Initialize event handler
    def __init__(self, project: Project, handler: Callable):
        self.project = project
        self.handler = handler

    # Handle file event
    def on_any_event(self, event: FileSystemEvent):
        self._handle(event)

    # -------------------------------------------------------------------------

    # Invoke file event handler
    def _handle(self, event: FileSystemEvent):
        config = self.project.config

        # Resolve path to docs directory
        base = os.path.dirname(config.config_file_path)
        docs = os.path.join(base, config.docs_dir)

        # Resolve project root and path to changed file
        root = os.path.relpath(base)
        path = os.path.relpath(event.src_path, root)

        # Check if mkdocs.yml or docs directory was deleted
        if event.src_path in [docs, config.config_file_path]:
            if event.event_type == "deleted":
                return

        # Invoke handler and print message that we're scheduling a build
        log.info(f"Schedule build due to '{path}' in '{root}'")
        self.handler(self.project)

# -----------------------------------------------------------------------------

# Project added or removed
class ProjectAddedOrRemoved(FileSystemEventHandler):

    # Initialize event handler
    def __init__(self, project: Project, handler: Callable):
        self.project = project
        self.handler = handler

    # Handle file creation event
    def on_created(self, event: FileSystemEvent):
        self._handle(event)

    # Handle file deletion event
    def on_deleted(self, event: FileSystemEvent):
        self._handle(event)

    # ------------------------------------------------------------------------

    # Invoke file event handler
    def _handle(self, event: FileSystemEvent):
        config = self.project.config

        # Touch mkdocs.yml to trigger rebuild
        if os.path.isfile(config.config_file_path):
            os.utime(config.config_file_path, None)

        # Invoke handler
        self.handler(self.project)

# -----------------------------------------------------------------------------
# Data
# -----------------------------------------------------------------------------

# Set up logging
log = logging.getLogger("mkdocs")
