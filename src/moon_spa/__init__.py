"""Main package for the moon-spa framework.

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

from moon_spa.app import create_default_framework
from moon_spa.framework import SpaFramework
from moon_spa.types import ClientMethods, Component, ComponentDefinition, StateField

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
