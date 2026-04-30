---
sidebar_position: 2
---

# State Management

Learn how to manage component state in Lua SPA.

## What is State?

State is data that changes over time in response to user interactions. Unlike props (which are immutable), state can be modified and causes re-renders when changed.

## Defining State

State is defined in the client class using nested `State*` classes:

```python
class Component:
    def client(self):
        class MyClient(ClientMethods):
            # State definition
            class CountState:
                name = "count"           # Variable name in template
                from_prop = "start"      # Initialize from prop (optional)
                default = 0              # Fallback value
                cast = "int"             # Type: "int", "str", "bool", "float", "raw"
            
            State = [CountState]
        
        return MyClient()
```

## State Field Parameters

### `name`
The variable name used in the template and methods.

```python
class CountState:
    name = "count"  # Access as {{ count }} in template
```

### `from_prop` (Optional)
Initialize state from a component prop.

```python
class StartState:
    name = "count"
    from_prop = "start"  # Initialized from props["start"]
    default = 0          # Used if prop not provided
```

If `from_prop` is set, the initial state value is:
1. The prop value if provided
2. The `default` value if prop is missing
3. Cast using the `cast` type

### `default`
The initial value if no prop is provided.

```python
class NameState:
    name = "username"
    default = "Anonymous"
```

### `cast`
Type coercion for the state value.

| Type | Description | Example |
|------|-------------|---------|
| `"int"` | Integer | `"42"` → `42` |
| `"str"` | String | `42` → `"42"` |
| `"float"` | Float | `"3.14"` → `3.14` |
| `"bool"` | Boolean | `"true"` → `True`, `"1"` → `True` |
| `"raw"` | No conversion | `value` → `value` |

```python
class QuantityState:
    name = "qty"
    cast = "int"  # "5" becomes 5
```

## Multiple State Fields

Define multiple state fields by adding them to the `State` list:

```python
class MyClient(ClientMethods):
    class EmailState:
        name = "email"
        default = ""
        cast = "str"
    
    class PasswordState:
        name = "password"
        default = ""
        cast = "str"
    
    class IsLoadingState:
        name = "is_loading"
        default = False
        cast = "bool"
    
    State = [EmailState, PasswordState, IsLoadingState]
```

Access in template:

```html
<input :value="email" />
<input type="password" :value="password" />
<p v-if="is_loading">Loading...</p>
```

## Mutating State

State is mutated through methods that return operations. Methods are listed in the `Methods` attribute:

```python
class MyClient(ClientMethods):
    class CountState:
        name = "count"
        default = 0
        cast = "int"
    
    State = [CountState]
    Methods = ["increment", "decrement", "reset"]
    
    def increment(self):
        return self.add("count", 1)
    
    def decrement(self):
        return self.sub("count", 1)
    
    def reset(self):
        return self.set("count", 0)
```

## State Operations

### `add(state_name, value)`

Increment numeric state.

```python
def increment(self):
    return self.add("count", 1)

def add_ten(self):
    return self.add("count", 10)
```

### `sub(state_name, value)`

Decrement numeric state.

```python
def decrement(self):
    return self.sub("count", 1)

def subtract_five(self):
    return self.sub("count", 5)
```

### `set(state_name, value)`

Set state to a value.

```python
def set_name(self):
    return self.set("username", "John Doe")

def clear(self):
    return self.set("count", 0)
```

### `toggle(state_name)`

Toggle boolean state.

```python
def toggle_menu(self):
    return self.toggle("is_open")
```

## Calling Methods from Templates

Call methods using the `@event` syntax:

```html
<template>
  <div>
    <p>Count: {{ count }}</p>
    <button @click="increment">Increment</button>
    <button @click="decrement">Decrement</button>
    <button @click="reset">Reset</button>
  </div>
</template>
```

## Complex State Updates

Chain multiple operations:

```python
def reset_form(self):
    return [
        self.set("email", ""),
        self.set("password", ""),
        self.set("errors", {}),
        self.set("is_submitted", False),
    ]
```

Perform conditional updates in lifecycle:

```python
def on_mount(self):
    # Initialize state based on props
    if some_condition:
        return [self.set("count", 100)]
    return []
```

## State with Derived Values

Use computed properties via `context()` for server-side computed values:

```python
def context(self, props):
    count = int(props.get("count", 0))
    max_value = int(props.get("max", 10))
    percentage = (count / max_value) * 100
    
    return {
        "count": count,
        "max_value": max_value,
        "percentage": percentage,
        "is_complete": count >= max_value,
    }
```

For client-side computed values, calculate them in methods:

```python
class MyClient(ClientMethods):
    class CountState:
        name = "count"
        default = 0
        cast = "int"
    
    State = [CountState]
    Methods = ["increment"]
    
    def increment(self):
        # Compute derived value
        is_even = (self.count + 1) % 2 == 0
        return [
            self.add("count", 1),
            self.set("is_even", is_even),
        ]
```

## State Lifecycle

### 1. Initialization

State initializes with `default` or `from_prop` value:

```python
class StartState:
    name = "count"
    from_prop = "start"
    default = 0
    cast = "int"
```

If component rendered with `<Counter start="5" />`:
- `count` initializes to `5`

If rendered as `<Counter />`:
- `count` initializes to `0`

### 2. Mounting

After initial render, `on_mount()` can set initial values:

```python
def on_mount(self):
    return [self.set("count", 10)]
```

### 3. Updates

User interaction triggers methods, which update state:

```python
def increment(self):
    return self.add("count", 1)  # Automatically triggers re-render
```

### 4. Unmounting

`on_unmount()` is called when component removed:

```python
def on_unmount(self):
    # Cleanup: close connections, cancel timers, etc.
    return []
```

## State Best Practices

### 1. Keep State Simple

Store only values that change:

```python
# Good - minimal state
class CountState:
    name = "count"
    default = 0

class IsOpenState:
    name = "is_open"
    default = False
```

### 2. Normalize State

Avoid redundant data:

```python
# Avoid storing derived values
# Instead of:
class User:
    name = "user"
    is_admin = False  # Derived from user.role
    is_logged_in = True  # Derived from user

# Do this:
class User:
    name = "user"  # Store only the user data
    # Compute is_admin and is_logged_in in template/methods
```

### 3. Use Props for Initial Values

Let parents control component behavior:

```python
# Good - uses props
class StartState:
    name = "count"
    from_prop = "start"  # Configurable by parent
    default = 0

# Parent can now do:
# <Counter start="10" /> or <Counter />
```

### 4. Name State Clearly

Use clear, descriptive names:

```python
# Good names
class IsLoadingState:
    name = "is_loading"

class CurrentUserState:
    name = "current_user"

class ErrorMessageState:
    name = "error_message"

# Avoid unclear names
class DataState:
    name = "data"  # Too vague

class TempState:
    name = "temp"  # Unclear purpose
```

### 5. Type State Correctly

Use appropriate `cast` types:

```python
# Good - appropriate types
class CountState:
    name = "count"
    cast = "int"

class IsActiveState:
    name = "is_active"
    cast = "bool"

class PriceState:
    name = "price"
    cast = "float"

# Avoid type mismatches
class CountState:
    name = "count"
    cast = "str"  # Wrong! Will break arithmetic
```

## Example: Login Form State

```python
class Component:
    def context(self, props):
        return {
            "title": "Login",
            "submit_label": "Sign In",
        }
    
    def client(self):
        class LoginClient(ClientMethods):
            class EmailState:
                name = "email"
                default = ""
                cast = "str"
            
            class PasswordState:
                name = "password"
                default = ""
                cast = "str"
            
            class IsLoadingState:
                name = "is_loading"
                default = False
                cast = "bool"
            
            class ErrorState:
                name = "error_message"
                default = ""
                cast = "str"
            
            State = [EmailState, PasswordState, IsLoadingState, ErrorState]
            Methods = ["submit", "clear_error"]
            
            def submit(self):
                # Validate and submit
                if not self._is_valid_email(self.email):
                    return self.set("error_message", "Invalid email")
                
                return [
                    self.set("is_loading", True),
                    self.set("error_message", ""),
                ]
            
            def clear_error(self):
                return self.set("error_message", "")
            
            def _is_valid_email(self, email):
                return "@" in email
            
            def on_mount(self):
                return []
        
        return LoginClient()
</python>

<template>
  <form @submit="submit">
    <h2>{{ title }}</h2>
    
    <div v-if="error_message" class="alert alert-error">
      {{ error_message }}
      <button type="button" @click="clear_error">×</button>
    </div>
    
    <div class="form-group">
      <label for="email">Email</label>
      <input 
        id="email"
        type="email"
        :value="email"
        placeholder="you@example.com"
      />
    </div>
    
    <div class="form-group">
      <label for="password">Password</label>
      <input 
        id="password"
        type="password"
        :value="password"
        placeholder="••••••••"
      />
    </div>
    
    <button type="submit" :disabled="is_loading">
      {{ is_loading ? "Signing in..." : submit_label }}
    </button>
  </form>
</template>
```

## Next Steps

- [Templates](./templates.md) - Template syntax and features
- [Component Communication](./communication.md) - Pass data between components
- [API Reference](../api/index.md) - Complete API documentation
