---
sidebar_position: 2
title: State
---

# State

State is reactive data kept in the browser. When state changes, the component re-renders automatically.

lua-spa state is declared inside `setup(self, props)`.

Use plain mappings for runtime state values. Server callables can mutate those values,
and the runtime patches the browser state.

## Standard state declaration

```python
class Counter(Component):
    def setup(self, props):
        state = {
            "count": 0,
            "title": props.get("title", "lua-spa"),
            "visible": True,
        }

        def increment():
            state["count"] += 1

        def toggle_visible():
            state["visible"] = not state["visible"]
```

Template:

```html
<p>{{ state.count }}</p>
<p l-if="state.visible">{{ state.title }}</p>
```

## Rules

- Define `state` inside `setup(self, props)`.
- Keep state keys stable and JSON-serializable.
- Mutate state through setup actions/lifecycle callables.
- Prefer explicit state keys over dynamically adding new keys at runtime.
