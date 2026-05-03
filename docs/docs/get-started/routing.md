---
sidebar_position: 5
title: Routing
---

# Routing

lua-spa has a built-in router configured entirely in `spa.config.json`. No extra code needed.

## Basic setup

```json
{
  "page_title": "my_app",
  "entry_component": "App",
  "router": {
    "routes": [
      { "path": "/",       "component": "Home" },
      { "path": "/about",  "component": "About" },
      { "path": "/users/:id", "component": "UserDetail" }
    ]
  }
}
```

## Route parameters

Dynamic segments start with `:`. The value is passed as a prop to the component:

```html
<template>
  <h1>User {{ props.id }}</h1>
</template>
```

## Nested routes

```json
{
  "routes": [
    {
      "path": "/dashboard",
      "component": "Dashboard",
      "children": [
        { "index": true, "component": "DashboardHome" },
        { "path": "settings", "component": "Settings" }
      ]
    }
  ]
}
```

## Route resolution flow

```mermaid
flowchart TD
    A[Browser GET /dashboard/settings] --> B[Router.resolve]
    B --> C{Match /dashboard?}
    C -- yes --> D[RouteComponent: Dashboard]
    D --> E{Match child settings?}
    E -- yes --> F[RouteComponent: Settings]
    F --> G[Render cascaded stack]
    G --> H["<Dashboard><Settings /></Dashboard>"]
    C -- no --> I[KeyError: Route not found]
```

## Wildcard / fallback

```json
{ "path": "*", "component": "NotFound" }
```

## Guard (meta)

Routes support arbitrary `meta` and a `guard` field for future middleware hooks:

```json
{
  "path": "/admin",
  "component": "Admin",
  "guard": "auth",
  "meta": { "requiresAuth": true }
}
```
