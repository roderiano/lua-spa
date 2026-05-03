---
sidebar_position: 1
title: Architecture
---

# Architecture

lua-spa is a Python-first SPA framework that blends **server-side rendering** with **client-side hydration**. It has no JavaScript build step — the browser runtime is a single self-contained script embedded at build time.

## High-level architecture

```mermaid
graph TB
    subgraph Python ["Python (server)"]
        config["spa.config.json"]
        loader["ComponentLoader"]
        renderer["Renderer"]
        codegen["CodeGen"]
        fw["SpaFramework"]
        server["SpaServer"]
    end

    subgraph Browser ["Browser (client)"]
        rt["SPA Runtime JS"]
        dom["DOM Diff/Patch"]
        hooks["useState hooks"]
    end

    config --> fw
    fw --> loader
    loader --> renderer
    loader --> codegen
    fw --> server
    server -->|HTML + Bootstrap JSON| Browser
    rt --> dom
    rt --> hooks
```

## Request lifecycle

```mermaid
sequenceDiagram
    participant Client as Browser
    participant Server as SpaServer
    participant FW as SpaFramework
    participant Loader as ComponentLoader
    participant Renderer as Renderer
    participant CG as CodeGen

    Client->>Server: GET /
    Server->>FW: build_view()
    FW->>Loader: load_entry("App")
    Loader->>Loader: parse .lspa files recursively
    Loader->>CG: build_client_script(python_block)
    CG-->>Loader: setup() JS function
    Loader-->>FW: ComponentDefinition registry
    FW->>Renderer: render_template_with_directives()
    Renderer-->>FW: SSR HTML string
    FW->>FW: embed registry JSON + bootstrap JSON + runtime JS
    FW-->>Server: complete HTML page
    Server-->>Client: 200 OK
    Client->>Client: runtime hydrates DOM
```

## Module map

```mermaid
graph LR
    main["main.py<br/><small>CLI entrypoint</small>"]
    app["app.py<br/><small>factory helpers</small>"]
    fw["framework.py<br/><small>SpaFramework</small>"]
    loader["loader.py<br/><small>ComponentLoader</small>"]
    renderer["renderer.py<br/><small>SSR template engine</small>"]
    codegen["codegen.py<br/><small>Python→JS compiler</small>"]
    scope["scope.py<br/><small>Python exec sandbox</small>"]
    trace["trace.py<br/><small>operation tracing proxies</small>"]
    router["router.py<br/><small>Router</small>"]
    server["server.py<br/><small>ThreadingHTTPServer</small>"]
    rt["runtime_assets.py<br/><small>embedded JS runtime</small>"]
    types["types.py<br/><small>shared dataclasses</small>"]

    main --> app
    app --> fw
    fw --> loader
    fw --> renderer
    fw --> router
    fw --> server
    fw --> rt
    loader --> codegen
    codegen --> scope
    codegen --> trace
    loader --> types
    fw --> types
```

## Design principles

1. **No build step** — The Python package ships a self-contained JS runtime. Users never run `npm`.
2. **SSR first** — Every page load starts as server-rendered HTML. JavaScript enhances, not replaces.
3. **Python is the authority** — Component logic lives in Python. JavaScript is generated automatically.
4. **Zero client dependencies** — The browser runtime has no external npm dependencies.
