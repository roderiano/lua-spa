# Module `renderer`

Template rendering, expression interpolation, and conditional evaluation on the server.

---

## Overview

The `renderer` module converts component templates with `{{ }}` expressions and `v-if` attributes into HTML, evaluating expressions in the context of props, state, and py.

---

## Main Functions

- **`build_scoped_context(context: Mapping[str, Any]) -> dict[str, Any]`**
  - Builds a scope dictionary for expression evaluation.
  - Allows access by simple name and by namespace (e.g., `count` and `state.count`).

- **`to_namespace(value: Any) -> Any`**
  - Recursively converts dicts and sequences into SimpleNamespace for dot access.

- **`evaluate_expression(expression: str, context: Mapping[str, Any]) -> Any`**
  - Evaluates a Python expression in the component context.

- **`interpolate(template: str, context: Mapping[str, Any]) -> str`**
  - Replaces `{{ expression }}` with their evaluated values.

- **`apply_server_conditionals(template: str, context: Mapping[str, Any]) -> str`**
  - Removes or keeps tags with `v-if` based on expression evaluation.

---

## Usage example
```python
from lua_spa.renderer import interpolate
html = interpolate('<div>{{ count }}</div>', {'count': 42})
```

---

> See also: [framework.md](framework.md) for integration with the rendering flow.
