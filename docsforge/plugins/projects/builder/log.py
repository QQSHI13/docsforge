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

from click import style
from logging import Filter
from docsforge.plugins.projects.structure import Project
from docsforge.__main__ import ColorFormatter

# -----------------------------------------------------------------------------
# Classes
# -----------------------------------------------------------------------------

# Dirty build warning filter
class ProjectsFilter(Filter):

    # Filter log messages
    def filter(self, record):
        message = record.getMessage()
        return not message.startswith("A 'dirty' build")

# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------

# Retrieve logger for project
def get_log_for(project: Project):
    log = logging.getLogger("".join(["mkdocs.material.projects", project.slug]))

    # Ensure logger does not propagate messags to parent logger, or messages
    # will be printed multiple times, and attach handler with color formatter
    log.propagate = False
    if not log.hasHandlers():
        log.addHandler(get_log_handler(project))
        log.setLevel(get_log_level_for(project))

    # Return logger
    return log

# Retrieve log level for project
def get_log_level_for(project: Project):
    level = logging.INFO

    # Determine log level as set in MkDocs - if the build is started with the
    # `--quiet` flag, the log level is set to `ERROR` to suppress all messages,
    # except for errors. If it's started with `--verbose`, MkDocs sets the log
    # level to `DEBUG`, the most verbose of all log levels.
    log = logging.getLogger("mkdocs")
    for handler in log.handlers:
        level = handler.level
        break

    # Determine if MkDocs was invoked with the `--quiet` flag and the log level
    # as configured in the plugin configuration. When `--quiet` is set, or the
    # projects plugin configuration disables logging, ignore the configured log
    # level and set it to `ERROR` to suppress all messages.
    quiet = level == logging.ERROR
    level = project.plugin.log_level.upper()
    if quiet or not project.plugin.log:
        level = logging.ERROR

    # Retun log level
    return level

# -----------------------------------------------------------------------------

# Retrieve log handler for project
def get_log_handler(project: Project):
    handler = logging.StreamHandler()
    handler.setFormatter(get_log_formatter(project))

    # Add filter to suppress dirty build warning, or we'll get as many of those
    # as projects are built - one warning is surely enough, KTHXBYE
    handler.addFilter(ProjectsFilter())
    return handler

# Retrieve log formatter for project
def get_log_formatter(project: Project):
    prefix = style(f"project://{project.slug}", underline = True)
    return ColorFormatter(f"[{prefix}] %(message)s")
