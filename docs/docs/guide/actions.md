---
sidebar_position: 3
title: Actions
---

# Actions

Actions are the only way to mutate state.

lua-spa uses `setup(self, props)` actions declared in the returned `actions` mapping.

## Standard action pattern

```python
class Counter(Component):
    def setup(self, props):
        state = {"count": 0, "visible": True}

        def increment():
            state["count"] += 1

        def decrement():
            state["count"] -= 1

        def reset():
            state["count"] = 0

        def flip():
            state["visible"] = not state["visible"]

        return {
            "props": props,
            "state": state,
            "data": {},
            "actions": {
                "increment": increment,
                "decrement": decrement,
                "reset": reset,
                "flip": flip,
            },
            "lifecycle": {},
        }
```

Template binding:

```html
<button @click="decrement">-</button>
<button @click="reset">0</button>
<button @click="increment">+</button>
```

## Conditional actions

```python
def increment(self):
    ...
```

For declarative operations, supported comparisons in `cond` are emitted as client-side guards: `<`, `<=`, `>`, `>=`, `==`, `!=`.

## Rules

- Define actions inside `setup(self, props)`.
- Use callables when action logic should execute on server via `server_call`.
- Use mapping operations (`set`, `add`, `sub`, `toggle`, `multi`, `log`) for direct client-side behavior.
- Keep state mutations explicit and deterministic.
