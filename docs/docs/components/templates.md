---
sidebar_position: 3
---

# Template Syntax

Master the template language for Lua SPA components.

## Variable Interpolation

Use `{{ }}` syntax to insert values into templates:

```html
<template>
  <h1>{{ title }}</h1>
  <p>Hello, {{ user_name }}!</p>
</template>
```

Interpolation supports expressions:

```html
<p>{{ user_name.upper() }}</p>
<p>{{ count * 2 }}</p>
<p>{{ is_open ? 'Open' : 'Closed' }}</p>
```

## Directives

### v-if / v-else / v-else-if

Conditionally render elements:

```html
<!-- Single condition -->
<p v-if="is_loading">Loading...</p>

<!-- If/Else -->
<p v-if="has_items">You have items</p>
<p v-else>No items yet</p>

<!-- If/Else-if/Else -->
<div v-if="status === 'pending'">Pending...</div>
<div v-else-if="status === 'success'">Success!</div>
<div v-else>Error</div>
```

The condition can be any Python expression evaluated in the template context.

### v-show

Similar to `v-if` but always renders the element, just hides it with CSS:

```html
<div v-show="is_visible">
  This is always in the DOM, just hidden
</div>
```

**When to use:**
- `v-if` - Elements toggle frequently (performance)
- `v-show` - Elements toggle frequently but CSS transitions are needed

### v-for

Render a list of items:

```html
<!-- Simple list -->
<ul>
  <li v-for="item in items">{{ item }}</li>
</ul>

<!-- Access index -->
<ol>
  <li v-for="(item, index) in items">
    {{ index + 1 }}. {{ item.name }}
  </li>
</ol>

<!-- Key binding for efficient updates -->
<ul>
  <li v-for="item in items" :key="item.id">
    {{ item.name }}
  </li>
</ul>

<!-- Nested loops -->
<div v-for="user in users">
  <h2>{{ user.name }}</h2>
  <ul>
    <li v-for="item in user.items">{{ item.name }}</li>
  </ul>
</div>
```

**Important**: Always use `:key` when rendering lists to improve performance:

```html
<!-- Good -->
<li v-for="item in items" :key="item.id">{{ item.name }}</li>

<!-- Less efficient, if items order changes -->
<li v-for="item in items">{{ item.name }}</li>
```

## Attribute Binding

### :attribute or v-bind

Bind dynamic values to attributes:

```html
<!-- Class binding -->
<div :class="{ active: is_active, disabled: is_disabled }">
  Button
</div>

<!-- Style binding -->
<div :style="{ color: text_color, backgroundColor: bg_color }">
  Styled text
</div>

<!-- Any attribute -->
<img :src="image_url" :alt="image_alt" />
<button :disabled="is_loading">{{ button_text }}</button>
<a :href="link_url">Link</a>

<!-- Boolean attributes -->
<input type="checkbox" :checked="is_checked" />
<option :selected="is_selected">Option</option>

<!-- Object spread (dynamic attributes) -->
<div v-bind="attributes">Content</div>
```

### Class Binding

Multiple ways to bind classes:

```html
<!-- Object notation -->
<div :class="{ active: is_active, error: has_error }">
  Content
</div>

<!-- Array notation -->
<div :class="[base_class, is_active ? 'active' : '']">
  Content
</div>

<!-- String interpolation -->
<div class="btn {{ is_active ? 'btn-active' : 'btn-inactive' }}">
  Button
</div>
```

### Style Binding

```html
<!-- Object notation -->
<div :style="{ 
  color: text_color,
  fontSize: font_size + 'px',
  backgroundColor: bg_color 
}">
  Styled content
</div>

<!-- Computed in template -->
<div :style="{ width: width_percent + '%' }">
  Progress bar
</div>
```

## Event Binding

### @event

Bind to DOM events:

```html
<!-- Click -->
<button @click="handle_click">Click me</button>

<!-- Input -->
<input @input="handle_input" />

<!-- Change -->
<select @change="handle_change">
  <option>Option 1</option>
</select>

<!-- Submit -->
<form @submit="handle_submit">
  <button type="submit">Submit</button>
</form>

<!-- Other events -->
<button @focus="on_focus">Focus me</button>
<button @blur="on_blur">Blur me</button>
<input @keypress="on_keypress" />
<input @keydown="on_keydown" />
<input @keyup="on_keyup" />
```

### Event Modifiers

Modify event behavior:

```html
<!-- Prevent default -->
<a href="#" @click.prevent="handle_click">Link</a>

<!-- Stop propagation -->
<button @click.stop="handle_click">Button</button>

<!-- Self (only trigger if target is self) -->
<div @click.self="handle_click">
  <button>Button inside</button>
</div>

<!-- Keyboard modifiers -->
<input @keyup.enter="handle_enter" />
<input @keydown.escape="handle_escape" />
<input @keydown.space="handle_space" />

<!-- Mouse modifiers -->
<button @click.left="handle_left_click">Left click</button>
<button @click.right="handle_right_click">Right click</button>

<!-- Combination -->
<input @keyup.ctrl.enter="handle_ctrl_enter" />
```

## Form Handling

### Input Fields

```html
<input 
  type="text"
  :value="email"
  @input="update_email"
  placeholder="Enter email"
/>

<input 
  type="password"
  :value="password"
  @input="update_password"
/>

<textarea 
  :value="message"
  @input="update_message"
></textarea>
```

### Checkboxes

```html
<!-- Single checkbox -->
<input 
  type="checkbox"
  :checked="agree"
  @change="toggle_agree"
/>
I agree

<!-- Multiple checkboxes -->
<label v-for="option in options" :key="option.id">
  <input 
    type="checkbox"
    :checked="selected_ids.includes(option.id)"
    @change="toggle_option"
  />
  {{ option.label }}
</label>
```

### Radio Buttons

```html
<label v-for="option in options" :key="option.id">
  <input 
    type="radio"
    :value="option.id"
    :checked="selected_id === option.id"
    @change="set_option"
  />
  {{ option.label }}
</label>
```

### Select Dropdown

```html
<select :value="selected_option" @change="update_option">
  <option value="">Choose...</option>
  <option v-for="option in options" :key="option.id" :value="option.id">
    {{ option.label }}
  </option>
</select>
```

## Conditional Classes and Styles

### Dynamic Classes

```html
<!-- Object syntax (recommended) -->
<button :class="{ 
  active: is_active,
  loading: is_loading,
  error: has_error
}">
  Click me
</button>

<!-- Array syntax -->
<div :class="[
  base_class,
  is_active ? 'btn-active' : 'btn-inactive',
  size_class
]">
  Content
</div>

<!-- With static classes -->
<div class="button" :class="{ primary: is_primary }">
  Button
</div>
```

### Dynamic Styles

```html
<div :style="{ 
  color: text_color,
  backgroundColor: background_color,
  opacity: transparency,
  transform: 'rotate(' + angle + 'deg)'
}">
  Styled content
</div>
```

## Component Props

Pass data to child components via attributes:

```html
@import Button from "./Button.lspa"
@import Card from "./Card.lspa"

<template>
  <!-- String props -->
  <Button label="Click me" type="primary" />
  
  <!-- Dynamic props -->
  <Button :label="button_label" :disabled="is_disabled" />
  
  <!-- Boolean props -->
  <Card :highlighted="is_featured" :clickable={true} />
  
  <!-- Object/Array props -->
  <Card :item="current_item" :items="all_items" />
</template>
```

## Comments

HTML comments in templates:

```html
<!-- This is a comment -->
<div>
  <!-- Comments are removed during rendering -->
  <p>Content</p>
</div>
```

## Advanced Patterns

### Computed Values

Use expressions for computed values:

```html
<div>
  <!-- Calculate in template -->
  <p>Total: ${{ price * quantity }}</p>
  <p>Discount: ${{ price * quantity * discount_rate }}</p>
</div>
```

For reusable computed values, use `context()`:

```python
def context(self, props):
    price = float(props.get("price", 0))
    quantity = int(props.get("quantity", 1))
    total = price * quantity
    
    return {
        "price": price,
        "quantity": quantity,
        "total": total,
    }
```

### Nested Conditionals

```html
<div v-if="user_logged_in">
  <div v-if="user.is_admin">
    <p>Welcome, admin!</p>
  </div>
  <div v-else>
    <p>Welcome, user!</p>
  </div>
</div>
<div v-else>
  <p>Please log in</p>
</div>
```

### Filter-like Operations

```html
<!-- Using list comprehension in context -->
<ul v-for="item in available_items">
  <li>{{ item.name }}</li>
</ul>
```

Where `available_items` is computed in `context()`:

```python
def context(self, props):
    items = props.get("items", [])
    available = [i for i in items if i.get("in_stock")]
    return {"available_items": available}
```

## Template Errors

### Common Mistakes

```html
<!-- Wrong: Missing curly braces -->
<p>Hello, name!</p>  <!-- Renders literally "name" -->
<p>Hello, {{ name }}!</p>  <!-- Correct -->

<!-- Wrong: Missing quotes in attributes -->
<button @click=handle_click></button>  <!-- Syntax error -->
<button @click="handle_click"></button>  <!-- Correct -->

<!-- Wrong: Undefined variables -->
<p>{{ undefined_var }}</p>  <!-- Shows empty or error -->

<!-- Wrong: Method calls in template (not supported) -->
<p>{{ user.method() }}</p>  <!-- Won't execute -->
<!-- Use context() to compute values instead -->
```

## Best Practices

1. **Keep templates simple** - Move complex logic to `context()` or methods
2. **Use `:key` in loops** - Improves rendering performance
3. **Bind boolean attributes** - Use `:checked`, `:disabled`, etc.
4. **Name variables clearly** - Use `is_active`, not `active`
5. **Use v-for with objects** - More efficient than conditional rendering
6. **Comment complex sections** - Help future readers understand intent

## Next Steps

- [State Management](./state.md) - Manage component state
- [Component Communication](./communication.md) - Pass data between components
