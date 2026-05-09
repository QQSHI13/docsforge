#!/usr/bin/env bash
# Complete dependency elimination - surgical approach
set -euo pipefail

cd /home/qq/.openclaw/workspace/projects/docsforge

echo "=== Step 1: Remove vendored duplicates and shims ==="
rm -rf docsforge/mkdocs_vendored docsforge/properdocs_vendored
rm -f docsforge/mkdocs_shim.py docsforge/properdocs_shim.py

echo "=== Step 2: Recover properdocs plugins.py ==="
# Get it from git (it was in the initial merge before plugins/ dir was created)
git show 0a60acd:docsforge/plugins.py > docsforge/properdocs_plugins.py 2>/dev/null || \
git show master~5:docsforge/plugins.py > docsforge/properdocs_plugins.py 2>/dev/null || \
# If not in git, we need another source
{ echo "ERROR: Cannot find original plugins.py"; exit 1; }

# Fix imports in the recovered plugins.py
sed -i \
    -e 's/from properdocs\./from docsforge./g' \
    -e 's/import properdocs\./import docsforge./g' \
    docsforge/properdocs_plugins.py

echo "=== Step 3: Update plugins/__init__.py ==="
cat > docsforge/plugins/__init__.py << 'EOF'
# Copyright (c) 2016-2025 Martin Donath <martin.donath@squidfunk.com>

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

# Re-export ProperDocs plugin system
from docsforge.properdocs_plugins import (
    BasePlugin,
    CombinedEvent,
    Config,
    EVENTS,
    LegacyConfig,
    PlainConfigSchema,
    PluginCollection,
    PrefixedLogger,
    SomeConfig,
    event_priority,
    get_plugin_logger,
    get_plugins,
)
EOF

echo "=== Step 4: Check what mkdocs modules we need ==="
# Find all mkdocs imports in Material plugins
find docsforge/plugins -name "*.py" -exec grep -l "from mkdocs" {} \; > /tmp/mkdocs_needs.txt
cat /tmp/mkdocs_needs.txt

echo "=== Step 5: Create mkdocs compat package ==="
mkdir -p docsforge/mkdocs_compat

# Copy essential mkdocs modules from system install
python3 -c "
import mkdocs
import os
import shutil

mkdocs_dir = mkdocs.__path__[0]
files_to_copy = [
    'theme.py', 'exceptions.py', 'plugins.py', 'utils/__init__.py',
    'utils/meta.py', 'utils/templates.py', 'utils/yaml.py',
    'config/base.py', 'config/config_options.py', 'config/defaults.py',
    'structure/pages.py', 'structure/files.py', 'structure/nav.py',
    'structure/toc.py', 'livereload.py'
]

target = 'docsforge/mkdocs_compat'
for f in files_to_copy:
    src = os.path.join(mkdocs_dir, f)
    dst = os.path.join(target, f)
    if os.path.exists(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        print(f'Copied {f}')
    else:
        print(f'MISSING: {f}')
" 2>&1

# Fix imports in mkdocs compat
find docsforge/mkdocs_compat -name "*.py" -exec sed -i \
    -e 's/from mkdocs\./from docsforge.mkdocs_compat./g' \
    -e 's/import mkdocs\./import docsforge.mkdocs_compat./g' \
    {} +

echo "=== Step 6: Update all Material plugin imports ==="
find docsforge/plugins -name "*.py" -exec sed -i \
    -e 's/from mkdocs\./from docsforge.mkdocs_compat./g' \
    -e 's/import mkdocs\./import docsforge.mkdocs_compat./g' \
    {} +

# Also fix extensions and overrides
find docsforge/extensions -name "*.py" -exec sed -i \
    -e 's/from mkdocs\./from docsforge.mkdocs_compat./g' \
    -e 's/import mkdocs\./import docsforge.mkdocs_compat./g' \
    {} +

find docsforge/overrides -name "*.py" -exec sed -i \
    -e 's/from mkdocs\./from docsforge.mkdocs_compat./g' \
    -e 's/import mkdocs\./import docsforge.mkdocs_compat./g' \
    {} +

echo "=== Done ==="
echo "Now run: pip uninstall mkdocs properdocs -y && pip install -e ."
