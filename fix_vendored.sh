#!/usr/bin/env bash
# Fix vendored code internal imports
set -euo pipefail

cd /home/qq/.openclaw/workspace/projects/docsforge

echo "=== Fix vendored properdocs internal imports ==="
find docsforge/properdocs_vendored -name "*.py" -exec sed -i \
    -e 's/from properdocs\./from docsforge.properdocs_vendored./g' \
    -e 's/import properdocs\./import docsforge.properdocs_vendored./g' \
    -e 's/from properdocs import/from docsforge.properdocs_vendored import/g' \
    {} +

echo "=== Fix vendored mkdocs internal imports ==="
find docsforge/mkdocs_vendored -name "*.py" -exec sed -i \
    -e 's/from mkdocs\./from docsforge.mkdocs_vendored./g' \
    -e 's/import mkdocs\./import docsforge.mkdocs_vendored./g' \
    -e 's/from mkdocs import/from docsforge.mkdocs_vendored import/g' \
    {} +

echo "=== Fix config_options.py mkdocs reference ==="
sed -i 's/import mkdocs\.plugins/import docsforge.mkdocs_vendored.plugins/g' docsforge/config/config_options.py

echo "=== Done ==="
