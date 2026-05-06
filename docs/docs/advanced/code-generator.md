---
sidebar_position: 4
title: Code Generator
---

# Code Generator

`lua_spa.codegen` · `lua_spa.scope` · `lua_spa.trace`

These three modules form the **Python-to-JavaScript compiler** that turns `Component.setup(self, props)` output into a `setup()` JS function.

## Pipeline

```mermaid
flowchart TD
  A["python block source"] --> B["load_python_scope()"]
  B --> C["exec() in full Python env"]
    C --> D["resolve_component_callables()"]
  D --> E["setup(self, props) invoked"]
    E --> F["normalize_client_spec()"]
    F --> G["props / state / actions / lifecycle specs"]
    G --> H["build_client_script()"]
    H --> I["setup() JS function string"]
```

## `load_python_scope(python_block) → dict`

`lua_spa.scope`

Executes the `<python>` block in a full Python environment (all built-ins available). Adds:
- `Component` base class
- `StateField` dataclass
- Tracing-aware overrides for `int`, `float`, `str`, `bool`

## `resolve_component_callables(scope)`

Returns `(context_fn, client_fn)` from a `Component` subclass implementing `setup(self, props)`.
Legacy `context()/client()` and top-level setup styles are rejected.

## Tracing proxies (`lua_spa.trace`)

When setup-derived operations are normalized, traced objects are used to preserve expression references and operation semantics.

```mermaid
classDiagram
    class _TraceProps {
        +__getattr__(name) _PropReference
    }
    class _TraceState {
        +__getattr__(name) _StateReference
    }
    class _PropReference {
        +str name
        +Any default
        +__add__, __sub__, __mul__, ...
    }
    class _BinaryExpression {
        +str op
        +Any left
        +Any right
    }
```

This allows expressions like `self.add("count", props.initialCount + 1)` to be converted to a JavaScript expression rather than evaluated eagerly in Python.

## Generated `setup()` structure

```js
function setup({ useState, props, componentName }) {
  // 1. Resolve and coerce props
  const resolvedProps = Object.assign({}, { name: "default" }, props || {});

  // 2. useState hooks
  const [__state_0, __set_state_0] = useState(0);

  // 3. Actions object + server bridge
  const actions = {
    increment: function () { __serverCall("action", "increment"); },
    reset:     function () { __set_state_0(0); },
  };

  // 4. __callAction dispatcher
  function __callAction(actionName, event) { ... }

  // 5. Lifecycle hooks
  const lifecycle = {
    onCreate:  function () {},
    onMount:   function () { __callAction("init"); },
    onUpdate:  function () {},
    onUnmount: function () {},
  };

  // 6. Exposed state + return
  const state = { count: __state_0 };
  return { props: resolvedProps, state, actions, lifecycle };
}
```

## Operation mapping

### Computed variables (`setup().data` → `py` namespace)

`setup(self, props)` can return a mapping, or omit `return` and let the server infer the spec.
The `data` section is evaluated server-side and injected into render context as `py`.
It is not compiled to JavaScript by itself; it is hydrated through props patches when returned by server callables.

```python
# Python
class Card(Component):
    def setup(self, props):
        price = props.get("price", 0)
        props = {**props}
        state = {}
        data = {
            "display": f"${price:.2f}",
            "is_cheap": price < 10,
        }

        return {
            "props": props,
            "state": state,
            "data": data,
            "actions": {},
            "lifecycle": {},
        }
```

```
Render context passed to template:
{
  "props": { "price": 7 },
  "state": { ... },
  "py":    { "display": "$7.00", "is_cheap": True }
}
```

Template access:
```html
<p>{{ py.display }}</p>          <!-- explicit namespace -->
<p l-if="is_cheap">On sale!</p>  <!-- flat / shorthand -->
```

`py` values are baked into the server-rendered HTML. They do **not** appear in the generated `setup()` function.

---

### State (`setup().state` → `useState` hooks)

Each state field in `setup().state` compiles to a `useState` hook. The initial value expression depends on how the field is declared:

| Python declaration | Internal spec | Generated JS |
|---|---|---|
| `"count": 0` | `{"default": 0}` | `useState(0)` |
| `"name": "lua"` | `{"default": "lua"}` | `useState("lua")` |
| `StateField("n", default=0, cast="int")` | `{"default": 0, "cast": "int"}` | `useState(0)` |
| `StateField("q", from_prop="qty", default=1, cast="int")` | `{"from_prop": "qty", "default": 1, "cast": "int"}` | `useState(Number(resolvedProps["qty"] ?? 1))` |

Example — full Python → JS compilation:

```python
# Python
class Counter(Component):
    def setup(self, props):
    props = {**props}
    state = {
            "count": 0,
            "label": "start",
        }
    data = {}

    return {
      "props": props,
      "state": state,
      "data": data,
      "actions": {},
      "lifecycle": {},
    }
```

```js
// Generated setup() (excerpt)
const [__state_0, __set_state_0] = useState(0);      // count
const [__state_1, __set_state_1] = useState("start"); // label

const state = { count: __state_0, label: __state_1 };
```

---

### Actions (`setup().actions`)

Actions are defined in `setup().actions` as operation mappings or callables.

| Python | Internal operation dict | Generated JS action body |
|---|---|---|
| `{"op":"add","state":"count","value":1}` | `{"op":"add","state":"count","value":1}` | `__set_state_0(function(v){return v+1;});` |
| `{"op":"sub","state":"count","value":1}` | `{"op":"sub","state":"count","value":1}` | `__set_state_0(function(v){return v-1;});` |
| `{"op":"set","state":"flag","value":True}` | `{"op":"set","state":"flag","value":True}` | `__set_state_1(function(){return true;});` |
| `{"op":"toggle","state":"flag"}` | `{"op":"toggle","state":"flag"}` | `__set_state_1(function(v){return !v;});` |
| `callable` | `{"op":"server_call","kind":"action","name":"..."}` | `__serverCall("action", "...");` |

Full example:

```python
# Python
class Counter(Component):
  def setup(self, props):
    return {
      "props": props,
      "state": {"count": 0},
      "data": {},
      "actions": {
        "increment": {"op": "add", "state": "count", "value": 1},
        "reset": {"op": "set", "state": "count", "value": 0},
      },
      "lifecycle": {},
    }
```

```js
// Generated setup() (excerpt)
const [__state_0, __set_state_0] = useState(0);

const actions = {
  increment: function () {
    __set_state_0(function (value) { return value + 1; });
  },
  reset: function () {
    __set_state_0(function () { return 0; });
  },
};
```

---

Callable actions are executed through the server bridge and generate state/props patches.
If an action mutates `data`, updated `data` keys are automatically included in the props patch even when the action returns `None`.

Latest behavior:
- Action callables can update `data` directly (for example `data["pypi"] = refreshed`) without returning a mapping.
- The server emits those `data` keys through props patching automatically.

```python
# Python
class Counter(Component):
    def setup(self, props):
        state = {"count": 0}
        data = {"limit": 10}

        def safe_increment():
            if state["count"] < 10:
                state["count"] += 1
                data["limit"] = 10

        return {
          "props": props,
          "state": state,
          "data": data,
          "actions": {"safe_increment": safe_increment},
          "lifecycle": {},
        }
```

Tracing records:

```python
# Internal operation list produced by _TraceState
[
  {
    "op": "add",
    "state": "count",
    "value": 1,
    "cond": {"left": "count", "op": "<", "right": 10}
  }
]
```

Generated JS:

```js
safe_increment: function () {
  if (__state_0 < 10) {
    __set_state_0(function (value) { return value + 1; });
  }
},
```

#### Conditional operators captured by `_TraceState`

State variables are named by **enumeration order**, not by field name: the first state field is `__state_0`, the second `__state_1`, and so on. The field name (`x`) is only used as a lookup key — it never appears in the JS variable name.

| Python comparison | `cond.op` | JS guard (where `__state_0` is the variable for `x`) |
|---|---|---|
| `self.state.x < n`  | `"<"`  | `if (__state_0 < n)` |
| `self.state.x <= n` | `"<="` | `if (__state_0 <= n)` |
| `self.state.x > n`  | `">"`  | `if (__state_0 > n)` |
| `self.state.x >= n` | `">="` | `if (__state_0 >= n)` |
| `self.state.x == n` | `"=="` | `if (__state_0 == n)` |
| `self.state.x != n` | `"!="` | `if (__state_0 != n)` |

#### Multi-step traced method

```python
def restart(self):
    self.state.score     = 0       # → {"op":"set","state":"score","value":0}
    self.state.lives     = 3       # → {"op":"set","state":"lives","value":3}
    self.state.game_over = False   # → {"op":"set","state":"game_over","value":False}
```

```js
restart: function () {
  __set_state_0(function () { return 0; });
  __set_state_1(function () { return 3; });
  __set_state_2(function () { return false; });
},
```
