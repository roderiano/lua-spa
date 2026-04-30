# Lua SPA Framework API Documentation

## Python Modules

### app.py
Helpers for creating a SPA framework instance.
- `create_default_framework(base_dir: Path | None = None) -> SpaFramework`: Build framework using only settings defined under lua_template/.

### framework.py
Core backend framework for rendering and serving a SPA. Main entry point for the framework API.
- `SpaFramework`: Backend framework that builds a SPA HTML view and serves it.
  - `from_lua_template_directory(cls, lua_template_dir: Path) -> SpaFramework`: Create a framework instance using only definitions under lua_template/.
  - `__init__(...)`: Initialize a SPA framework instance.
  - `component_names`: Names of all loaded components.
  - `server_address`: (host, port) tuple for the server.
  - `build_view(props: Mapping[str, Any] | None = None) -> str`: Build the complete HTML page with embedded SPA data and runtime.
  - `serve(host: str | None = None, port: int | None = None) -> None`: Start the HTTP server.

### loader.py
Component loader: reads .lspa files and builds the dependency graph.
- `ComponentLoader`: Loads components and their import graph from .lspa files.
  - `__init__(components_dir: Path)`: Initialize a loader for a component directory.
  - `components`: Loaded components registry.
  - `load_entry(entry_component: str)`: Load a component and all its dependencies.

### codegen.py
Client-side code generation: converts Python specs into JavaScript setup() function.
- `build_client_script(python_block: str) -> str`: Generate the client-side setup() function from a component's Python block.

### runtime_assets.py
Client-side runtime used by the Lua SPA framework. (JavaScript)
- `SPA_RUNTIME_JS`: JavaScript runtime string.
  - Defines all client-side logic for mounting, rendering, updating, and managing SPA components.
  - Key functions: `readJsonScript`, `firstRenderableChild`, `evaluateExpression`, `interpolate`, `parseTemplate`, `toVNodes`, `nodeToVNode`, `createApp`, `mount`, `mountComponent`, `hydrate`, `patch`, `patchElement`, `patchChildren`, `unmount`, `patchProps`, `setElementProp`, `patchElementEvents`, `bootstrap`.

## JavaScript API (runtime)

- `readJsonScript(id)`: Reads and parses JSON from a script tag by id.
- `firstRenderableChild(container)`: Finds the first renderable child node.
- `evaluateRawExpression(expression, context)`: Evaluates a JS expression in a context.
- `evaluateExpression(expression, context)`: Evaluates and stringifies a JS expression.
- `interpolate(template, context)`: Replaces {{ ... }} in template with evaluated expressions.
- `parseTemplate(template, context, registry)`: Parses template into virtual nodes.
- `toVNodes(parent, context, registry)`: Converts DOM nodes to virtual nodes.
- `nodeToVNode(node, context, registry)`: Converts a DOM node to a virtual node.
- `createApp(config, registry)`: Creates the SPA app instance.
- `mount(vnode, container, anchor, app, currentComponent)`: Mounts a vnode.
- `mountComponent(vnode, container, anchor, app, parentComponent, hydrationNode)`: Mounts a component vnode.
- `hydrate(vnode, existingNode, container, app, currentComponent)`: Hydrates server-rendered nodes.
- `patch(previous, next, container, anchor, app, currentComponent)`: Patches vnodes.
- `patchElement(previous, next, app, currentComponent)`: Patches element vnodes.
- `patchChildren(previous, next, container, app, currentComponent)`: Patches children vnodes.
- `unmount(vnode, container)`: Unmounts a vnode.
- `patchProps(el, previous, next)`: Patches element properties.
- `setElementProp(el, key, value)`: Sets an element property.
- `patchElementEvents(el, previous, next, currentComponent)`: Patches element events.
- `bootstrap()`: Boots the SPA runtime.

---

> Para detalhes de cada função, consulte os docstrings nos arquivos fonte.
