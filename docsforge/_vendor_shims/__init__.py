# Makes import mkdocs/properdocs work by adding them to sys.modules
import sys
from docsforge._vendor import mkdocs, properdocs
sys.modules['mkdocs'] = mkdocs
sys.modules['properdocs'] = properdocs
