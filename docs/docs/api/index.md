---
sidebar_position: 1
---

# API Reference

Complete reference for Lua SPA classes, functions, and types.

## Overview

The Lua SPA framework consists of several key modules:

- **`framework.py`** - Main `SpaFramework` class
- **`types.py`** - Type definitions and base classes
- **`loader.py`** - Component loading
- **`renderer.py`** - Template rendering
- **`codegen.py`** - JavaScript generation
- **`runtime_assets.py`** - Client-side runtime
- **`server.py`** - HTTP server

## Quick Reference

### Framework

```python
from lua_spa.framework import SpaFramework
from pathlib import Path

# Create framework from lua_template directory
framework = SpaFramework.from_lua_template_directory(
    Path("lua_template")
)

# Or create with explicit parameters
framework = SpaFramework(
    view_file=Path("lua_template/index.lspa"),
    components_dir=Path("lua_template/components"),
    entry_component="App",
    mount_id="app",
    default_props={},
    host="127.0.0.1",
    port=8000,
)

# Render and serve
framework.serve()
```

### Component Base Class

```python
from lua_spa.types import Component, ClientMethods

class MyComponent(Component):
    def context(self, props):
        """Server-side data for template."""
        return {}
    
    def client(self):
        """Client-side specification."""
        return {}
```

### Client Methods

```python
from lua_spa.types import ClientMethods

class MyClientClass(ClientMethods):
    # State operations
    def method(self):
        self.add("count", 1)        # Increment
        self.sub("count", 1)        # Decrement
        self.set("count", 0)        # Set value
        self.toggle("is_open")      # Toggle boolean
```

### State Definition

```python
from lua_spa.types import StateField

class MyClient(ClientMethods):
    class CountState:
        name = "count"
        from_prop = "start"
        default = 0
        cast = "int"
    
    State = [CountState]
```

## Modules

### [SpaFramework](./framework.md)

Main orchestrator for the framework.

```python
class SpaFramework:
    @classmethod
    def from_lua_template_directory(cls, lua_template_dir: Path) -> SpaFramework
    
    def __init__(
        self,
        view_file: Path,
        components_dir: Path,
        entry_component: str = "App",
        mount_id: str = "app",
        default_props: Mapping[str, Any] | None = None,
        host: str = "127.0.0.1",
        port: int = 8000,
    ) -> None
    
    def render(self, props: Mapping[str, Any] | None = None) -> str
    
    def serve(self) -> None
```

### [Type Definitions](./types.md)

Core types and configuration classes.

```python
@dataclass(frozen=True)
class LuaTemplateConfig:
    entry_component: str
    mount_id: str
    initial_props: Mapping[str, Any]
    host: str
    port: int

@dataclass(frozen=True)
class ComponentDefinition:
    name: str
    template: str
    client_script: str
    python_block: str
    imports: Mapping[str, str]

@dataclass(frozen=True)
class StateField:
    name: str
    from_prop: str | None = None
    default: Any = None
    cast: str = "raw"

class Component:
    pass

class ClientMethods:
    def add(self, state: str, value: Any = 1) -> dict[str, Any]
    def sub(self, state: str, value: Any = 1) -> dict[str, Any]
    def set(self, state: str, value: Any) -> dict[str, Any]
    def toggle(self, state: str) -> dict[str, Any]
```

### [Component Loader](./loader.md)

Load and parse `.lspa` component files.

```python
class ComponentLoader:
    def __init__(self, components_dir: Path)
    
    def load(self, component_name: str) -> ComponentDefinition
    
    def load_entry(self, component_name: str) -> dict[str, ComponentDefinition]
```

### [Renderer](./renderer.md)

Render templates with data.

```python
def build_python_context(component_def: ComponentDefinition, component_instance: Any, props: dict) -> dict

def interpolate(html: str, context: dict) -> str

def apply_server_conditionals(html: str, context: dict) -> str

def build_server_state(component_def: ComponentDefinition, component_instance: Any) -> dict
```

### [Code Generator](./codegen.md)

Generate JavaScript code for client.

```python
def generate_client_code(component_def: ComponentDefinition, component_instance: Any) -> str
```

### [Scope Execution](./scope.md)

Execute component Python code.

```python
def load_python_scope(python_block: str) -> dict[str, Any]

def resolve_component_instance(local_scope: Mapping[str, Any]) -> Any | None

def resolve_component_callables(local_scope: Mapping[str, Any]) -> tuple[Any | None, Any | None]
```

### [Server](./server.md)

HTTP server for serving SPA.

```python
class SpaServer:
    def __init__(self, framework: SpaFramework)
    
    def serve(self) -> None
```

### [Runtime Assets](./runtime_assets.md)

Client-side JavaScript runtime.

Provides:
- State management
- Event handling
- DOM diffing
- Component lifecycle

## Common Patterns

### Creating a Component

```python
from lua_spa.types import Component, ClientMethods

class MyComponent(Component):
    def context(self, props):
        return {
            "title": props.get("title", "Default"),
        }
    
    def client(self):
        class Client(ClientMethods):
            class StateVar:
                name = "count"
                default = 0
                cast = "int"
            
            State = [StateVar]
            Methods = ["increment"]
            
            def increment(self):
                return self.add("count", 1)
        
        return Client()
```

### Rendering Component

```python
framework = SpaFramework.from_lua_template_directory(Path("lua_template"))

# Render with default props
html = framework.render()

# Render with custom props
html = framework.render({"user_name": "Alice"})
```

### Starting Server

```python
framework = SpaFramework.from_lua_template_directory(Path("lua_template"))
framework.serve()  # Starts server on configured host/port
```

## Next Steps

- [Framework](./framework.md) - Detailed SpaFramework documentation
- [Types](./types.md) - Type system and data classes
- [Component Loader](./loader.md) - Loading and parsing components
- [Components](../components/index.md) - Create components guide
