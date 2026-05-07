---
sidebar_position: 11
title: Routing
---

# Routing

The lua-spa router is configured entirely in `spa.config.json` — no code needed. It supports nested routes, dynamic parameters, index routes, wildcard fallbacks, and route guards.

```mermaid
flowchart TD
    A["spa.config.json"] -->|"router.routes"| B["Router.from_config()"]
    B --> C["Router.resolve(path)"]
    C --> D["RouteMatch\n(components + params)"]
    D --> E["Router.render()"]
    E --> F["Cascaded component tags"]
    F --> G["SpaFramework renders to HTML"]
```

---

## Basic setup

Add a `"router"` key to `spa.config.json`:

```json
{
  "page_title": "My App",
  "server": { "host": "127.0.0.1", "port": 8000 },
  "router": {
    "routes": [
      { "path": "/",      "component": "Home" },
      { "path": "/about", "component": "About" },
      { "path": "/blog",  "component": "Blog" }
    ]
  }
}
```

When `router` is enabled, route rendering is driven by `router.routes`.

### Router contract (standard)

- `router.routes`: defines which components are matched and rendered.
- with `"initial_path": "/"`, rendering starts from the route that matches `"/"`.
- if you want a layout shell, declare it as a route `component` and nest children under it.

Recommended route shape for layout apps:

```json
{
  "router": {
    "routes": [
      {
        "path": "/",
        "component": "Layout",
        "children": [
          { "index": true, "component": "Home" },
          { "path": "about", "component": "About" }
        ]
      }
    ]
  }
}
```

---

## Route parameters

Prefix a path segment with `:` to capture it as a prop:

```json
{ "path": "/users/:id",          "component": "UserDetail" },
{ "path": "/posts/:year/:month", "component": "PostArchive" }
```

The captured values are passed to the component as props and available in the template:

```html
<python>
class UserDetail(Component):
  def setup(self, props):
    return {
      "props": props,
      "state": {},
      "data": {"user_id": props.get("id", "unknown")},
      "actions": {},
      "lifecycle": {},
    }
</python>

<template>
  <h1>User {{ py.user_id }}</h1>
</template>
```

Multiple params in one path:

```html
<python>
class PostArchive(Component):
  def setup(self, props):
    data = {
      "year":  props.get("year"),
      "month": props.get("month"),
    }
    
    return {
      "props": props,
      "state": {},
      "data": data,
      "actions": {},
      "lifecycle": {},
    }
</python>

<template>
  <h2>Posts from {{ py.month }}/{{ py.year }}</h2>
</template>
```

---

## Nested routes

Use `"children"` to nest routes inside path groups:

```json
{
  "router": {
    "routes": [
      {
        "path": "/",
        "children": [
          { "index": true,         "component": "Home" },
          { "path": "about",       "component": "About" },
          { "path": "users",       "component": "UserList" },
          { "path": "users/:id",   "component": "UserDetail" }
        ]
      }
    ]
  }
}
```

The router resolves the full stack — parent first, then child — and renders them as nested component tags for the routed outlet:

```html
<!-- resolved for /users/42 -->
<UserLayout>
  <UserDetail __props="...id=42..." />
</UserLayout>
```

### Resolution flow

```mermaid
flowchart TD
  A["GET /users/42"] --> B["Match / (group route)"]
  B --> C["Match child users/:id → UserDetail"]
    C --> D["params: {id: '42'}"]
  D --> E["Render matched component stack"]
```

### How `children` is implemented in lua-spa

Internally, nested routing happens in three stages:

1. Route tree normalization:
   The router reads `children` recursively from `router.routes` and builds a tree of route nodes.
2. Recursive match:
   `Router.resolve(path)` matches the parent route first, then keeps matching against `children` with remaining path segments.
3. Cascaded render:
   `Router.render(match)` creates nested tags from child to parent, so parent layouts wrap child pages.

For `/users/42`, the routed stack is equivalent to:

```html
<UserLayout __props="...routeParams...">
  <UserDetail __props="...routeParams.id=42..." />
</UserLayout>
```

The final output is the rendered route stack.
If the parent route is a layout component, child content is passed to that layout as `children`.

### Practical example (router + `.lspa`)

`spa.config.json`:

```json
{
  "page_title": "Nested Users",
  "router": {
    "initial_path": "/users/42",
    "routes": [
      {
        "path": "/",
        "component": "AppLayout",
        "children": [
          { "index": true,       "component": "HomePage" },
          { "path": "users",    "component": "UserListPage" },
          { "path": "users/:id", "component": "UserDetailPage" }
        ]
      }
    ]
  }
}
```

`AppLayout.lspa`:

```html
@import Nav from './Nav/Nav.lspa'

<python>
class AppLayout(Component):
    pass
</python>

<template>
  <div class="layout">
    <Nav />
    <main class="layout__content">
      {{ children }}
    </main>
  </div>
</template>
```

`UserDetailPage.lspa`:

```html
<python>
class UserDetailPage(Component):
  def setup(self, props):
        params = props.get("routeParams", {})
    return {
      "props": props,
      "state": {},
      "data": {"user_id": params.get("id", "unknown")},
      "actions": {},
      "lifecycle": {},
    }
</python>

<template>
  <article>
    <h1>User {{ py.user_id }}</h1>
  </article>
</template>
```

With `"initial_path": "/users/42"`, the rendered structure is:

```html
<AppLayout>
  <HomePage /><!-- for "/" -->
  <!-- or -->
  <UserDetailPage /><!-- for "/users/42" -->
</AppLayout>
```

---

## Index routes

An `"index": true` route matches when the parent path is matched exactly (no extra segments):

```json
{
  "path": "/dashboard",
  "component": "Dashboard",
  "children": [
    { "index": true,        "component": "DashboardHome" },
    { "path": "settings",   "component": "Settings" },
    { "path": "analytics",  "component": "Analytics" }
  ]
}
```

| URL | Renders |
|-----|---------|
| `/dashboard` | `Dashboard` + `DashboardHome` |
| `/dashboard/settings` | `Dashboard` + `Settings` |
| `/dashboard/analytics` | `Dashboard` + `Analytics` |

---

## Wildcard / 404 fallback

Use `"path": "*"` as the last route to catch unmatched paths:

```json
{
  "router": {
    "routes": [
      { "path": "/",     "component": "Home" },
      { "path": "/about","component": "About" },
      { "path": "*",     "component": "NotFound" }
    ]
  }
}
```

Wildcard also works inside `children` to catch unknown sub-paths:

```json
{
  "path": "/app",
  "component": "App",
  "children": [
    { "index": true, "component": "Dashboard" },
    { "path": "*",   "component": "NotFound" }
  ]
}
```

---

## Static props on routes

Pass static props to a component directly from the route config:

```json
{
  "path": "/help",
  "component": "Page",
  "props": { "slug": "help", "title": "Help Center" }
}
```

These are merged with any dynamic params before being passed to the component.

---

## Route metadata

Attach arbitrary metadata to a route with `"meta"`:

```json
{
  "path": "/admin",
  "component": "Admin",
  "meta": { "requiresAuth": true, "role": "admin" }
}
```

`meta` is available in the component as `props.routeMeta`:

```html
<python>
class Admin(Component):
  def setup(self, props):
        meta = props.get("routeMeta", {})
    return {
      "props": props,
      "state": {},
      "data": {"requires_auth": meta.get("requiresAuth", False)},
      "actions": {},
      "lifecycle": {},
    }
</python>
```

---

## Route guards

The `"guard"` field names a JavaScript guard function registered on `window.LuaSpaGuards`. Guards run client-side before navigation:

```json
{
  "path": "/settings",
  "component": "Settings",
  "guard": "requireLogin"
}
```

```js
// In a <script> tag or separate JS file loaded before the SPA
window.LuaSpaGuards = {
  requireLogin: function (route) {
    if (!localStorage.getItem("token")) {
      return "/login";   // redirect
    }
    return true;         // allow
  }
};
```

---

## `initial_path`

Control which route is rendered for the first server-side HTML response:

```json
{
  "router": {
    "initial_path": "/dashboard",
    "routes": [ ... ]
  }
}
```

Defaults to `"/"` if omitted.

---

## Full example: layout + sections

```json
{
  "page_title": "Docs",
  "server": { "host": "127.0.0.1", "port": 8000 },
  "router": {
    "initial_path": "/",
    "routes": [
      {
        "path": "/",
        "component": "Layout",
        "children": [
          { "index": true,          "component": "Home" },
          { "path": "guide",        "component": "Guide" },
          { "path": "guide/:slug",  "component": "GuidePage" },
          { "path": "api",          "component": "ApiRef" },
          { "path": "*",            "component": "NotFound" }
        ]
      }
    ]
  }
}
```

`Layout.lspa`:

```html
@import Nav from './Nav/Nav.lspa'

<python>
class Layout(Component):
    pass
</python>

<template>
  <div class="layout">
    <Nav />
    <main class="layout__content">
      {{ children }}
    </main>
  </div>
</template>
```

`GuidePage.lspa`:

```html
<python>
class GuidePage(Component):
  def setup(self, props):
    return {
      "props": props,
      "state": {},
      "data": {"slug": props.get("slug", "")},
      "actions": {},
      "lifecycle": {},
    }
</python>

<template>
  <article>
    <h1>{{ py.slug }}</h1>
  </article>
</template>
```

```mermaid
flowchart LR
    A["GET /guide/actions"] --> B["Match / → Layout"]
    B --> C["Match guide/:slug → GuidePage"]
    C --> D["params: {slug: 'actions'}"]
    D --> E["Layout wraps GuidePage\nwith slug prop"]
```
