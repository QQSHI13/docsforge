# Makes import mkdocs/properdocs work by adding them to sys.modules
import sys

# Redirect mkdocs.* and properdocs.* imports to docsforge.*
sys.modules['mkdocs'] = sys.modules['docsforge']
sys.modules['properdocs'] = sys.modules['docsforge']
