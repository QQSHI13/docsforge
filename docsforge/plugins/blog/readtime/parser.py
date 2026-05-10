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

from html.parser import HTMLParser

# TODO: Refactor the `void` set into a common module and import it from there
# and not from the search plugin.
from docsforge.plugins.search.plugin import void

# -----------------------------------------------------------------------------
# Classes
# -----------------------------------------------------------------------------

# Readtime parser
class ReadtimeParser(HTMLParser):

    # Initialize parser
    def __init__(self):
        super().__init__(convert_charrefs = True)

        # Tags to skip
        self.skip = set([
            "object",                  # Objects
            "script",                  # Scripts
            "style",                   # Styles
            "svg"                      # SVGs
        ])

        # Current context
        self.context = []

        # Keep track of text and images
        self.text   = []
        self.images = 0

    # Called at the start of every HTML tag
    def handle_starttag(self, tag, attrs):
        # Collect images
        if tag == "img":
            self.images += 1

        # Ignore self-closing tags
        if tag not in void:
            # Add tag to context
            self.context.append(tag)

    # Called for the text contents of each tag
    def handle_data(self, data):
        # Collect text if not inside skip context
        if not self.skip.intersection(self.context):
            self.text.append(data)

    # Called at the end of every HTML tag
    def handle_endtag(self, tag):
        if self.context and self.context[-1] == tag:
            # Remove tag from context
            self.context.pop()
