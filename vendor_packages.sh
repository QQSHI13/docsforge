#!/usr/bin/env bash
# Create proper vendor packages with working module paths
set -euo pipefail

cd /home/qq/.openclaw/workspace/projects/docsforge
source venv/bin/activate

echo "=== Step 1: Clean up old attempts ==="
rm -rf docsforge/mkdocs_vendored docsforge/properdocs_vendored
rm -f docsforge/mkdocs_shim.py docsforge/properdocs_shim.py

# Reinstall temporarily to get source
pip install mkdocs properdocs 2>&1 | tail -3

echo "=== Step 2: Vendor mkdocs ==="
python3 -c "
import mkdocs, shutil, os
src = mkdocs.__path__[0]
dst = 'docsforge/_vendor/mkdocs'
shutil.copytree(src, dst, dirs_exist_ok=True)
print(f'Vendored mkdocs from {src} to {dst}')
"

echo "=== Step 3: Vendor properdocs ==="
python3 -c "
import properdocs, shutil, os
src = properdocs.__path__[0]
dst = 'docsforge/_vendor/properdocs'
shutil.copytree(src, dst, dirs_exist_ok=True)
print(f'Vendored properdocs from {src} to {dst}')
"

echo "=== Step 4: Fix vendored internal imports ==="
# mkdocs internal references
find docsforge/_vendor/mkdocs -name "*.py" -exec sed -i \
    -e 's/from mkdocs\./from docsforge._vendor.mkdocs./g' \
    -e 's/import mkdocs\./import docsforge._vendor.mkdocs./g' \
    {} +

# properdocs internal references  
find docsforge/_vendor/properdocs -name "*.py" -exec sed -i \
    -e 's/from properdocs\./from docsforge._vendor.properdocs./g' \
    -e 's/import properdocs\./import docsforge._vendor.properdocs./g' \
    {} +

echo "=== Step 5: Fix docsforge code to use vendored packages ==="
# All code in docsforge/ should use vendored packages
find docsforge -name "*.py" -not -path "*/_vendor/*" -exec sed -i \
    -e 's/from mkdocs\./from docsforge._vendor.mkdocs./g' \
    -e 's/import mkdocs\./import docsforge._vendor.mkdocs./g' \
    -e 's/from properdocs\./from docsforge._vendor.properdocs./g' \
    -e 's/import properdocs\./import docsforge._vendor.properdocs./g' \
    {} +

echo "=== Step 6: Create top-level shims ==="
# These make 'import mkdocs' and 'import properdocs' work globally
mkdir -p docsforge/_vendor_shims
cat > docsforge/_vendor_shims/__init__.py << 'EOF'
# Makes import mkdocs/properdocs work by adding them to sys.modules
import sys
from docsforge._vendor import mkdocs, properdocs
sys.modules['mkdocs'] = mkdocs
sys.modules['properdocs'] = properdocs
EOF

echo "=== Step 7: Ensure shims loaded on docsforge import ==="
# Add to docsforge/__init__.py
cat >> docsforge/__init__.py << 'EOF'

# Install vendor compatibility shims
import docsforge._vendor_shims
EOF

echo "=== Step 8: Uninstall external packages ==="
pip uninstall mkdocs properdocs mkdocs-get-deps -y 2>&1 | tail -5

echo "=== Step 9: Reinstall docsforge ==="
pip install -e . 2>&1 | tail -5

echo "=== Done ==="
echo "Testing imports..."
python3 -c "
import docsforge
from docsforge._vendor.mkdocs.theme import Theme
from docsforge._vendor.properdocs.plugins import BasePlugin
from docsforge.__main__ import cli
print('All imports OK!')
"
