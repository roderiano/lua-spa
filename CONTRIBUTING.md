<div align="center">
  <img src="src/lua_template/static/logo.png" alt="lua-spa logo" width="120" height="120" />
  <h1><strong>LUA-SPA CONTRIBUTING</strong></h1>
</div>
<div align="center">
  First off, thank you for considering contributing to lua-spa! It's people like you that make lua-spa such a great tool.
</div>



## Branching Strategy

We use a structured branching model:

-   `staging` → Main development branch (feature aggregation)
-   `release` → Stable branch used to generate production packages

### Rules

-   All new features must branch from `staging`
-   All pull requests must target `staging`
-   `staging` accumulates code for upcoming releases
-   `release` is updated only when preparing a new version
-   Every branch must be linked to an issue number

### Branch Naming

Create branches with the issue number prefix:

    <issue-number>-<type>-<short-description>

Examples:
-   13-bug-missing-lua_template-scaffold-directory
-   42-feature-router-params
-   77-docs-update-contributing-guide

Tip: create the branch directly from the GitHub issue page when possible.



## Contribution Rules

To ensure quality and traceability:

-   Every contribution **must be linked to a GitHub Issue**
-   If no issue exists, create one before starting
-   Reference the issue in your PR (e.g., `Closes #123`)



## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues.

When creating a bug report, include:

-   Clear and descriptive title
-   Steps to reproduce
-   Expected vs actual behavior
-   Screenshots if possible



### Suggesting Enhancements

Enhancements are tracked as GitHub issues.

Include:

-   Clear title
-   Description
-   Current vs expected behavior



### Pull Requests

1.  Fork the repository
2.  Create your branch from `staging`
3.  Use an issue-linked branch name (for example: `123-fix-cli-template-discovery`)
4.  Add tests if needed
5.  Ensure tests pass
6.  Ensure coverage is at least **90%**
7.  Run linting and type checks
8.  Open PR targeting `staging`



## Development Setup

``` bash
poetry install
```

Create a new branch:

``` bash
git checkout staging
git checkout -b <issue-number>-<type>-<short-description>
```



## Development Workflow

Run app:

``` bash
poetry run lua-spa serve --reload
```

Run tests:

``` bash
poetry run pytest
```

Run coverage:

``` bash
poetry run pytest --cov=src/lua_spa --cov-report=term
```

Lint & typing:

``` bash
poetry run ruff check src
poetry run mypy src
```



## Commit Guidelines

We follow Conventional Commits:

    type(scope): description

Examples:

-   feat(component): add new hook
-   fix(runtime): resolve hydration bug
-   docs(readme): update usage



## Before Submitting a PR

Make sure:

-   Linked to an issue
-   Tests passing
-   Coverage ≥ 90%
-   Lint and type checks passing
-   PR targets `staging`



## Pre-commit

``` bash
poetry run pre-commit install
poetry run pre-commit run --all-files
```



## Release Process

-   Merge `staging` → `release`
-   Generate package
-   Tag version



Thanks for contributing 🚀
