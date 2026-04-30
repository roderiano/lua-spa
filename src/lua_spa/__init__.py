"""Main package for the lua-spa framework.

Core modules:
  - framework: SpaFramework, main entry point for the backend
  - types: ViewConfig, ComponentDefinition, StateField, Component, ClientMethods
  - loader: ComponentLoader for parsing .lspa files
  - renderer: Template interpolation and server-side rendering
  - codegen: Client-side JavaScript code generation
  - scope: Python component execution and spec normalization
  - trace: State mutation and property access tracing
  - server: HTTP server for serving the SPA
"""

from lua_spa.app import create_default_framework
from lua_spa.framework import SpaFramework
from lua_spa.types import ClientMethods, Component, ComponentDefinition, StateField

__all__ = [
    "SpaFramework",
    "create_default_framework",
    "Component",
    "ClientMethods",
    "ComponentDefinition",
    "StateField",
    "__version__",
]
__version__ = "0.1.0"
