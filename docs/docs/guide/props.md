---
sidebar_position: 4
title: Props
---

# Props

Props are input values passed from parent components (or bootstrap `initial_props`) into a component.

In moon-spa, props defaults are declared in `setup(self, props)`.

## Passing props

From parent template:

```html
<Card title="Hello" count="42" active="true" />
```

From `spa.config.json`:

```json
{
  "initial_props": { "user": "admin", "debug": false }
}
```

## Declaring props in `setup()`

```python
class Card(Component):
  def setup(self, props):
    return {
      "props": {
        "title": "Default Title",
        "count": 0,
        "active": False,
        **props,
      },
      "state": {},
      "data": {},
      "actions": {},
      "lifecycle": {},
    }
```

You can also omit `return` entirely. In that case, moon-spa infers `props` from the local
`props` variable created in `setup(self, props)`:

```python
class Card(Component):
  def setup(self, props):
    props = {
      "title": "Default Title",
      "count": 0,
      "active": False,
      **props,
    }

    state = {}
    data = {}
```

The runtime merges defaults with incoming values and coerces scalar types (`int`/`float`/`bool`/`str`) safely.

## Reading props in setup and template

`setup(self, props)` receives props as a Python dict:

```python
def setup(self, props):
  title = props.get("title", "Default Title")
  return {
    "props": {"title": title, **props},
    "state": {},
    "data": {},
    "actions": {},
    "lifecycle": {},
  }
```

Template:

```html
<template>
  <p>{{ props.title }}</p>
  <p l-if="props.active">Active!</p>
</template>
```

## Rules

- Define props defaults in `setup(self, props)`.
- `setup` may return a mapping or omit `return` and rely on server inference.
- Use `props` for input values and `state` for reactive mutations.
- Server callables may return explicit prop patches, but mutating `data` is also enough because moon-spa patches those keys automatically.
