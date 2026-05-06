---
sidebar_position: 4
title: First Component
---

# Your First Component

Let's build a click counter — the "Hello World" of reactive UIs.

## Create the file

`components/Counter/Counter.lspa`

```html
<python>
class Counter(Component):
  def setup(self, props):
    state = {"count": 0}
    props = {"label": "clicks", **props}

    def increment():
      state["count"] += 1

    def decrement():
      state["count"] -= 1

    def reset():
      state["count"] = 0

    # Optional: The server can infer this return automatically.
    return {
      "props": props,
      "state": state,
      "data": {},
      "actions": {
        "increment": increment,
        "decrement": decrement,
        "reset": reset,
      },
      "lifecycle": {},
    }
</python>

<template>
  <div class="counter">
    <p>{{ state.count }} {{ props.label }}</p>
    <button @click="increment">+</button>
    <button @click="decrement">-</button>
    <button @click="reset">Reset</button>
  </div>
</template>
```

## Import it in `App.lspa`

```html
@import Counter from './Counter/Counter.lspa'

<python>
class App(Component):
    pass
</python>

<template>
  <div class="page">
    <Counter label="taps" />
  </div>
</template>
```

## How it works

```mermaid
sequenceDiagram
    participant Python as Python (server)
    participant JS as JavaScript (browser)

  Python->>Python: setup(self, props)
    Python->>Python: render template → SSR HTML
    Python->>JS: bootstrap JSON (registry + config)
  JS->>JS: hydrate + bind actions
    JS->>JS: hydrate DOM (diff + patch)
    Note over JS: User clicks "+"
  JS->>Python: POST /__moon_spa_action (action=increment)
  Python->>JS: patch {state, props}
  JS->>JS: apply patch and re-render
```

## Key concepts introduced

| Concept | What it does |
|---|---|
| `setup(self, props)` | Declares props, state, data, actions and lifecycle |
| `state.count` | Reads reactive state in the template |
| `@click="action"` | Binds a DOM event to an action |
| callable action | Runs through `POST /__moon_spa_action` and patches state/props |
