---
sidebar_position: 5
title: spa.config.json
---

# spa.config.json

The project configuration file, placed at the root of the `lua_template` directory.

## Full schema

```json
{
  "page_title": "my_app",
  "entry_component": "App",
  "mount_id": "app",
  "initial_props": {
    "user": "guest"
  },
  "server": {
    "host": "127.0.0.1",
    "port": 8000
  },
  "router": {
    "routes": [
      {
        "path": "/",
        "component": "Home",
        "props": {},
        "children": [],
        "index": false,
        "guard": null,
        "meta": {}
      }
    ]
  }
}
```

## Fields

| Field | Type | Default | Description |
|---|---|---|---|
| `page_title` | `string` | `"lua-spa"` | HTML `<title>` tag value |
| `entry_component` | `string` | `"App"` | Root component name (must exist in `components/`) |
| `mount_id` | `string` | `"app"` | DOM element ID where the app mounts |
| `initial_props` | `object` | `{}` | Default props passed to the entry component |
| `server.host` | `string` | `"127.0.0.1"` | Bind address |
| `server.port` | `number` | `8000` | Port |
| `router` | `object \| null` | `null` | Router configuration (see [Router API](/docs/api/router)) |

## Minimal config

```json
{
  "page_title": "hello",
  "server": { "host": "0.0.0.0", "port": 3000 }
}
```

## Config loading

```mermaid
flowchart LR
    A["spa.config.json"] -->|parsed| B[LuaTemplateConfig dataclass]
    B --> C[SpaFramework.__init__]
```

`LuaTemplateConfig` is a frozen dataclass defined in `lua_spa.types`.
