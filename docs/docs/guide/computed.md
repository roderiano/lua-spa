---
sidebar_position: 5
title: Computed Variables
---

# Computed Variables

Computed variables let you derive values from props (or any Python logic) on the **server side**, making them available in your template as the `py` namespace.

They are declared in `context(self, props)` — a method called once per request before rendering.

```mermaid
flowchart LR
    P["props"] --> C["context(self, props)"]
    C -->|"returns dict"| PY["py namespace"]
    PY --> T["{{ py.name }} in template"]
    PY --> T2["{{ name }} — also works (flattened)"]
```

---

## Declaring computed variables

Return a plain dict from `context(self, props)`. Every key becomes a variable you can use in the template:

```python
class Greeting(Component):
    def context(self, props):
        name = props.get("name", "World")
        return {
            "message":    f"Hello, {name}!",
            "upper_name": name.upper(),
            "char_count": len(name),
        }
```

```html
<template>
  <div>
    <h1>{{ py.message }}</h1>
    <p>Name in caps: {{ upper_name }}</p>
    <small>{{ char_count }} characters</small>
  </div>
</template>
```

`py.message` and `message` are equivalent — values are available both ways.

---

## What you can do inside `context()`

`context(self, props)` is plain Python. You can call any function, import libraries,
format strings, run conditionals, compute lists — anything:

```python
from datetime import date

class InvoiceHeader(Component):
    def context(self, props):
        total   = props.get("subtotal", 0) * 1.2          # add 20% tax
        due     = props.get("due_date", str(date.today()))
        overdue = due < str(date.today())

        return {
            "total_with_tax": f"${total:.2f}",
            "due_label":      f"Due: {due}",
            "status":         "OVERDUE" if overdue else "Pending",
            "status_class":   "danger"  if overdue else "info",
        }
```

```html
<template>
  <div class="invoice-header">
    <span class="{{ status_class }}">{{ py.status }}</span>
    <p>{{ py.total_with_tax }}</p>
    <p>{{ py.due_label }}</p>
  </div>
</template>
```

---

## Combining `context()` with `client()` (state + computed)

`context()` provides **server-side** computed values (in `py`).  
`client()` provides **client-side** reactive state.

Both can coexist in the same component:

```python
class ProductCard(Component):
    def context(self, props):
        price    = props.get("price", 0)
        discount = props.get("discount", 0)
        final    = price * (1 - discount / 100)
        return {
            "display_price":    f"${price:.2f}",
            "display_final":    f"${final:.2f}",
            "discount_label":   f"{discount}% off" if discount else "",
            "has_discount":     discount > 0,
        }

    def client(self):
        return {
            "state": {
                "quantity": 1,
                "in_cart":  False,
            },
            "actions": {
                "add":     self.add("quantity"),
                "remove":  self.sub("quantity"),
                "to_cart": self.set("in_cart", True),
            },
        }
```

```html
<template>
  <div class="product-card">
    <p l-if="py.has_discount" class="tag">{{ py.discount_label }}</p>
    <p><s>{{ py.display_price }}</s> → <strong>{{ py.display_final }}</strong></p>

    <div class="qty">
      <button @click="remove">−</button>
      <span>{{ state.quantity }}</span>
      <button @click="add">+</button>
    </div>

    <button @click="to_cart" l-if="!state.in_cart">Add to cart</button>
    <span l-else>✓ In cart</span>
  </div>
</template>
```

> `py.*` values are baked into the initial HTML at request time.  
> `state.*` values are reactive — they update live in the browser.

---

## Returning an object instead of a dict

If your `context()` returns an object, its **public attributes** (no leading `_`) are extracted automatically:

```python
class Summary(Component):
    def context(self, props):
        class Info:
            label  = props.get("label", "n/a").title()
            count  = len(props.get("items", []))
            plural = "s" if count != 1 else ""

        return Info()
```

```html
<template>
  <p>{{ py.label }}: {{ py.count }} item{{ py.plural }}</p>
</template>
```

---

## Limitations

| | `context()` — `py` namespace | `client()` — `state` |
|---|---|---|
| When evaluated | **once, server-side**, at request time | client-side, reactive |
| Reacts to user input | ❌ | ✅ |
| Can run Python / import libs | ✅ | ❌ |
| Available in template | ✅ as `{{ py.x }}` or `{{ x }}` | ✅ as `{{ state.x }}` |
| Survives browser navigation | ❌ re-evaluated on next request | ✅ lives in JS memory |

Because computed variables are server-side, they are ideal for:
- Formatting values derived from props (prices, dates, labels)
- Pre-computing lists or lookup tables
- Conditional classes or status strings
- Any logic that requires Python libraries unavailable in the browser
