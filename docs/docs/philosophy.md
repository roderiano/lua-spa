---
sidebar_position: 3
title: Philosophy
---

# Philosophy

## Why lua-spa exists

Modern frontend development has drifted toward enormous complexity: JavaScript bundlers, transpilers, virtual DOMs, state management libraries, and megabyte-sized bundles — all to display a web page.

lua-spa asks: **what if Python handled it all?**

## Core beliefs

### Python is a great frontend language

Python's readability and expressiveness make it ideal for UI logic. `setup(self, props)` unifies server data (`data`) and reactive behavior (`state/actions/lifecycle`) in one contract. No JSX, no TypeScript generics, no `useEffect` dependency arrays.

### SSR should be the default, not the exception

Server-rendered HTML is fast, SEO-friendly, and accessible. JavaScript should enhance an already-functional page, not be required to show any content at all.

### No build step is a feature

Every extra tool in the chain is a point of failure, a configuration burden, and an onboarding obstacle. lua-spa ships the runtime inside the package. `pip install` is the entire setup.

### Constraints enable clarity

By restricting client logic to Python-declared specs, lua-spa can:
- Generate optimized JavaScript automatically
- Validate component contracts at load time
- Make components fully readable without executing them

## What lua-spa is NOT

- A full React/Vue replacement for complex client applications
- A server framework (it's a SPA layer — pair it with FastAPI, Flask, etc.)
- A UI component library (it's a rendering engine)
- Production-ready for high-traffic applications without an external WSGI server

## The name

**lua** (Portuguese for *moon*) — lightweight, reflected light from a larger body.  
**spa** — Single Page Application.

A minimal SPA framework that reflects Python's simplicity.
