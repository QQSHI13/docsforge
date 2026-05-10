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

from docsforge.config.base import Config
from docsforge.config.config_options import Deprecated, ListOfItems, Type
from docsforge.config.defaults import _LogLevel

# -----------------------------------------------------------------------------
# Classes
# -----------------------------------------------------------------------------

# Social plugin configuration
class SocialConfig(Config):
    enabled = Type(bool, default = True)
    concurrency = Type(int, default = max(1, os.cpu_count() - 1))

    # Settings for caching
    cache = Type(bool, default = True)
    cache_dir = Type(str, default = ".cache/plugin/social")

    # Settings for logging
    log = Type(bool, default = True)
    log_level = _LogLevel(default = "warn")

    # Settings for cards
    cards = Type(bool, default = True)
    cards_dir = Type(str, default = "assets/images/social")
    cards_layout_dir = Type(str, default = "layouts")
    cards_layout = Type(str, default = "default")
    cards_layout_options = Type(dict, default = {})
    cards_include = ListOfItems(Type(str), default = [])
    cards_exclude = ListOfItems(Type(str), default = [])

    # Settings for debugging
    debug = Type(bool, default = False)
    debug_on_build = Type(bool, default = False)
    debug_grid = Type(bool, default = True)
    debug_grid_step = Type(int, default = 32)
    debug_color = Type(str, default = "grey")

    # Deprecated settings
    cards_color = Deprecated(
        message =
            "Deprecated, use 'cards_layout_options.background_color' "
            "and 'cards_layout_options.color' with 'default' layout"
        )
    cards_font = Deprecated(
        message = "Deprecated, use 'cards_layout_options.font_family'"
    )
