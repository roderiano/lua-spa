# Module `loader`

Loader for `.lspa` components and dependency graph builder.

---

## Overview

The `loader` module is responsible for reading component files, extracting templates, Python blocks, and imports, and building a complete registry of all components required by the application.

---

## Main Class

### `ComponentLoader`

Loads components and their dependencies from `.lspa` files.

#### Methods and Properties

- **`__init__(components_dir: Path)`**
  - Initializes the loader for a component directory.

- **`components`**
  - Property that returns the registry of loaded components.

- **`load_entry(entry_component: str)`**
  - Loads a component and all its dependencies recursively.
  - **Exceptions:** FileNotFoundError, ValueError.

- **Internal methods:**
  - `_load_component`, `_extract_imports`, `_extract_template`, `_extract_python` — used for parsing and extracting data from files.

---

## Usage example
```python
from lua_spa.loader import ComponentLoader
loader = ComponentLoader(Path('src/lua_template/components'))
components = loader.load_entry('App')
```

---

> See also: [types.md](types.md) for details about ComponentDefinition.
