
<div align="center">
  <img src="src/lua_template/static/logo.png" alt="lua-spa logo" width="120" height="120" />
  <h1><strong>LUA-SPA</strong></h1>
</div>

Backend-first SPA framework in Python.

This project now includes:

- LuaTemplate file served by the backend
- `.lspa` components (HTML + Python) with component import support
- Client hydration at component level
- DOM diff renderer inspired by React's virtual DOM flow
- `useState` hook-style state management
- Base app definitions isolated in `lua_template/spa.config.json`

## Requirements

- Python 3.11+
- Poetry installed

## How to use

1. Install locally (development):

   ```bash
   poetry install
   ```

2. Install CLI globally or in a venv:

  ```bash
  pip install .
  ```

  This exposes the `lua-spa` command in the active environment.

3. Create a new project from the built-in template:

  ```bash
  lua-spa create my_project
  lua-spa create my_project ./apps
  ```

  Rules for `my_project`:
  - only letters, numbers, and underscore
  - no spaces or special characters
  - destination path is optional (default is `.`)

  The command copies `lua_template` into a new folder named after your project.

4. Run the application:

   ```bash
  poetry run lua-spa serve
   ```

  Tip: `poetry run lua-spa` shows CLI help.

5. Open the browser:

  ```text
  http://127.0.0.1:8000
  ```

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- **English**: http://localhost:3000
- **Português**: http://localhost:3000/pt-BR

To start the documentation locally:

```bash
cd docs
npm run start
```

## Structure

```text
lua-spa/
  pyproject.toml
  README.md
  .gitignore
  src/
    lua_spa/
      __init__.py
      __main__.py
      app.py
      framework.py
      main.py
      runtime_assets.py
  lua_template/
    index.lspa
    spa.config.json
    components/
      App.lspa
      Counter.lspa
  tests/
    test_app.py
```

## Tests

```bash
poetry run pytest
```

## Component format

Components are `.lspa` files with optional imports and a `<python>` block.

Inside `<python>`, use:

- `Component.context(props)` for server-side values used by template interpolation (`py.*`)
- `Component.client()` returning an object with attributes:
  - props as public variables on the client class (`start = 0`, `label = "Counter"`)
  - `State` as a list of state classes (each class defines `name`, `from_prop`, `default`, `cast`)
  - `Methods` as function names (Python methods returning operation configs)
  - lifecycle as functions: `on_mount()`, `on_update()`, `on_unmount()`

The Python code in `<python>` is executed by the backend during render/compile.

```html
@import Counter from "./Counter.lspa"

<python>
class CounterClient(ClientMethods):
  title = "Contador"
  limit = 5
  start = 0

  class CountState:
    name = "count"
    from_prop = "start"
    default = 0
    cast = "int"

  State = [CountState]

  Methods = ["increment", "reset"]

  def increment(self):
    return self.add("count", 1)

  def reset(self):
    return self.set("count", 0)

  def created(self):
    return []

  def mounted(self):
    return []

  def updated(self):
    return []

  def unmounted(self):
    return []


class Component:
    def context(self, props):
        return {
            "title": props.get("title", "Lua SPA Framework"),
        }

    def client(self):
        return CounterClient()
</python>

<template>
  <div>
    <h2>{{ title }}</h2>
    <p>Contador: {{ count }}</p>

    <button @click="increment">+1</button>
    <button @click="reset">Reset</button>

    <p l-if="count > limit">Limite atingido!</p>
  </div>
</template>
```

Use `on:event="actionName"` in templates to bind events to actions declared in client methods.

## LuaTemplate base definition

All base app definitions are centralized in `lua_template/spa.config.json`:

- Entry component (`entry_component`)
- Mount id (`mount_id`)
- Initial props (`initial_props`)
- Server host/port (`server`)

This keeps `lua_spa` isolated and generic while the lua_template directory defines the app behavior.

## Linting and typing

```bash
poetry run ruff check .
poetry run mypy src
```

## Pre-commit

This project uses pre-commit to keep code quality consistent before each commit.

Configured hooks:

- Ruff: auto-fix issues and sort imports
- Ruff: lint checks
- Black: code formatting and formatting validation
- Flake8: style validation
- MyPy: strict type checking

Install and run hooks:

```bash
poetry run pre-commit install
poetry run pre-commit run --all-files
```

## Contributing

Contributions are welcome.

1. Create a branch for your changes.
2. Install dependencies with Poetry.
3. Install pre-commit hooks.
4. Run checks locally before opening a pull request:

  ```bash
  poetry run pre-commit run --all-files
  poetry run pytest
  ```

5. Open a pull request with a clear description of what changed and why.
