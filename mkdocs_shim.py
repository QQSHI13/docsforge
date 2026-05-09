"""Compatibility shim: mkdocs module redirects to docsforge."""

import sys
import importlib

# When someone imports 'mkdocs', redirect them to 'docsforge'
class MkdocsShim:
    """Makes `import mkdocs` work and redirects to docsforge."""
    
    def __init__(self):
        # Import docsforge and expose all its attributes
        self._docsforge = importlib.import_module('docsforge')
    
    def __getattr__(self, name):
        return getattr(self._docsforge, name)

# Install the shim in sys.modules
sys.modules['mkdocs'] = MkdocsShim()
