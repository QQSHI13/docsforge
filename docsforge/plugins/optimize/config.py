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
from docsforge.config.config_options import ListOfItems, Type

# -----------------------------------------------------------------------------
# Classes
# -----------------------------------------------------------------------------

# Optimize plugin configuration
class OptimizeConfig(Config):
    enabled = Type(bool, default = True)
    concurrency = Type(int, default = max(1, os.cpu_count() - 1))

    # Settings for caching
    cache = Type(bool, default = True)
    cache_dir = Type(str, default = ".cache/plugin/optimize")

    # Settings for optimization
    optimize = Type(bool, default = True)
    optimize_png = Type(bool, default = True)
    optimize_png_speed = Type(int, default = 3)
    optimize_png_strip = Type(bool, default = True)
    optimize_jpg = Type(bool, default = True)
    optimize_jpg_quality = Type(int, default = 60)
    optimize_jpg_progressive = Type(bool, default = True)
    optimize_include = ListOfItems(Type(str), default = [])
    optimize_exclude = ListOfItems(Type(str), default = [])

    # Settings for reporting
    print_gain = Type(bool, default = True)
    print_gain_summary = Type(bool, default = True)
