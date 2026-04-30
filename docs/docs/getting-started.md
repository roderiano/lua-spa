---
sidebar_position: 2
---

# Getting Started

Learn how to set up Lua SPA and create your first component.

## Prerequisites

- **Python 3.11+**
- **Poetry** (for dependency management)
- A modern web browser

## Installation

### 1. Clone and Install

```bash
git clone https://github.com/lua-spa/lua-spa.git
cd lua-spa
poetry install
```

### 2. Run the Development Server

```bash
poetry run lua-spa
```

You should see output like:

```
Starting development server on http://127.0.0.1:8000
Press Ctrl+C to stop the server
```

### 3. Open Your Browser

Navigate to `http://127.0.0.1:8000` and you should see the Counter example.

## Project Structure

The framework reads your application from the `lua_template/` directory:

```
lua_template/
├── spa.config.json          # App configuration
├── index.lspa              # Root HTML template
└── components/             # Your components
    ├── App.lspa
    └── Counter.lspa
```

## Understanding spa.config.json

The `spa.config.json` file contains global app configuration:

```json
{
  "entry_component": "App",
  "mount_id": "app",
  "initial_props": {},
  "server": {
    "host": "127.0.0.1",
    "port": 8000
  }
}
```

**Fields:**
- `entry_component` - Root component to render (must match a component filename)
- `mount_id` - DOM ID where the app mounts
- `initial_props` - Default props passed to the root component
- `server` - Host and port configuration

## Understanding index.lspa

The `index.lspa` is your root HTML template:

```html
<!DOCTYPE html>
<html>
  <head>
    <meta charset="UTF-8" />
    <title>Lua SPA</title>
  </head>
  <body>
    <div id="app"></div>
  </body>
</html>
```

This is just standard HTML. The `<div id="app"></div>` is where your component mounts (controlled by `mount_id` in config).

## Your First Component

Create `lua_template/components/Counter.lspa`:

```html
<python>
class Component:
    def context(self, props):
        return {"label": "Counter"}
    
    def client(self):
        from lua_spa.types import ClientMethods
        
        class CounterClient(ClientMethods):
            start = 0
            
            class CountState:
                name = "count"
                from_prop = "start"
                default = 0
                cast = "int"
            
            State = [CountState]
            Methods = ["increment", "reset"]
            
            def increment(self):
                return self.add("count", 1)
            
            def reset(self):
                return self.set("count", 0)
        
        return CounterClient()
</python>

<template>
  <div>
    <h1>{{ label }}</h1>
    <p>Count: <strong>{{ count }}</strong></p>
    
    <button @click="increment">+1</button>
    <button @click="reset">Reset</button>
  </div>
</template>
```

### Breaking It Down

1. **`<python>` block**: Defines server and client logic
   - `context(props)` - Server-side data for template rendering
   - `client()` - Returns client-side component class

2. **State Definition**:
   - `name` - Variable name in template
   - `from_prop` - Initialize from a prop
   - `default` - Fallback value
   - `cast` - Type coercion (`"int"`, `"str"`, `"bool"`, `"float"`, `"raw"`)

3. **Methods**: List of method names that can be called on client
   - `increment()` - Returns operation to execute
   - `reset()` - Returns operation to execute

4. **`<template>` block**: Vue-like template syntax
   - `{{ }}` - Variable interpolation
   - `@click` - Event binding
   - `v-if`, `v-for`, etc. - Vue directives

## Rendering and Hydration

When you start the server:

1. **Server**: Renders the component to HTML using `context()` data
2. **Client**: Hydrates the HTML with JavaScript from `client()`
3. **Interaction**: User events trigger state changes on the client
4. **Update**: DOM automatically updates based on state changes

## Common Tasks

### Add a New Component

Create `lua_template/components/Greeting.lspa`:

```html
<python>
class Component:
    def context(self, props):
        name = props.get("name", "World")
        return {"greeting": f"Hello, {name}!"}
    
    def client(self):
        return {}  # No client-side logic needed
</python>

<template>
  <h1>{{ greeting }}</h1>
</template>
```

### Use a Component in Another Component

In `lua_template/components/App.lspa`:

```html
@import Greeting from "./Greeting.lspa"
@import Counter from "./Counter.lspa"

<python>
class Component:
    def context(self, props):
        return {}
    
    def client(self):
        return {}
</python>

<template>
  <div>
    <Greeting name="Alice" />
    <Counter />
  </div>
</template>
```

### Pass Props Between Components

Props are passed via HTML attributes:

```html
<Counter start="5" />
```

Access them in the component:

```python
def context(self, props):
    initial_value = props.get("start", 0)
    return {"count": initial_value}
```

## Development Commands

```bash
# Run development server with hot reload
poetry run lua-spa

# Run tests
poetry run pytest

# Type checking with MyPy
poetry run mypy src

# Linting with Ruff
poetry run ruff check src

# Format code
poetry run ruff format src
```

## Next Steps

- Learn [Component Concepts](./components/index.md)
- Explore [State Management](./components/state.md)
- Read the [Framework API](./api/framework.md)

## Troubleshooting

### Port Already in Use

Change the port in `spa.config.json`:

```json
"server": {
  "port": 8001
}
```

### Component Not Rendering

1. Check that the component file exists in `lua_template/components/`
2. Ensure the filename matches the import (case-sensitive)
3. Check the terminal for Python syntax errors in the component

### State Changes Not Reflecting

Make sure your method returns an operation dict:

```python
def increment(self):
    return self.add("count", 1)  # Returns operation
```

Not:

```python
def increment(self):
    # This won't work - needs to return an operation
    pass
```
