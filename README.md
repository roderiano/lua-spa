# lua-spa

Backend-first SPA framework prototype in Python.

This project now includes:

- View file served by the backend
- `.lspa` components (HTML + Python) with component import support
- Client hydration at component level
- DOM diff renderer inspired by React's virtual DOM flow
- `useState` hook-style state management
- Base app definitions isolated in `view/spa.config.json`

## Requirements

- Python 3.11+
- Poetry installed

## How to use

1. Install dependencies:

   ```bash
   poetry install
   ```

2. Run the application:

   ```bash
  poetry run lua-spa
   ```

3. Open the browser:

  ```text
  http://127.0.0.1:8000
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
  view/
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

- `context(props)` for server-side values used by template interpolation (`py.*`)
- `client()` for declarative client state/actions (hydration + `useState` behavior)

```html
@import Counter from "./Counter.lspa"

<python>
def context(props):
    return {
        "title": props.get("title", "Lua SPA Framework"),
    }


def client():
  return {
    "state": {
      "count": {
        "from_prop": "start",
        "default": 0,
        "cast": "int",
      }
    },
    "actions": {
      "increment": {
        "op": "add",
        "state": "count",
        "value": 1,
      },
    },
  }
</python>

<template>
  <section>
    <h1>{{ py.title }}</h1>
    <Counter start="1" />
  </section>
</template>
```

Use `on:event="actionName"` in templates to bind events to actions declared in `client()`.

## View base definition

All base app definitions are centralized in `view/spa.config.json`:

- Entry component (`entry_component`)
- Mount id (`mount_id`)
- Initial props (`initial_props`)
- Server host/port (`server`)

This keeps `lua_spa` isolated and generic while the view directory defines the app behavior.

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
