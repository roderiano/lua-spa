---
sidebar_position: 10
title: Backend Integration
---

# Backend Integration

moon-spa is a Python framework. Its HTTP server is intentionally minimal — but you can embed it inside a larger Python application or replace the server entirely.

## Using `SpaFramework` directly

```python
from pathlib import Path
from moon_spa.framework import SpaFramework

framework = SpaFramework(
    view_file=Path("my_app/index.lspa"),
    components_dir=Path("my_app/components"),
    static_dir=Path("my_app/static"),
    page_title="My App",
    port=8080,
)
framework.serve(reload=True)
```

## Generating HTML without serving

`build_view()` returns a plain string — no server required:

```python
html = framework.build_view(props={"user": "alice"})
# Write to a file, return from another web framework, etc.
with open("dist/index.html", "w") as f:
    f.write(html)
```

## Embedding in Flask / FastAPI

```python
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from moon_spa.app import create_default_framework

api = FastAPI()
spa = create_default_framework()

@api.get("/")
def serve_spa():
    return HTMLResponse(spa.build_view())

@api.get("/api/data")
def get_data():
    return {"hello": "world"}
```

## Architecture with external backend

```mermaid
flowchart LR
    Browser -->|GET /| SpaFramework
    SpaFramework -->|build_view| HtmlPage
    HtmlPage -->|SSR + bootstrap| Browser
    Browser -->|POST /__moon_spa_action| SpaFramework
    SpaFramework -->|state/props patch| Browser
    Browser -->|GET /__reload__| SpaFramework
    Browser -->|fetch /api/...| FastAPI
    FastAPI -->|JSON| Browser
    Browser -->|state updates| ReRender
```

## Runtime bridge endpoints

When using moon-spa built-in server, these runtime routes are reserved:

- `POST /__moon_spa_action`: executes callable actions/lifecycle and returns `{ok, result}`
- `GET /__reload__`: SSE stream used only when `serve(..., reload=True)`

If you embed moon-spa behind another framework/proxy, preserve these routes or mount moon-spa
under a dedicated prefix and update your integration accordingly.

## Passing server data to components

Use `build_view(props={...})` to inject server-side data at render time:

```python
user = db.get_user(session["user_id"])
html = framework.build_view(props={"username": user.name, "role": user.role})
```

The props flow into `setup(self, props)` on the server and into `resolvedProps` on the client.
