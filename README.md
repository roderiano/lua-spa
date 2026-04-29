# lua-spa

Python project scaffold with Poetry for the `lua-spa` application.

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
      main.py
  tests/
    test_app.py
```

## Tests

```bash
poetry run pytest
```

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
