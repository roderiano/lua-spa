---
sidebar_position: 2
---

# SpaFramework Class

The main orchestrator for the Lua SPA framework.

## Overview

`SpaFramework` is the central class that coordinates all framework operations: loading components, rendering templates, generating client code, and serving the application.

## Class Definition

```python
class SpaFramework:
    """Backend framework that builds a SPA HTML view and serves it."""
```

## Class Methods

### `from_lua_template_directory(lua_template_dir: Path) -> SpaFramework`

Factory method to create a framework instance from a `lua_template/` directory.

**Parameters:**
- `lua_template_dir` (Path): Path to lua_template directory containing:
  - `spa.config.json` - Configuration file
  - `index.lspa` - Root HTML template
  - `components/` - Components subdirectory

**Returns:**
- `SpaFramework` - Configured framework instance

**Raises:**
- `FileNotFoundError` - If spa.config.json or index.lspa not found
- `ValueError` - If configuration is malformed

**Example:**

```python
from pathlib import Path
from lua_spa.framework import SpaFramework

# Create framework from directory
framework = SpaFramework.from_lua_template_directory(Path("lua_template"))

# Framework is now ready to render and serve
html = framework.render()
```

**What it does:**
1. Loads `spa.config.json`
2. Reads configuration (entry_component, mount_id, host, port, etc.)
3. Creates SpaFramework instance with those settings
4. Loads entry component and dependencies

## Instance Methods

### `__init__(...)`

Initialize a SpaFramework instance directly.

**Parameters:**
- `view_file` (Path, required) - Path to index.lspa
- `components_dir` (Path, required) - Path to components directory
- `entry_component` (str, default="App") - Name of root component
- `mount_id` (str, default="app") - DOM ID where app mounts
- `default_props` (Mapping[str, Any], optional) - Default props for root component
- `host` (str, default="127.0.0.1") - Server host
- `port` (int, default=8000) - Server port

**Raises:**
- `FileNotFoundError` - If view_file doesn't exist
- `ValueError` - If components can't be loaded

**Example:**

```python
from pathlib import Path
from lua_spa.framework import SpaFramework

framework = SpaFramework(
    view_file=Path("lua_template/index.lspa"),
    components_dir=Path("lua_template/components"),
    entry_component="App",
    mount_id="app",
    default_props={"title": "My App"},
    host="127.0.0.1",
    port=8000,
)
```

### `render(props: Mapping[str, Any] | None = None) -> str`

Render the component tree to HTML string.

**Parameters:**
- `props` (Mapping[str, Any], optional) - Props for root component

**Returns:**
- `str` - Complete HTML with embedded JavaScript

**Raises:**
- `ValueError` - If rendering fails

**Process:**
1. Load entry component (if not cached)
2. Execute component Python block
3. Call `context(props)` to get server data
4. Interpolate variables in template
5. Apply directives (v-if, v-for, etc.)
6. Generate client JavaScript
7. Combine into final HTML

**Example:**

```python
# Render with default props
html = framework.render()

# Render with custom props
html = framework.render({"user_name": "Alice", "theme": "dark"})

# Save to file
Path("output.html").write_text(html)
```

### `serve() -> None`

Start the HTTP server and begin serving the SPA.

**Parameters:**
- None

**Returns:**
- None (blocks until server stops)

**Process:**
1. Create HTTP server on configured host/port
2. Listen for incoming requests
3. For each request:
   - Render component to HTML
   - Send to client
4. Block until Ctrl+C

**Example:**

```python
framework = SpaFramework.from_lua_template_directory(Path("lua_template"))

# This blocks - server runs until Ctrl+C
framework.serve()
```

**Server Output:**
```
Starting Lua SPA development server on http://127.0.0.1:8000
Press Ctrl+C to stop the server
```

### `build_html(html: str) -> str`

Build the final HTML document with all assets.

**Parameters:**
- `html` (str) - Component HTML to wrap

**Returns:**
- `str` - Complete HTML document

**Process:**
1. Wrap component HTML in `<body>`
2. Add `<head>` with meta tags, title, etc.
3. Inject client-side runtime JS
4. Return complete HTML

**Example:**

```python
component_html = framework.render()
full_html = framework.build_html(component_html)
```

## Properties

### `entry_component`

The name of the root component to render.

```python
framework.entry_component  # "App"
```

### `mount_id`

The DOM ID where the app mounts.

```python
framework.mount_id  # "app"
```

## Usage Examples

### Basic Setup

```python
from pathlib import Path
from lua_spa.framework import SpaFramework

# Create from configuration directory
framework = SpaFramework.from_lua_template_directory(Path("lua_template"))

# Start server
framework.serve()
```

### Render and Save

```python
framework = SpaFramework.from_lua_template_directory(Path("lua_template"))

# Render to HTML
html = framework.render()

# Save to file
Path("dist/index.html").write_text(html)
```

### Custom Configuration

```python
framework = SpaFramework(
    view_file=Path("custom_dir/root.lspa"),
    components_dir=Path("custom_dir/my_components"),
    entry_component="MainApp",
    mount_id="root",
    default_props={"version": "1.0"},
    host="0.0.0.0",  # Listen on all interfaces
    port=3000,
)

framework.serve()
```

### Render with Props

```python
framework = SpaFramework.from_lua_template_directory(Path("lua_template"))

# Render different versions with different props
html_english = framework.render({"language": "en"})
html_spanish = framework.render({"language": "es"})

# Save both versions
Path("dist/en/index.html").write_text(html_english)
Path("dist/es/index.html").write_text(html_spanish)
```

## Error Handling

### FileNotFoundError

Raised when required files are missing:

```python
try:
    framework = SpaFramework.from_lua_template_directory(Path("wrong_path"))
except FileNotFoundError as e:
    print(f"Configuration not found: {e}")
```

### ValueError

Raised when configuration or rendering fails:

```python
try:
    html = framework.render({"count": "not_a_number"})
except ValueError as e:
    print(f"Render failed: {e}")
```

## Performance Considerations

### Component Caching

Components are loaded once and cached:

```python
# First render loads components
html1 = framework.render()  # Loads components from disk

# Second render uses cached components
html2 = framework.render()  # Instant, uses cache
```

### State Serialization

State is serialized to HTML attributes for hydration:

```html
<!-- Generated HTML includes state as data attributes -->
<div data-lspa-state="{'count': 0, 'is_open': false}">
  ...
</div>
```

### DOM Diffing

Client-side DOM diffing minimizes updates:

```javascript
// Client receives HTML, extracts state, hydrates
const component = new CounterClient();
component.hydrate({ count: 0 });

// When user clicks, method is called
component.increment();  // Updates state and re-renders

// DOM diffing algorithm compares old vs new
// Only changed elements are updated in browser
```

## Next Steps

- [Component Loader](./loader.md) - Learn about component loading
- [Rendering](./renderer.md) - Template rendering details
- [Server](./server.md) - HTTP server details
