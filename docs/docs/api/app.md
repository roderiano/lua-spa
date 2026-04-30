# Module `app`

Helpers to initialize the SPA application based on the Lua-SPA framework.

---

## Overview

The `app` module provides utility functions to create an instance of the main framework, centralizing initial configuration and making application bootstrap easier.

---

## Functions

### `create_default_framework(base_dir: Path | None = None) -> SpaFramework`

Creates a framework instance using only the settings found in `lua_template/`.

**Parameters:**
- `base_dir` (Path | None): Base directory to look for the `lua_template` folder. If not provided, uses the current directory.

**Returns:**
- `SpaFramework`: Configured framework instance ready for use.

**Usage example:**
```python
from lua_spa.app import create_default_framework
framework = create_default_framework()
framework.serve()
```

**Context:**
Use this function to quickly initialize the development or production server, without manually handling paths or configuration.

---

> See also: [framework.md](framework.md) for details about the SpaFramework class.
