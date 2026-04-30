# Module `framework`

Main framework for rendering, orchestration, and delivery of SPAs.

---

## Overview

The `framework` module is the backend core, responsible for loading components, rendering HTML, generating client-side JavaScript, and serving the application via HTTP. It integrates all Lua-SPA subsystems.

---

## Main Class

### `SpaFramework`

Backend framework that builds the SPA HTML view and serves it via HTTP.

#### Methods and Properties

- **`from_lua_template_directory(lua_template_dir: Path) -> SpaFramework`**
  - Creates a framework instance from a `lua_template` directory.
  - Loads `spa.config.json` and configures components, mount point, initial props, host, and port.
  - **Exceptions:** FileNotFoundError if files do not exist.

- **`__init__(...)`**
  - Initializes the framework instance.
  - Parameters: file paths, root component name, mount id, default props, host, and port.
  - **Exceptions:** FileNotFoundError, ValueError.

- **`component_names`**
  - Returns the names of all loaded components.

- **`server_address`**
  - Returns the configured (host, port) tuple.

- **`build_view(props: Mapping[str, Any] | None = None) -> str`**
  - Generates the complete HTML page, rendering the root component, injecting data and runtime JS.

- **`serve(host: str | None = None, port: int | None = None) -> None`**
  - Starts the HTTP server to serve the SPA.

- **Internal methods:**
  - `_build_bootstrap_block`, `_serialize_json_payload`, `_render_component`, `_expand_child_components`, `_render_tag_match`, `_parse_attributes` — used for rendering, serialization, and component expansion.

---

## Usage example
```python
from lua_spa.framework import SpaFramework
fw = SpaFramework.from_lua_template_directory(Path('src/lua_template'))
fw.serve()
```

---

> See also: [loader.md](loader.md), [renderer.md](renderer.md), [runtime_assets.md](runtime_assets.md)
