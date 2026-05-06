---
sidebar_position: 2
title: State
---

# State

State is reactive data kept in the browser. When state changes, the component re-renders automatically.

lua-spa now has one official state model: **Python classes/objects (or `StateField`)**, never declarative dict state specs.

## Standard state declaration

```python
from lua_spa.types import StateField

class Counter(Component):
    def client(self):
        class State:
            count = 0
            title = "lua-spa"
            visible = True
            qty = StateField(name="qty", from_prop="initialQty", default=1, cast="int")

        class ClientSpec:
            pass

        spec = ClientSpec()
        spec.State = State
        return spec
```

Template:

```html
<p>{{ state.count }}</p>
<p l-if="state.visible">{{ state.title }}</p>
```

## Rules

- Use `State` class/object with public attributes.
- Use `StateField` only when you need prop-seeded defaults and type coercion.
- Do not use `"state": {...}` declarative dictionaries.
- Mutate state through Python action methods (see Actions guide).
