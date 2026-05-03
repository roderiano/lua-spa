---
sidebar_position: 2
title: Quick Start
---

# Quick Start

From zero to a running SPA in under 5 minutes.

## 1. Create a project

```bash
lua-spa create my_app
cd my_app
```

This copies the built-in `lua_template` scaffold into `./my_app/`.

## 2. Run the dev server

```bash
lua-spa serve
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## 3. Live reload

```bash
lua-spa serve --reload
```

The server watches `.lspa`, `.py`, `.css`, and `.js` files. The browser refreshes automatically when any file changes.

## What happens on `serve`

```mermaid
sequenceDiagram
    participant CLI as lua-spa serve
    participant FW as SpaFramework
    participant Loader as ComponentLoader
    participant Server as HTTP Server
    participant Browser

    CLI->>FW: create_default_framework()
    FW->>Loader: load_entry("App")
    Loader-->>FW: ComponentDefinition registry
    FW->>Server: serve(host, port)
    Browser->>Server: GET /
    Server->>FW: build_view()
    FW-->>Server: HTML + JS bootstrap
    Server-->>Browser: 200 OK
```
