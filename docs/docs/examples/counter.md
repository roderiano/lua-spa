---
sidebar_position: 1
title: Counter
---

# Counter

The simplest interactive component: a click counter with increment, decrement, and reset.

## Full source

`components/Counter/Counter.lspa`

```html
<python>
class Counter(Component):
  def setup(self, props):
    state = {"value": 0}

    def inc():
      state["value"] += 1

    def dec():
      state["value"] -= 1

    def reset():
      state["value"] = 0

    # Optional: The server can infer this return automatically.
    return {
      "props": {"label": "count", "step": 1, **props},
      "state": state,
      "data": {},
      "actions": {"inc": inc, "dec": dec, "reset": reset},
      "lifecycle": {},
    }
</python>

<template>
  <div class="counter">
    <span class="counter__label">{{ props.label }}</span>
    <span class="counter__value">{{ state.value }}</span>
    <div class="counter__buttons">
      <button @click="dec">−</button>
      <button @click="reset">0</button>
      <button @click="inc">+</button>
    </div>
  </div>
</template>
```

`App.lspa`

```html
@import Counter from './Counter/Counter.lspa'

<python>
class App(Component):
    pass
</python>

<template>
  <div class="page">
    <Counter label="score" />
    <Counter label="lives" />
  </div>
</template>
```

## How it works

```mermaid
sequenceDiagram
    participant User
    participant DOM
    participant Runtime

    User->>DOM: clicks "+"
    DOM->>Runtime: @click → inc action
    Runtime->>Runtime: setValue(value + 1)
    Runtime->>DOM: diff + patch counter__value text
    DOM-->>User: updated number
```

## Key patterns

- Multiple instances of the same component each have **independent state**
- `props.label` is passed from the parent as a static string attribute
- Callable actions are normalized to server calls and patch state/props back to client
