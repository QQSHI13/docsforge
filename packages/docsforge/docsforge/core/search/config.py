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

from docsforge.config_options import (
    Choice,
    Deprecated,
    Optional,
    ListOfItems,
    Type
)
from docsforge.config_base import Config
from docsforge.core.search.lang import LangOption

# -----------------------------------------------------------------------------
# Options
# -----------------------------------------------------------------------------

# Options for search pipeline
pipeline = ("stemmer", "stopWordFilter", "trimmer")

# -----------------------------------------------------------------------------
# Classes
# -----------------------------------------------------------------------------

# Search field configuration
class SearchFieldConfig(Config):
    boost = Type((int, float), default = 1.0)

# Search plugin configuration
class SearchConfig(Config):
    enabled = Type(bool, default = True)

    # Settings for search
    lang = Optional(LangOption())
    separator = Optional(Type(str))
    pipeline = Optional(ListOfItems(Choice(pipeline)))
    fields = Type(dict, default = {})

    # Settings for text segmentation (Chinese)
    jieba_dict = Optional(Type(str))
    jieba_dict_user = Optional(Type(str))

    # Unsupported settings, originally implemented in MkDocs
    indexing = Deprecated(message = "Unsupported option")
    prebuild_index = Deprecated(message = "Unsupported option")
    min_search_length = Deprecated(message = "Unsupported option")
