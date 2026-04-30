# Module `scope`

Extraction and normalization of component specifications from Python blocks.

---

## Overview

The `scope` module executes Python blocks from components in a controlled environment, extracting `context()` and `client()` functions, as well as props, state, actions, and lifecycle for use both in the backend and for JS code generation.

---

## Main Functions

- **`resolve_component_instance(local_scope: Mapping[str, Any]) -> Any | None`**
  - Instantiates the component from the local scope, if possible.

- **`resolve_component_callables(local_scope: Mapping[str, Any]) -> tuple[Any | None, Any | None]`**
  - Extracts the `context()` and `client()` functions from the component.

- **`normalize_context_result(result: Any) -> dict[str, Any]`**
  - Normalizes the return value of `context()` to a dict.

- **`normalize_client_spec(raw_spec: Any) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, list[str]]]`**
  - Extracts and normalizes props, state, actions, and lifecycle from the client.

- **`normalize_props_source`, `normalize_state_source`, `normalize_state_item`**
  - Normalize props and state from different formats.

- **`resolve_methods_actions`, `invoke_method_callable`**
  - Extract and execute action methods, capturing state mutations.

- **`normalize_lifecycle_spec`, `normalize_lifecycle_methods`**
  - Normalize and extract lifecycle hooks.

---

## Usage example
```python
from lua_spa.scope import resolve_component_callables
context_fn, client_fn = resolve_component_callables(locals())
```

---

> See also: [codegen.md](codegen.md) for integration with JS code generation.
