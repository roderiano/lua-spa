---
sidebar_position: 3
---

# Architecture Overview

Understand how Lua SPA works under the hood.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Browser (Client)                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Runtime JS (runtime_assets.py)                       │  │
│  │ - State management                                   │  │
│  │ - Event handling                                     │  │
│  │ - DOM diffing                                        │  │
│  │ - Component lifecycle                               │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ HTTP / WebSocket
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Python Backend                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ SpaFramework (framework.py)                          │  │
│  │  - Orchestrates rendering & serving                 │  │
│  │  - Manages component lifecycle                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│  ┌────────────┬───────────┼───────────┬─────────────────┐  │
│  │            │           │           │                 │  │
│  ▼            ▼           ▼           ▼                 ▼  │
│ Loader    Scope       Renderer    CodeGen          Server   │
│(loader.py)(scope.py) (renderer.py)(codegen.py)  (server.py) │
│  - Load    - Execute   - Build     - Generate     - HTTP    │
│    .lspa     Python     HTML        JavaScript    - Route    │
│  - Parse   - Extract   - Insert    - Inject       - Serve   │
│    imports   context    state       runtime                  │
│  - Resolve  - Trace    - Apply      - Bundle               │
│    props    types      directives                           │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Runtime Assets (runtime_assets.py)                   │  │
│  │ - Client-side runtime code (embedded in HTML)        │  │
│  │ - State management logic                             │  │
│  │ - Event binding                                       │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Request/Response Flow

### Initial Page Load

```
1. Browser requests GET /
         │
         ▼
2. Server (server.py)
   - Loads configuration from spa.config.json
   - Creates SpaFramework instance
         │
         ▼
3. SpaFramework.render()
   - Loads entry component
   - Extracts python_block
         │
         ▼
4. Scope (scope.py)
   - Executes component's Python code
   - Extracts context() and client() callables
   - Normalizes state and method definitions
         │
         ▼
5. Renderer (renderer.py)
   - Calls context(props) to get server data
   - Interpolates variables in template
   - Applies v-if, v-for directives
   - Returns rendered HTML
         │
         ▼
6. CodeGen (codegen.py)
   - Extracts client specs (state, methods, lifecycle)
   - Generates JavaScript class
   - Injects into HTML as <script> tag
         │
         ▼
7. HTML Response
   - Full HTML + Embedded JS + CSS
   - Includes Runtime JS (runtime_assets.py)
         │
         ▼
8. Browser parses HTML
   - Mounts runtime JS
   - Initializes components
   - Hydrates state from HTML attributes
   - Attaches event listeners
```

### User Interaction

```
1. User clicks button (@click="increment")
   │
   ▼
2. Runtime JS intercepts event
   │
   ▼
3. Call method: component.increment()
   │
   ▼
4. Method returns operation:
   {"op": "add", "state": "count", "value": 1}
   │
   ▼
5. Runtime applies operation to state
   │
   ▼
6. Component re-renders with new state
   │
   ▼
7. DOM diffing algorithm compares old vs new
   │
   ▼
8. Minimal DOM updates applied
   │
   ▼
9. Browser repaints affected elements
```

## Data Flow

### Component Definition (.lspa file)

A `.lspa` file contains:

```html
@import ComponentName from "./path.lspa"

<python>
# Python code executed on server at render time
class Component:
    def context(self, props):
        # Returns server-side data for template
        return {"key": "value"}
    
    def client(self):
        # Returns client spec for JavaScript generation
        class MyClientClass(ClientMethods):
            # Client properties
            initial_value = 10
            
            # State definitions
            class StateField:
                name = "count"
                from_prop = "start"
                default = 0
                cast = "int"
            
            State = [StateField]
            Methods = ["increment"]
            
            def increment(self):
                return self.add("count", 1)
        
        return MyClientClass()
</python>

<template>
  <!-- Vue-like template syntax -->
  <div>{{ count }}</div>
  <button @click="increment">+</button>
</template>
```

### Execution Sequence

1. **Parse** (loader.py)
   - Split into python_block, template, imports
   - Resolve component imports

2. **Execute** (scope.py)
   - Run python_block in isolated namespace
   - Extract Component class or instance

3. **Extract Specs** (scope.py)
   - Call component.context(props) → server data
   - Call component.client() → client spec

4. **Render** (renderer.py)
   - Merge server data with template
   - Apply directives (v-if, v-for, etc.)
   - Produce HTML with state embedded

5. **Generate Code** (codegen.py)
   - Extract state, methods, lifecycle from client spec
   - Generate JavaScript class
   - Inject client runtime

6. **Serve** (server.py)
   - Return complete HTML + JS + CSS

7. **Hydrate** (Runtime JS)
   - Initialize component class
   - Restore state from HTML attributes
   - Attach event listeners

## Module Responsibilities

### `framework.py` - SpaFramework Class

**Purpose**: Main orchestrator for the entire system.

**Key Methods**:
- `from_lua_template_directory()` - Factory from configuration
- `render()` - Render component tree to HTML
- `build_html()` - Construct final HTML document
- `serve()` - Start HTTP server

**Responsibilities**:
- Load .lspa components
- Coordinate rendering pipeline
- Generate client code
- Inject runtime

### `loader.py` - ComponentLoader Class

**Purpose**: Parse and load .lspa files.

**Key Methods**:
- `load()` - Load single component file
- `load_entry()` - Load component and dependencies
- `_parse_component()` - Parse .lspa file into parts
- `_parse_imports()` - Extract @import directives

**Responsibilities**:
- Parse .lspa file structure
- Extract python block, template, imports
- Recursively load imported components
- Cache loaded components

### `scope.py` - Component Scope Execution

**Purpose**: Execute Python code in isolated scope.

**Key Functions**:
- `load_python_scope()` - Execute component Python
- `resolve_component_instance()` - Extract component object
- `resolve_component_callables()` - Get context() and client()
- `normalize_component_spec()` - Validate and normalize specs

**Responsibilities**:
- Execute component Python safely
- Extract callable interfaces
- Validate client specifications
- Normalize state and method definitions

### `renderer.py` - Template Rendering

**Purpose**: Render templates with data.

**Key Functions**:
- `build_python_context()` - Build interpolation context
- `interpolate()` - Replace {{ }} with values
- `apply_server_conditionals()` - Handle v-if/v-show
- `build_server_state()` - Serialize state to HTML

**Responsibilities**:
- Template variable interpolation
- Directive processing
- State serialization
- HTML generation

### `codegen.py` - JavaScript Code Generation

**Purpose**: Generate client-side JavaScript.

**Key Functions**:
- `generate_client_code()` - Generate JS class
- `generate_methods()` - Create method dispatch
- `generate_lifecycle()` - Handle hooks
- `generate_hydration()` - Initialize state

**Responsibilities**:
- Generate JavaScript from specs
- Create state management code
- Create method dispatch
- Create event binding code

### `runtime_assets.py` - Client Runtime

**Purpose**: Client-side runtime code (JavaScript).

**Key Components**:
- State management class
- Event handler system
- DOM diffing algorithm
- Lifecycle hook system

**Responsibilities**:
- Initialize components
- Manage state
- Handle events
- Update DOM

### `server.py` - HTTP Server

**Purpose**: Serve the SPA.

**Key Methods**:
- `__init__()` - Initialize with framework
- `serve()` - Start server
- `_request_handler()` - Handle HTTP requests

**Responsibilities**:
- Listen for HTTP requests
- Render on request
- Serve static assets
- Handle errors

## State Management Flow

```
Component Props
      │
      ▼
┌──────────────────┐
│ Server Renders   │
│ HTML with state  │
└──────────────────┘
      │
      ▼
┌──────────────────────────────┐
│ Browser receives HTML        │
│ Hydrates JS with state       │
│ Attaches event listeners     │
└──────────────────────────────┘
      │
      ▼
User interaction (click, input, etc.)
      │
      ▼
┌──────────────────────────┐
│ Method executes          │
│ Returns operation object │
└──────────────────────────┘
      │
      ▼
┌──────────────────────────┐
│ Operation applies to     │
│ state in-memory          │
└──────────────────────────┘
      │
      ▼
┌──────────────────────────┐
│ Component re-renders     │
│ with new state           │
└──────────────────────────┘
      │
      ▼
┌──────────────────────────┐
│ DOM diff compares        │
│ old vs new HTML          │
└──────────────────────────┘
      │
      ▼
┌──────────────────────────┐
│ Minimal DOM updates      │
│ applied to page          │
└──────────────────────────┘
```

## Key Design Decisions

### Backend-First Rendering
- Server handles initial render for SEO and fast first paint
- Client hydrates with interactive state management
- Separates concerns: server (data) vs client (interaction)

### Component Isolation
- Each component has its own Python scope
- State is component-local by default
- Props are the interface between components

### DOM Diffing
- Inspired by React's virtual DOM
- Minimizes browser repaints and reflows
- Efficient for complex component trees

### Type Safety
- Full MyPy strict mode compliance
- Runtime type casting with `cast` parameter
- Prevents common bugs at development time

## Performance Considerations

### Server-Side
- Components loaded once at startup
- Python executed only on initial render
- Efficient HTML generation

### Client-Side
- Minimal JavaScript payload
- DOM diffing avoids unnecessary updates
- Event delegation for efficiency

### Rendering
- Incremental rendering for large trees
- Caching of computed properties
- Lazy component initialization

## Extension Points

### Custom Directives
Extend template rendering in `renderer.py`:

```python
def apply_custom_directive(html, directive, value):
    # Custom v-* handling
    pass
```

### Custom State Types
Add type casting in `trace.py`:

```python
def _custom_cast(value, cast_type):
    # Custom type conversion
    pass
```

### Custom Components
Subclass `Component`:

```python
class SpecializedComponent(Component):
    def context(self, props):
        # Custom logic
        pass
```
