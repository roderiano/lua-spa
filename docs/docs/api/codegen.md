# Module `codegen`

JavaScript code generation from Python component specifications.

---

## Overview

The `codegen` module converts Python blocks from components into JavaScript `setup()` functions, which are used on the client side to initialize state, actions, and component lifecycle.

---

## Functions

### `build_client_script(python_block: str) -> str`

Generates the client-side `setup()` function from a component's `<python>` block.

**Parameters:**
- `python_block` (str): Python code extracted from the component.

**Returns:**
- (str): JavaScript code for the `setup()` function.

**Details:**
- Analyzes the Python block, extracts props, state, actions, and lifecycle.
- Generates code that defines state hooks, action functions, and lifecycle hooks.
- Returns a JS string ready to be embedded in HTML.

**Usage example:**
```python
from lua_spa.codegen import build_client_script
js_code = build_client_script(python_block)
```

---

> See also: [scope.md](scope.md) for details about Python spec extraction.
