---
sidebar_position: 4
title: CLI
---

# CLI Reference

The `lua-spa` command-line tool.

```
lua-spa <command> [options]
```

## Commands

### `lua-spa create <name>`

Scaffold a new project by copying the built-in `lua_template` into a new directory.

```bash
lua-spa create my_app
```

| Argument | Description |
|---|---|
| `name` | Project name (letters, numbers, underscore — no spaces) |

**Optional path:**

```bash
lua-spa create my_app ./apps
```

| Argument | Default | Description |
|---|---|---|
| `path` | `.` | Destination directory where the project folder is created |

**Errors:**
- `ValueError` if the name contains invalid characters
- `FileExistsError` if the directory already exists

---

### `lua-spa serve`

Start the development server.

```bash
lua-spa serve
lua-spa serve --reload
```

| Option | Description |
|---|---|
| `--reload` | Watch `.lspa`, `.py`, `.css`, `.js` for changes and live-reload the browser |

Prints the server URL on startup:

```
Serving lua-spa at http://127.0.0.1:8000

With `--reload`, the watcher path is shown relative to the current working directory:

```text
Live reload activated. Watching src for file changes...
```

---

### `lua-spa new component <name> [path]`

Create a new component by copying `ComponentTemplate`, renaming files/content,
and writing it into `lua_template/components/<name>/`.

```bash
lua-spa new component UserCard
lua-spa new component UserCard ./apps/my_project
```

| Argument | Default | Description |
|---|---|---|
| `name` | — | Component name (Python identifier, e.g. `UserCard`) |
| `path` | `.` | Project root where `lua_template` exists |

CLI output includes the exact created locations:

```text
Component created at: <...>/components/UserCard/UserCard.lspa
Style created at: <...>/components/UserCard/UserCard.css
```
```

With `--reload`, the watcher path is shown relative to the current working directory:

```text
Live reload activated. Watching src for file changes...
```

---

### `lua-spa new component <name> [path]`

Create a new component by copying `ComponentTemplate`, renaming files/content,
and writing it into `lua_template/components/<name>/`.

```bash
lua-spa new component UserCard
lua-spa new component UserCard ./apps/my_project
```

| Argument | Default | Description |
|---|---|---|
| `name` | — | Component name (Python identifier, e.g. `UserCard`) |
| `path` | `.` | Project root where `lua_template` exists |

CLI output includes the exact created locations:

```text
Component created at: <...>/components/UserCard/UserCard.lspa
Style created at: <...>/components/UserCard/UserCard.css
```

## Invoke via Python module

```bash
python -m lua_spa serve --reload
python -m lua_spa create my_app
python -m lua_spa new component UserCard
```

## Serve flow

```mermaid
flowchart TD
    A[lua-spa serve] --> B[create_default_framework]
    B --> C[resolve_template_directory]
    C --> D["load spa.config.json"]
    D --> E[SpaFramework.__init__]
    E --> F[ComponentLoader.load_entry]
    F --> G[SpaServer.serve]
    G --> H[ThreadingHTTPServer listening]
    H --> I[GET /__reload__ stream when --reload]
    H --> J[POST /__lua_spa_action for server_call]
```
