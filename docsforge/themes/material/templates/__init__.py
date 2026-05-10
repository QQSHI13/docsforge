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
import sys

from colorama import Fore, Style
from pathlib import Path
from sys import stderr

# Check if we're running MkDocs. Disable the warning automatically for other
# contexts, e.g., to allow for forks of MkDocs to adjust behavior to fit
def is_mkdocs():
    path = Path(sys.argv[0])
    return path.name in ("mkdocs", "mkdocs.exe") or (
        path.name == "__main__.py" and path.parent.name == "mkdocs"
    )

# Check if we're running MkDocs and the warning hasn't been disabled
if is_mkdocs() and not os.getenv("NO_MKDOCS_2_WARNING"):
    print(
        "\n"
        f"{Fore.RED} │  ⚠  Warning from the Material for MkDocs team{Style.RESET_ALL}\n"
        f"{Fore.RED} │{Style.RESET_ALL}\n"
        f"{Fore.RED} │{Style.RESET_ALL}  MkDocs 2.0, the underlying framework of Material for MkDocs,\n"
        f"{Fore.RED} │{Style.RESET_ALL}  will introduce backward-incompatible changes, including:\n"
        f"{Fore.RED} │{Style.RESET_ALL}\n"
        f"{Fore.RED} │  × {Style.RESET_ALL}All plugins will stop working – the plugin system has been removed\n"
        f"{Fore.RED} │  × {Style.RESET_ALL}All theme overrides will break – the theming system has been rewritten\n"
        f"{Fore.RED} │  × {Style.RESET_ALL}No migration path exists – existing projects cannot be upgraded\n"
        f"{Fore.RED} │  × {Style.RESET_ALL}Closed contribution model – community members can't report bugs\n"
        f"{Fore.RED} │  × {Style.RESET_ALL}Currently unlicensed – unsuitable for production use\n"
        f"{Fore.RED} │{Style.RESET_ALL}\n"
        f"{Fore.RED} │{Style.RESET_ALL}  Our full analysis:\n"
        f"{Fore.RED} │{Style.RESET_ALL}\n"
        f"{Fore.RED} │{Style.RESET_ALL}  \033[4mhttps://squidfunk.github.io/mkdocs-material/blog/2026/02/18/mkdocs-2.0/{Style.RESET_ALL}\n"
        f"{Style.RESET_ALL}",
        file=stderr
    )

# Disable for subsequent imports
os.environ["NO_MKDOCS_2_WARNING"] = "true"
