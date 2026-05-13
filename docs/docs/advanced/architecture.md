---
sidebar_position: 1
title: Architecture
---

# Architecture

moon-spa is a Python-first SPA framework that blends **server-side rendering** with **client-side hydration**. It has no JavaScript build step — the browser runtime is a single self-contained script embedded at build time.

## High-level architecture

```mermaid
flowchart TB
    subgraph Python ["Python (server)"]
        config["spa.config.json"]
        loader["ComponentLoader"]
        renderer["Renderer"]
        codegen["CodeGen"]
        scope["Scope (setup inference)"]
        fw["SpaFramework"]
        server["SpaServer"]
    end

    subgraph Browser ["Browser (client)"]
        boot["SSR page + bootstrap"]
        rt["SPA Runtime JS"]
        dom["DOM Diff/Patch"]
        actions["Action dispatcher"]
        sse["Reload stream listener"]
    end

    config --> fw
    fw --> loader
    loader --> renderer
    loader --> codegen
    codegen --> scope
    fw --> server
    server -->|HTML + Bootstrap JSON| boot
    boot --> rt
    rt -->|POST __moon_spa_action| server
    server -->|state props patch JSON| rt
    rt -->|GET __reload__ reload mode| server
    rt --> dom
    rt --> actions
    rt --> sse
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
    participant Scope as Scope

    Client->>Server: GET /
    Server->>FW: build_view()
    FW->>Loader: load_entry("App")
    Loader->>Loader: parse .lspa files recursively
    Loader->>Scope: resolve_component_callables()
    Scope-->>Loader: setup spec (explicit or inferred)
    Loader->>CG: build_client_script(python_block)
    CG-->>Loader: setup() JS function
    Loader-->>FW: ComponentDefinition registry
    FW->>Renderer: render_template_with_directives()
    Renderer-->>FW: SSR HTML string
    FW->>FW: embed registry JSON + bootstrap JSON + runtime JS
    FW-->>Server: complete HTML page
    Server-->>Client: 200 OK
    Client->>Client: runtime hydrates DOM
    Client->>Server: POST /__moon_spa_action (callable action/lifecycle)
    Server->>FW: execute_server_callable(...)
    FW-->>Server: state/props patch
    Server-->>Client: {ok, result}
```

## Module map

```mermaid
flowchart LR
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
4. **Server-driven callables** — Callable actions/lifecycle run through `POST /__moon_spa_action` and patch state/props deterministically.
5. **Inference by default** — `setup(self, props)` may omit return mapping; server infers props/state/data/actions/lifecycle.
6. **Zero client dependencies** — The browser runtime has no external npm dependencies.
