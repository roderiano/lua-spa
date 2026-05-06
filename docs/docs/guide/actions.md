---
sidebar_position: 3
title: Actions
---

# Actions

Actions are the only way to mutate state.

lua-spa now uses one official action style: **Python methods**.

## Standard action pattern

```python
class Counter(Component):
    def client(self):
        class State:
            count = 0
            visible = True

        class ClientSpec:
            Methods = ["increment", "decrement", "reset", "flip"]
            State = State

        return ClientSpec()

    def increment(self):
        self.state.count += 1

    def decrement(self):
        self.state.count -= 1

    def reset(self):
        self.state.count = 0

    def flip(self):
        self.state.visible = not self.state.visible
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
    if self.state.count < 10:
        self.state.count += 1
```

Supported comparisons are traced and emitted as client-side guards: `<`, `<=`, `>`, `>=`, `==`, `!=`.

## Rules

- Define actions as Python methods.
- Optionally whitelist methods with `Methods = [...]` or `methods()`.
- Keep state writes inside methods (`self.state.x = ...`, `+=`, `-=`).
- Do not use declarative `"actions": {...}` dict specs.
