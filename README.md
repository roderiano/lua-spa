
<div align="center">
  <img src="src/lua_template/static/logo.png" alt="lua-spa logo" width="120" height="120" />
  <h1><strong>LUA-SPA</strong></h1>
</div>

Backend-first SPA framework in Python.

This project includes:

-   LuaTemplate file served by the backend
-   `.lspa` components (HTML + Python) with component import support
-   Client hydration at component level
-   DOM diff renderer inspired by React's virtual DOM flow
-   `useState` hook-style state management
-   Base app definitions isolated in `lua_template/spa.config.json`

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
lua-spa create my_project
lua-spa create my_project ./apps
```



### Run the application

``` bash
poetry run lua-spa serve
```

Enable hot reload:

``` bash
poetry run lua-spa serve --reload
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
lua-spa/
  pyproject.toml
  src/
    lua_spa/
      app.py
      framework.py
      main.py
  lua_template/
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
poetry run pytest --cov=src/lua_spa --cov-report=term
```



## Component Format

Components are `.lspa` files composed of:

-   optional imports
-   `<python>` block (executed on backend)
-   `<template>` block (HTML)
