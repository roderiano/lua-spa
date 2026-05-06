---
sidebar_position: 4
title: Props
---

# Props

Props are read-only input values passed from parent components (or from bootstrap `initial_props`) into a component.

lua-spa uses one professional pattern for client props: **Python classes/objects only**.

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

## Declaring props in `client()`

Declare a `Props` class with public attributes.

```python
class Card(Component):
    def client(self):
        class Props:
            title = "Default Title"
            count = 0
            active = False

        class ClientSpec:
            pass

        spec = ClientSpec()
        spec.Props = Props
        return spec
```

The runtime merges defaults with incoming values and coerces scalar types (`int`/`float`/`bool`/`str`) safely.

## Reading props on server and template

Server-side (`context`) receives props as a Python dict:

```python
def context(self, props):
    return {"title": props.get("title", "Default Title")}
```

Template:

```html
<template>
  <p>{{ props.title }}</p>
  <p l-if="props.active">Active!</p>
</template>
```

## Rules

- Use classes/objects/functions for props definitions.
- Do not use declarative props dict specs inside `client()`.
- Treat props as immutable input; mutate only state via methods/actions.
