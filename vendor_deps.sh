#!/usr/bin/env bash
# Vendor mkdocs and properdocs into docsforge, eliminating external dependencies
set -euo pipefail

cd /home/qq/.openclaw/workspace/projects/docsforge
source venv/bin/activate

echo "=== Step 1: Copy mkdocs source into docsforge ==="
MKDOCS_SRC=$(python3 -c "import mkdocs; print(mkdocs.__path__[0])")
cp -r "$MKDOCS_SRC" docsforge/mkdocs_vendored

echo "=== Step 2: Copy properdocs source into docsforge ==="
PROPERDOCS_SRC=$(python3 -c "import properdocs; print(properdocs.__path__[0])")
cp -r "$PROPERDOCS_SRC" docsforge/properdocs_vendored

echo "=== Step 3: Global import replacement ==="
# Replace mkdocs.X → docsforge.X in all docsforge files (except the vendored dirs)
find docsforge -name "*.py" -not -path "*/mkdocs_vendored/*" -not -path "*/properdocs_vendored/*" -exec sed -i \
    -e 's/from mkdocs\./from docsforge./g' \
    -e 's/import mkdocs\./import docsforge./g' \
    {} +

echo "=== Step 4: Fix docsforge internal references ==="
# Now fix the vendored code to reference itself
find docsforge/mkdocs_vendored -name "*.py" -exec sed -i \
    -e 's/from mkdocs\./from docsforge.mkdocs_vendored./g' \
    -e 's/import mkdocs\./import docsforge.mkdocs_vendored./g' \
    {} +

find docsforge/properdocs_vendored -name "*.py" -exec sed -i \
    -e 's/from properdocs\./from docsforge.properdocs_vendored./g' \
    -e 's/import properdocs\./import docsforge.properdocs_vendored./g' \
    {} +

echo "=== Step 5: Create shims at docsforge level ==="
cat > docsforge/mkdocs_shim.py << 'EOF'
"""Shim: docsforge acts as mkdocs for backward compatibility."""
import sys
from docsforge import mkdocs_vendored as _mkdocs

# Re-export everything from vendored mkdocs
for attr in dir(_mkdocs):
    if not attr.startswith('_'):
        globals()[attr] = getattr(_mkdocs, attr)

sys.modules['mkdocs'] = sys.modules['docsforge.mkdocs_shim']
EOF

cat > docsforge/properdocs_shim.py << 'EOF'
"""Shim: docsforge acts as properdocs for backward compatibility."""
import sys
from docsforge import properdocs_vendored as _properdocs

# Re-export everything from vendored properdocs
for attr in dir(_properdocs):
    if not attr.startswith('_'):
        globals()[attr] = getattr(_properdocs, attr)

sys.modules['properdocs'] = sys.modules['docsforge.properdocs_shim']
EOF

echo "=== Step 6: Update pyproject.toml to remove external deps ==="
cat > pyproject.toml << 'EOF'
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "docsforge"
description = "Self-contained unified documentation engine with Material theme."
readme = "README.md"
license = "GPL-3.0-or-later"
authors = [{name = "DocsForge Contributors"}]
classifiers = [
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "Environment :: Web Environment",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Documentation",
    "Topic :: Text Processing",
]
dynamic = ["version"]
requires-python = ">=3.10"
dependencies = [
    "click >=7.0",
    "Jinja2 >=2.11.1",
    "markupsafe >=2.0.1",
    "Markdown >=3.3.6",
    "PyYAML >=5.1",
    "watchdog >=2.0",
    "ghp-import >=1.0",
    "pyyaml_env_tag >=0.1",
    "packaging >=20.5",
    "pathspec >=0.11.1",
    "platformdirs >=2.2.0",
    "colorama >=0.4; platform_system == 'Windows'",
    "pymdown-extensions >=10.0",
    "mkdocs-minify-plugin >=0.7",
    "mkdocs-redirects >=1.2",
    "babel >=2.9.0",
]

[project.optional-dependencies]
imaging = ["pillow>=10.2", "cairosvg>=2.6"]

[project.urls]
Documentation = "https://docsforge.readthedocs.io/"
Source = "https://github.com/docsforge/docsforge"
Issues = "https://github.com/docsforge/docsforge/issues"

[project.scripts]
docsforge = "docsforge.__main__:cli"

# All entrypoints point to docsforge internals
[project.entry-points."docsforge.plugins"]
"material/blog" = "docsforge.plugins.blog.plugin:BlogPlugin"
"material/group" = "docsforge.plugins.group.plugin:GroupPlugin"
"material/info" = "docsforge.plugins.info.plugin:InfoPlugin"
"material/meta" = "docsforge.plugins.meta.plugin:MetaPlugin"
"material/offline" = "docsforge.plugins.offline.plugin:OfflinePlugin"
"material/optimize" = "docsforge.plugins.optimize.plugin:OptimizePlugin"
"material/privacy" = "docsforge.plugins.privacy.plugin:PrivacyPlugin"
"material/projects" = "docsforge.plugins.projects.plugin:ProjectsPlugin"
"material/search" = "docsforge.plugins.search.plugin:SearchPlugin"
"material/social" = "docsforge.plugins.social.plugin:SocialPlugin"
"material/tags" = "docsforge.plugins.tags.plugin:TagsPlugin"
"material/typeset" = "docsforge.plugins.typeset.plugin:TypesetPlugin"

[project.entry-points."docsforge.themes"]
material = "docsforge.themes.material.templates"

[tool.hatch.version]
path = "docsforge/__init__.py"

[tool.hatch.build.targets.sdist]
include = ["/docsforge", "/README.md", "/LICENSE"]

[tool.hatch.build.targets.wheel]
include = ["/docsforge"]
EOF

echo "=== Step 7: Update __init__.py to install shims ==="
cat >> docsforge/__init__.py << 'EOF'

# Install backward-compatibility shims
import sys
from docsforge import mkdocs_shim, properdocs_shim
EOF

echo "=== Vendoring complete ==="
echo "Run: pip uninstall mkdocs properdocs -y && pip install -e ."
