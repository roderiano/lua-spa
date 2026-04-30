---
sidebar_position: 1
---

# Lua SPA

A lightweight **backend-first SPA framework** written in Python that provides a modern, reactive component system with server-side rendering and client-side hydration.

## Key Features

- **Backend-First Architecture**: Server-side rendering with client-side hydration
- **Component-Based**: Reusable `.lspa` components combining HTML templates with Python logic
- **State Management**: Vue-like `useState` hooks for reactive state
- **DOM Diffing**: Efficient DOM updates using virtual DOM diffing algorithm
- **Hot Reload**: Automatic server restart and browser refresh during development
- **Type Safe**: Full Python typing support with MyPy strict mode
- **Zero Configuration**: Get started with minimal setup

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/lua-spa/lua-spa.git
cd lua-spa

# Install dependencies
poetry install
```

### Run the Application

```bash
# Start the development server
poetry run lua-spa
```

Open your browser to `http://127.0.0.1:8000`

## Project Structure

```
lua-spa/
├── src/lua_spa/              # Framework core
│   ├── framework.py          # Main SpaFramework class
│   ├── loader.py             # Component loader
│   ├── renderer.py           # Template rendering engine
│   ├── codegen.py            # JavaScript code generation
│   ├── scope.py              # Component scope execution
│   ├── types.py              # Type definitions
│   ├── runtime_assets.py     # Client-side runtime
│   └── server.py             # HTTP server
├── lua_template/             # Application definition
│   ├── spa.config.json       # App configuration
│   ├── index.lspa            # Root template
│   └── components/           # Reusable components
│       ├── App.lspa
│       └── Counter.lspa
└── tests/                    # Test suite
```

## What You'll Learn

- [Getting Started](./getting-started.md) - Basic setup and first component
- [Architecture Overview](./architecture.md) - System design and data flow
- [Components](./components/index.md) - Creating `.lspa` components
- [State Management](./components/state.md) - Managing component state
- [Framework API](./api/framework.md) - Core classes and methods
- [Type System](./api/types.md) - Type definitions and interfaces

## Next Steps

👉 **Start with** [Getting Started](./getting-started.md) for a hands-on introduction.
