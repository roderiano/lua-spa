"""Main package for the lua-spa framework."""

from lua_spa.app import create_default_framework
from lua_spa.framework import SpaFramework

__all__ = ["SpaFramework", "create_default_framework", "__version__"]
__version__ = "0.1.0"
