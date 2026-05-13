
<div align="center">
  <img src="http://github.com/roderiano/moon-spa/raw/release/src/moon_template/static/logo.png" alt="moon-spa logo" width="120" height="120" />
  <h1><strong>LUA-SPA</strong></h1>
</div>

<p align="center">
  <a href="https://github.com/roderiano/moon-spa/actions?query=branch%staging">
    <img src="https://github.com/roderiano/moon-spa/actions/workflows/quality-and-tests.yaml/badge.svg?branch=staging" />
  </a>
  <a href="https://codecov.io/gh/roderiano/moon-spa">
    <img src="https://codecov.io/gh/roderiano/moon-spa/branch/staging/graph/badge.svg" />
  </a>
  <img src="https://img.shields.io/pypi/dm/moon-spa" />
  <img src="https://img.shields.io/github/license/roderiano/moon-spa" />
  <img src="https://img.shields.io/github/v/release/roderiano/moon-spa" />
  <img src="https://img.shields.io/github/stars/roderiano/moon-spa?style=flat" />
</p>

Backend-first SPA framework in Python.

This project includes:

-   Template file served by the backend
-   `.lspa` components (HTML + Python) with component import support
-   Client hydration at component level
-   DOM diff renderer inspired by React's virtual DOM flow
-   `useState` hook-style state management
-   Setup-only component contract via `Component.setup(self, props)`
-   Server-call bridge for callable actions and lifecycle hooks
-   Base app definitions isolated in `src/moon_template/spa.config.json`

## Requirements

-   Python 3.10+
-   Poetry installed



## How to use

### Install locally (development)

``` bash
poetry install
```


### Create a new project

``` bash
moon-spa create my_project
moon-spa create my_project ./apps
```

### Create a component from template

``` bash
moon-spa new component UserCard
moon-spa new component UserCard ./apps/my_project
```

The CLI copies `ComponentTemplate`, renames files/content, and prints the exact created paths.



### Run the application

``` bash
poetry run moon-spa serve
```

Enable hot reload:

``` bash
poetry run moon-spa serve --reload
```

When reload is enabled, watcher logs use relative paths:

``` text
Live reload activated. Watching src for file changes...
```

Open in browser:

    http://127.0.0.1:8000



## Documentation

Docs are available in the `docs/` directory:

Run locally:

``` bash
cd docs
npx docusaurus start
```



## Project Structure

``` text
moon-spa/
  pyproject.toml
  src/
    moon_spa/
      app.py
      codegen.py
      framework.py
      loader.py
      main.py
      renderer.py
      router.py
      scope.py
      server.py
      runtime_assets.py
    moon_template/
      index.lspa
      spa.config.json
      components/
  tests/
```



## Tests

``` bash
poetry run pytest
```

With coverage:

``` bash
poetry run pytest --cov=src/moon_spa --cov-report=term
```



## Component Format

Components are `.lspa` files composed of:

-   optional imports
-   `<python>` block with a `Component` subclass implementing `setup(self, props)`
-   `<template>` block (HTML)

`setup(self, props)` can return a mapping with `props`, `state`, `data`, `actions`, and `lifecycle`,
or omit return and let the server infer these sections from local variables/functions.
Callable `actions` and `lifecycle` entries are executed through the `POST /__moon_spa_action` bridge.
When actions/lifecycle mutate `data`, those keys are patched back to client props automatically.
