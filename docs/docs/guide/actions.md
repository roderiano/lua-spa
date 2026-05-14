---
sidebar_position: 3
title: Actions
---

# Actions

Actions are the only way to mutate state.

moon-spa uses `setup(self, props)` actions declared explicitly in `actions` or inferred from local callables when `setup` omits a return mapping.

## Standard action pattern

```python
class Counter(Component):
    def setup(self, props):
        state = {"count": 0, "visible": True}
        data = {"lastChange": "init"}

        def increment():
            state["count"] += 1
            data["lastChange"] = "increment"

        def decrement():
            state["count"] -= 1

        def reset():
            state["count"] = 0

        def flip():
            state["visible"] = not state["visible"]
```

Template binding:

```html
<button @click="decrement">-</button>
<button @click="reset">0</button>
<button @click="increment">+</button>
```

## Event bindings

You can bind actions to any DOM event using the `@event` syntax:

```html
<input @input="onInput" />
<input @change="onChange" />
<input @blur="onBlur" />
<input @keyup="onKeyup" />
<form @submit="onSubmit">...</form>
```

- `@input`, `@change`, `@blur`, `@keyup`, `@submit`, and other DOM events are supported.
- For forms, on submit, all form fields are collected into a dictionary and assigned to `state[form_name]` (see the Templating guide for details).
- The state is always updated before the action runs.
- The action receives the latest state, including form data if applicable.

## Conditional actions

```python
def increment():
    if state["count"] < 10:
        state["count"] += 1
```

For declarative operations, supported comparisons in `cond` are emitted as client-side guards: `<`, `<=`, `>`, `>=`, `==`, `!=`.

## Rules

- Define actions inside `setup(self, props)`.
- You may omit returned `actions` mapping; server can infer actions from local functions.
- Functions named as lifecycle hooks (`created`, `mounted`, `updated`, `unmounted`) are inferred as lifecycle, not actions.
- Use callables when action logic should execute on server via `server_call`.
- Use mapping operations (`set`, `add`, `sub`, `toggle`, `multi`, `log`) for direct client-side behavior.
- Keep state mutations explicit and deterministic.
- If an action mutates `data`, the resulting `data` keys are patched to props automatically without `return {...}`.
