---
sidebar_position: 1
---

# Components

Components are the building blocks of Lua SPA applications. A component is a `.lspa` file that combines an HTML template with Python logic.

## What is a Component?

A `.lspa` file contains three sections:

1. **Imports** - Import other components
2. **Python Block** - Server and client logic
3. **Template** - HTML with Vue-like syntax

```html
@import OtherComponent from "./OtherComponent.lspa"

<python>
class Component:
    def context(self, props):
        # Server-side data
        return {"title": "My Component"}
    
    def client(self):
        # Client-side logic
        return {}
</python>

<template>
  <div>
    <h1>{{ title }}</h1>
    <OtherComponent />
  </div>
</template>
```

## Component Structure

### 1. Imports Section (Optional)

Import other components using `@import`:

```html
@import Button from "./Button.lspa"
@import Card from "./Card.lspa"
@import { Dialog, Tooltip } from "./Dialogs.lspa"
```

The imported component name must be used in the template.

### 2. Python Block

Define component logic in a `<python>` section:

```python
<python>
class Component:
    def context(self, props):
        """Server-side data for template rendering.
        
        Called during server-side render.
        Return dict with variables to interpolate in template.
        
        Args:
            props: Dict of component properties passed from parent
        
        Returns:
            Dict of server-side data for template
        """
        name = props.get("name", "World")
        return {
            "title": f"Hello, {name}!",
            "items": ["Item 1", "Item 2"],
        }
    
    def client(self):
        """Client-side component specification.
        
        Called on the client to set up interactive behavior.
        Return a client class with properties, state, methods, lifecycle.
        
        Returns:
            ClientMethods subclass or dict with client specs
        """
        from lua_spa.types import ClientMethods
        
        class MyComponentClient(ClientMethods):
            # Client properties (available in template)
            is_open = False
            button_label = "Click me"
            
            # State definitions
            class IsOpenState:
                name = "is_open"
                default = False
                cast = "bool"
            
            State = [IsOpenState]
            
            # Methods (callable from template events)
            Methods = ["toggle"]
            
            def toggle(self):
                return self.toggle("is_open")
            
            # Lifecycle hooks
            def on_mount(self):
                """Called when component mounts to DOM."""
                return []
            
            def on_update(self):
                """Called when component state changes."""
                return []
            
            def on_unmount(self):
                """Called when component removed from DOM."""
                return []
        
        return MyComponentClient()
</python>
```

### 3. Template Section

Write Vue-like templates in a `<template>` section:

```html
<template>
  <div class="component">
    <h1>{{ title }}</h1>
    
    <!-- Conditionals -->
    <p v-if="show_message">Message is visible</p>
    <p v-else>Message is hidden</p>
    
    <!-- Loops -->
    <ul>
      <li v-for="item in items" :key="item.id">
        {{ item.name }}
      </li>
    </ul>
    
    <!-- Event binding -->
    <button @click="toggle">
      {{ is_open ? "Close" : "Open" }}
    </button>
    
    <!-- Class binding -->
    <div :class="{ active: is_open, disabled: is_disabled }">
      Dynamic classes
    </div>
    
    <!-- Nested components -->
    <MyComponent :title="title" @event="handle_event" />
  </div>
</template>
```

## Component Props

Props are how parent components pass data to child components.

### Defining Props

Props are passed via HTML attributes:

```html
<Button label="Click me" type="primary" disabled={true} />
```

### Receiving Props

Access props in `context(props)`:

```python
def context(self, props):
    label = props.get("label", "Button")
    button_type = props.get("type", "default")
    is_disabled = props.get("disabled", False)
    
    return {
        "label": label,
        "button_type": button_type,
        "is_disabled": is_disabled,
    }
```

### Dynamic Props

Props can be variables from parent state:

```html
<Button :label="button_text" :disabled="is_loading" />
```

## Component Lifecycle

Components have several lifecycle hooks:

### `on_mount()`

Called when the component first renders and mounts to the DOM.

```python
def on_mount(self):
    """Initialize component, fetch data, set timers, etc."""
    return []  # Returns list of operations
```

### `on_update()`

Called when component state changes.

```python
def on_update(self):
    """Respond to state changes, validate, animate, etc."""
    return []
```

### `on_unmount()`

Called when component is removed from DOM.

```python
def on_unmount(self):
    """Cleanup: clear timers, unsubscribe, etc."""
    return []
```

## Example: Counter Component

```html
<python>
from lua_spa.types import ClientMethods

class Component:
    def context(self, props):
        start = int(props.get("start", 0))
        return {
            "label": props.get("label", "Counter"),
            "count": start,
        }
    
    def client(self):
        class CounterClient(ClientMethods):
            start = 0
            max_value = 10
            
            class CountState:
                name = "count"
                from_prop = "start"
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
            
            def on_mount(self):
                print("Counter mounted")
                return []
        
        return CounterClient()
</python>

<template>
  <div class="counter">
    <h2>{{ label }}</h2>
    <div class="value">{{ count }}</div>
    
    <div class="buttons">
      <button @click="decrement">-</button>
      <button @click="reset">Reset</button>
      <button @click="increment">+</button>
    </div>
    
    <p v-if="count >= max_value" class="warning">
      Maximum value reached!
    </p>
  </div>
</template>
```

## Example: Form Component

```html
<python>
from lua_spa.types import ClientMethods

class Component:
    def context(self, props):
        return {
            "title": props.get("title", "Form"),
            "submit_label": props.get("submit_label", "Submit"),
        }
    
    def client(self):
        class FormClient(ClientMethods):
            is_submitted = False
            
            class EmailState:
                name = "email"
                default = ""
                cast = "str"
            
            class PasswordState:
                name = "password"
                default = ""
                cast = "str"
            
            State = [EmailState, PasswordState]
            Methods = ["submit", "reset"]
            
            def submit(self):
                # In real app, would validate and send to server
                return self.set("is_submitted", True)
            
            def reset(self):
                # Reset form
                return [
                    self.set("email", ""),
                    self.set("password", ""),
                    self.set("is_submitted", False),
                ]
        
        return FormClient()
</python>

<template>
  <form @submit="submit">
    <h2>{{ title }}</h2>
    
    <div class="form-group">
      <label for="email">Email</label>
      <input 
        id="email"
        type="email" 
        @input="update_email"
        :value="email"
      />
    </div>
    
    <div class="form-group">
      <label for="password">Password</label>
      <input 
        id="password"
        type="password" 
        @input="update_password"
        :value="password"
      />
    </div>
    
    <button type="submit">{{ submit_label }}</button>
    
    <p v-if="is_submitted" class="success">
      Form submitted successfully!
    </p>
  </form>
</template>
```

## Component Patterns

### Container / Presentational

Split logic from presentation:

```html
<!-- Container.lspa -->
@import ItemList from "./ItemList.lspa"

<python>
class Component:
    def context(self, props):
        items = fetch_items()  # Fetch data
        return {"items": items}
    
    def client(self):
        return {}
</python>

<template>
  <ItemList :items="items" />
</template>
```

```html
<!-- ItemList.lspa -->
<python>
class Component:
    def context(self, props):
        return {"items": props.get("items", [])}
    
    def client(self):
        return {}
</python>

<template>
  <ul>
    <li v-for="item in items">{{ item.name }}</li>
  </ul>
</template>
```

### Higher-Order Components

Wrap components with additional logic:

```html
<!-- WithAuth.lspa -->
@import Page from "./Page.lspa"

<python>
class Component:
    def context(self, props):
        user = get_current_user()
        return {"user": user, "is_authenticated": user is not None}
    
    def client(self):
        return {}
</python>

<template>
  <div v-if="is_authenticated">
    <Page :user="user" />
  </div>
  <div v-else>
    <p>Please log in</p>
  </div>
</template>
```

## Best Practices

1. **Keep components small** - Aim for single responsibility
2. **Props for input** - Pass data via props, not global state
3. **Separate concerns** - Distinguish server logic from client logic
4. **Meaningful names** - Use clear, descriptive names
5. **Document interfaces** - Comment on props and expected behavior
6. **Handle edge cases** - Provide defaults for missing props
7. **Test components** - Write unit tests for logic

## Next Steps

- [State Management](./state.md) - Learn about state in detail
- [Template Syntax](./templates.md) - Deep dive into template features
- [Component Communication](./communication.md) - Pass data between components
