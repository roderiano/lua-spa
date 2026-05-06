---
sidebar_position: 2
title: Rendering Engine
---

# Rendering Engine

`lua_spa.renderer`

The server-side template engine that converts `.lspa` templates into HTML before the page is sent to the browser.

## Processing pipeline

```mermaid
flowchart TD
    A["Raw template string"] --> B["apply_server_loops()"]
    B --> C["apply_server_conditionals()"]
    C --> D["interpolate()"]
    D --> E["Rendered HTML string"]
```

Each pass operates on the string produced by the previous pass. This ordering ensures:
- Loop bodies can contain conditionals
- Conditionals can contain `{{ }}` expressions
- Expressions are always evaluated last on final content

## `render_template_with_directives(template, context)`

Main entry point. Accepts a template string and a context dict (`props`, `state`, `py`).

```python
html = render_template_with_directives(
    "<p l-if=\"count > 0\">{{ count }}</p>",
    {"state": {"count": 3}, "props": {}, "py": {}}
)
# "<p>3</p>"
```

## Loop expansion (`i-for`)

```mermaid
flowchart TD
    A[Find opening tags with i-for] --> B[Balance closing tag]
    B --> C[Evaluate iterable expression]
    C --> D{Items empty?}
    D -- yes --> E[Replace with empty string]
    D -- no --> F[Expand body once per item]
    F --> G[Update context with loop variables]
    G --> H[Concatenate expanded blocks]
```

Multi-target unpacking is supported:

```html
<li i-for="i, item in enumerate(items)">{{ i }}: {{ item }}</li>
```

Nested loops work by re-running the pass until no more `i-for` attributes remain.

## Conditional rendering (`l-if`)

```mermaid
flowchart TD
    A[Parse sibling elements] --> B{Has l-if?}
    B -- yes --> C[Evaluate condition]
    C -- true --> D[Keep element, strip l-if attr]
    C -- false --> E{l-else-if next?}
    E -- yes --> F[Evaluate l-else-if condition]
    F -- true --> G[Keep l-else-if element]
    F -- false --> H{l-else next?}
    H -- yes --> I[Keep l-else element]
    H -- no --> J[Remove all siblings]
    B -- no --> K[Keep element unchanged]
```

## Interpolation (`{{ }}`)

All `{{ expr }}` tokens in the final string are replaced by evaluating `expr` in a safe Python context:

```python
_SAFE_EVAL_GLOBALS = {
    "__builtins__": {},
    "range": range,
    "len": len,
    "enumerate": enumerate,
}
```

The template context adds `state`, `props`, and `py` on top of these globals.

## Context object

```python
context = {
    "state":  {...},  # from setup() state
    "props":  {...},  # from parent or initial_props
    "py":     {...},  # from setup().data
}
```

`build_python_context(...)` and `build_server_state(...)` in `renderer.py` assemble this dict from `setup(self, props)` output before rendering.
