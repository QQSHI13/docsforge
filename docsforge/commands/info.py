"""DocsForge info command - system information for debugging."""

from __future__ import annotations

import logging
import os
import sys

from docsforge import __version__

log = logging.getLogger(__name__)


def info() -> None:
    """Display system information for debugging."""
    print()
    print("=" * 60)
    print("  DOCSFORGE SYSTEM INFORMATION")
    print("=" * 60)
    print()
    
    # Version info
    print(f"  DocsForge version:   {__version__}")
    print(f"  Python version:      {sys.version}")
    print(f"  Platform:            {sys.platform}")
    print()
    
    # Paths
    import docsforge
    pkg_dir = os.path.dirname(os.path.abspath(docsforge.__file__))
    print(f"  Package directory:   {pkg_dir}")
    print(f"  Working directory:   {os.getcwd()}")
    print()
    
    # Config files
    print("  Configuration files:")
    for name in ['docsforge.yml', 'docsforge.yaml', 'mkdocs.yml', 'mkdocs.yaml']:
        status = "✓ found" if os.path.exists(name) else "not found"
        print(f"    {name:20} {status}")
    print()
    
    # Themes
    print("  Available themes:")
    from docsforge.utils import get_theme_names
    for theme in get_theme_names():
        print(f"    {theme}")
    print()
    
    # Plugins
    print("  Built-in plugins:")
    builtin_plugins = [
        'search', 'tags', 'blog', 'info', 'meta', 'minify',
        'privacy', 'social', 'offline', 'optimize', 'typeset'
    ]
    for plugin in builtin_plugins:
        print(f"    {plugin}")
    print()
    
    # Installed plugins
    print("  Installed third-party plugins:")
    from docsforge.plugins.base import get_plugins
    try:
        plugins = get_plugins()
        third_party = [name for name in plugins if name not in builtin_plugins]
        if third_party:
            for plugin in third_party:
                print(f"    {plugin}")
        else:
            print("    (none)")
    except Exception as e:
        print(f"    Could not enumerate: {e}")
    print()
    
    # Markdown extensions
    print("  Pre-configured Markdown extensions:")
    extensions = [
        'pymdownx.superfences', 'pymdownx.tabbed', 'pymdownx.details',
        'pymdownx.tasklist', 'pymdownx.keys', 'pymdownx.mark',
        'pymdownx.tilde', 'pymdownx.caret', 'pymdownx.smartsymbols',
        'pymdownx.highlight', 'pymdownx.inlinehilite', 'pymdownx.snippets',
        'pymdownx.betterem', 'pymdownx.magiclink', 'pymdownx.arithmatex',
        'tables', 'footnotes', 'admonition', 'toc', 'abbr',
    ]
    for ext in extensions:
        print(f"    {ext}")
    print()
    
    # Features
    print("  Feature support:")
    
    # Check for TikZ
    tikz_available = False
    try:
        import subprocess
        result = subprocess.run(['which', 'pdflatex'], capture_output=True, text=True)
        tikz_available = result.returncode == 0
    except Exception:
        pass
    print(f"    TikZ diagrams:       {'✓ pdflatex found' if tikz_available else '✗ pdflatex not found (install TeX Live for TikZ)'}")
    
    # Check for lunr
    try:
        import lunr
        print(f"    Lunr.py search:      ✓")
    except ImportError:
        print(f"    Lunr.py search:      ✗ (optional, JS search still works)")
    
    print()
    print("=" * 60)
    print()
