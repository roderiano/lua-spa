"""Core backend framework for rendering and serving a SPA.

This module orchestrates the component loader, renderer, code generator,
and server to provide a complete SPA framework. It's the main entry point
for the framework API.
"""

from __future__ import annotations

import html
import json
import mimetypes
import re
from pathlib import Path
from typing import Any, Mapping

from lua_spa.loader import ComponentLoader
from lua_spa.renderer import (
    build_python_context,
    build_server_state,
    interpolate,
    render_template_with_directives,
)
from lua_spa.scope import execute_setup_server_callable
from lua_spa.router import Router
from lua_spa.runtime_assets import SPA_RUNTIME_JS
from lua_spa.server import SpaServer
from lua_spa.types import ComponentDefinition, load_lua_template_config

_ATTR_PATTERN = re.compile(r"([:@A-Za-z_][A-Za-z0-9_:\-]*)\s*=\s*(?:\"([^\"]*)\"|'([^']*)')")
_STYLE_SRC_PATTERN = re.compile(
    r"<style\s+[^>]*src\s*=\s*(?:\"([^\"]+)\"|'([^']+)')[^>]*>\s*</style>",
    re.IGNORECASE,
)


class SpaFramework:
    """Backend framework that builds a SPA HTML view and serves it.

    Loads .lspa components, renders them server-side, generates client-side
    JavaScript, and provides an HTTP server to deliver the complete SPA to browsers.
    """

    @classmethod
    def from_lua_template_directory(cls, lua_template_dir: Path) -> SpaFramework:
        """Create a framework instance using only definitions under lua_template/.

        Loads spa.config.json from lua_template_dir and creates a framework configured
        with that settings.

        Args:
            lua_template_dir: Path to the lua_template directory containing spa.config.json
                     and a components/ subdirectory.

        Returns:
            A configured SpaFramework instance.

        Raises:
            FileNotFoundError: If spa.config.json or the lua_template file doesn't exist.
        """
        config = load_lua_template_config(lua_template_dir / "spa.config.json")
        return cls(
            view_file=lua_template_dir / "index.lspa",
            components_dir=lua_template_dir / "components",
            static_dir=lua_template_dir / "static",
            mount_id=config.mount_id,
            default_props=config.initial_props,
            host=config.host,
            port=config.port,
            page_title=config.page_title,
            router=config.router,
        )

    def __init__(
        self,
        view_file: Path,
        components_dir: Path,
        static_dir: Path | None = None,
        entry_component: str = "App",
        mount_id: str = "app",
        default_props: Mapping[str, Any] | None = None,
        host: str = "127.0.0.1",
        port: int = 8000,
        page_title: str = "lua-spa",
        router: Mapping[str, Any] | None = None,
    ) -> None:
        """Initialize a SPA framework instance.

        Args:
            view_file: Path to the main index.lspa file.
            components_dir: Path to the components directory.
            entry_component: Name of the root component to render.
            mount_id: DOM ID where the app mounts in the HTML.
            default_props: Default props passed to the entry component.
            host: Host to bind the server to.
            port: Port to bind the server to.

        Raises:
            FileNotFoundError: If view_file doesn't exist.
            ValueError: If components can't be loaded or are malformed.
        """
        self._view_file = view_file
        self._components_dir = components_dir
        self._static_dir = static_dir if static_dir is not None else view_file.parent / "static"
        self.entry_component = entry_component
        self.mount_id = mount_id
        self.page_title = page_title
        self._default_props = dict(default_props or {})
        self._host = host
        self._port = port
        self._router_config = dict(router) if isinstance(router, Mapping) else None

        if not self._view_file.exists():
            raise FileNotFoundError(f"View file not found: {self._view_file}")

        self._components: dict[str, ComponentDefinition] = {}
        self.reload_components()

    @property
    def component_names(self) -> tuple[str, ...]:
        """Get the names of all loaded components."""
        return tuple(self._components.keys())

    @property
    def server_address(self) -> tuple[str, int]:
        """Get the (host, port) tuple for the server."""
        return (self._host, self._port)

    def reload_components(self) -> None:
        """Reload all component definitions from disk.

        This is used by hot reload so file changes in .lspa components are
        reflected without restarting the server process.
        """
        loader = ComponentLoader(self._components_dir)
        loaded = loader.load_entry(self.entry_component)
        self._components = dict(loaded)

    def build_view(self, props: Mapping[str, Any] | None = None) -> str:
        """Build the complete HTML page with embedded SPA data and runtime.

        Renders the entry component with the given props, embeds component
        registry and bootstrap config as JSON, and includes the client-side
        runtime JavaScript.

        Args:
            props: Override or extend the default props.

        Returns:
            Complete HTML page as a string.
        """
        page_shell = self._view_file.read_text(encoding="utf-8")
        page_shell = self._inline_style_src_tags(page_shell, self._view_file.parent)
        initial_props = dict(self._default_props)
        initial_props.update(dict(props or {}))

        if self._router_config is not None:
            spa_outlet = self._render_router_outlet(initial_props)
        else:
            spa_outlet = self._render_component(self.entry_component, initial_props)
        bootstrap = self._build_bootstrap_block(initial_props)

        page = page_shell.replace("{{ SPA_MOUNT_ID }}", html.escape(self.mount_id, quote=True))
        page = page.replace("{{ SPA_PAGE_TITLE }}", html.escape(self.page_title, quote=False))
        page = page.replace("{{ SPA_OUTLET }}", spa_outlet)
        page = page.replace("{{ SPA_BOOTSTRAP }}", bootstrap)
        return page

    def _inline_style_src_tags(self, markup: str, base_dir: Path) -> str:
        """Replace <style src="..."> with inline CSS loaded from disk."""

        def replace(match: re.Match[str]) -> str:
            relative_src = match.group(1) or match.group(2)
            if relative_src is None:
                return match.group(0)
            css_path = (base_dir / relative_src).resolve()
            if not css_path.exists() or not css_path.is_file():
                raise FileNotFoundError(f"Style file not found: {css_path}")
            css_content = css_path.read_text(encoding="utf-8")
            return f"<style>\n{css_content}\n</style>"

        return _STYLE_SRC_PATTERN.sub(replace, markup)

    def get_static_asset(self, request_path: str) -> tuple[bytes, str] | None:
        """Resolve and read a static asset by HTTP path.

        Args:
            request_path: Request path such as "/static/logo.svg" or "/favicon.ico".

        Returns:
            A tuple of (file bytes, MIME type) if found; otherwise None.
        """
        if request_path == "/favicon.ico":
            for candidate_name in ("favicon.ico", "favicon.png", "favicon.svg"):
                candidate = self._static_dir / candidate_name
                if candidate.exists() and candidate.is_file():
                    mime_type, _ = mimetypes.guess_type(str(candidate))
                    return candidate.read_bytes(), (mime_type or "application/octet-stream")
            return None

        if not request_path.startswith("/static/"):
            return None

        relative_path = request_path[len("/static/") :]
        if relative_path == "":
            return None

        candidate = (self._static_dir / relative_path).resolve()
        static_root = self._static_dir.resolve()

        try:
            candidate.relative_to(static_root)
        except ValueError:
            return None

        if not candidate.exists() or not candidate.is_file():
            return None

        mime_type, _ = mimetypes.guess_type(str(candidate))
        return candidate.read_bytes(), (mime_type or "application/octet-stream")

    def serve(self, host: str | None = None, port: int | None = None, reload: bool = False) -> None:
        """Start the HTTP server.

        Blocks indefinitely, serving the SPA on the specified host and port.

        Args:
            host: Override the configured host (default: self._host).
            port: Override the configured port (default: self._port).
        """
        resolved_host = host if host is not None else self._host
        resolved_port = port if port is not None else self._port
        SpaServer.serve(self, resolved_host, resolved_port, reload)

    def _build_bootstrap_block(self, props: Mapping[str, Any]) -> str:
        """Build the bootstrap JSON payloads and runtime script.

        Creates the lua-spa-registry (component definitions) and lua-spa-config
        (entry point and props), then embeds the client-side runtime JavaScript.

        Args:
            props: Component props.

        Returns:
            HTML script tags with embedded JSON and JavaScript.
        """
        registry = {
            name: {
                "template": component.template,
                "script": component.client_script,
                "imports": component.imports,
            }
            for name, component in self._components.items()
        }
        entry_python_context: Mapping[str, Any] = {}
        entry_component = self._components.get(self.entry_component)
        if entry_component is not None:
            entry_python_context = build_python_context(entry_component.python_block, props)

        synced_props = dict(props)
        if isinstance(entry_python_context, Mapping) and len(entry_python_context) > 0:
            synced_props["__context"] = dict(entry_python_context)

        config = {
            "mountId": self.mount_id,
            "entry": self.entry_component,
            "props": synced_props,
            "router": self._router_config,
        }

        registry_payload = self._serialize_json_payload(registry)
        config_payload = self._serialize_json_payload(config)

        return (
            '<script type="application/json" id="lua-spa-registry">'
            + registry_payload
            + "</script>"
            + '<script type="application/json" id="lua-spa-config">'
            + config_payload
            + "</script>"
            + "<script>"
            + SPA_RUNTIME_JS
            + "\nwindow.LuaSpaRuntime.bootstrap();</script>"
        )

    def _serialize_json_payload(self, payload: Mapping[str, Any]) -> str:
        r"""Serialize a dict to JSON, escaping forward slashes to prevent HTML injection.

        Args:
            payload: A dict to serialize.

        Returns:
            JSON string with </ escaped to <\/.
        """
        raw_json = json.dumps(payload, ensure_ascii=True)
        return raw_json.replace("</", "<\\/")

    def _render_component(self, name: str, props: Mapping[str, Any]) -> str:
        """Render a component to HTML with the given props.

        Calls component.context() for server state, evaluates {{ }} expressions,
        applies l-if conditionals, and recursively expands child components.

        Args:
            name: Component name.
            props: Component props.

        Returns:
            Rendered HTML fragment.

        Raises:
            ValueError: If component is unknown.
        """
        if name not in self._components:
            raise ValueError(f"Unknown component: {name}")

        component = self._components[name]
        server_state = build_server_state(component.python_block, props)
        python_context = build_python_context(component.python_block, props)
        context: dict[str, Any] = {
            "props": dict(props),
            "state": server_state,
            "py": python_context,
        }

        html_fragment = interpolate(component.template, context)
        html_fragment = render_template_with_directives(html_fragment, context)
        expanded = self._expand_child_components(html_fragment, context)
        return expanded

    def _render_router_outlet(self, props: Mapping[str, Any]) -> str:
        if self._router_config is None:
            return self._render_component(self.entry_component, props)
        router = Router.from_config(self._router_config)
        initial_path = str(self._router_config.get("initial_path", "/"))
        try:
            match = router.resolve(initial_path)
        except KeyError:
            match = router.resolve("/")
        route_template = router.render(match)
        context: dict[str, Any] = {
            "props": dict(props),
            "state": {},
            "py": {},
        }
        return self._expand_child_components(route_template, context)

    def _expand_child_components(self, template: str, context: Mapping[str, Any]) -> str:
        """Recursively expand custom component tags into their rendered HTML.

        Processes largest component names first to avoid conflicts (e.g., render
        "MyLongComponent" before "My").

        Args:
            template: HTML with component tags.
            context: Rendering context (props, state, py).

        Returns:
            HTML with all component tags expanded.
        """
        rendered = template

        for component_name in sorted(self._components.keys(), key=len, reverse=True):
            escaped_name = re.escape(component_name)
            open_close_pattern = re.compile(
                rf"<{escaped_name}\b([^>]*)>(.*?)</{escaped_name}>",
                flags=re.DOTALL | re.IGNORECASE,
            )
            self_closing_pattern = re.compile(
                rf"<{escaped_name}\b([^>]*)/>",
                flags=re.DOTALL | re.IGNORECASE,
            )

            rendered = open_close_pattern.sub(
                lambda match: self._render_tag_match(
                    component_name, match.group(1), match.group(2), context
                ),
                rendered,
            )
            rendered = self_closing_pattern.sub(
                lambda match: self._render_tag_match(component_name, match.group(1), "", context),
                rendered,
            )

        return rendered

    def execute_server_callable(
        self,
        component_name: str,
        kind: str,
        callable_name: str,
        props: Mapping[str, Any] | None,
        state: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        """Execute a setup action/lifecycle callable and return state/props patches."""
        component = self._components.get(component_name)
        if component is None:
            raise ValueError(f"Unknown component: {component_name}")

        return execute_setup_server_callable(
            component.python_block,
            kind=kind,
            name=callable_name,
            props=props,
            state=state,
        )

    def _render_tag_match(
        self,
        component_name: str,
        attrs_raw: str,
        inner_html: str,
        parent_context: Mapping[str, Any],
    ) -> str:
        """Render a component tag with its attributes and children.

        Args:
            component_name: Name of the component.
            attrs_raw: Raw attribute string (e.g., 'prop="value"').
            inner_html: Content between opening and closing tags.
            parent_context: Parent rendering context.

        Returns:
            Rendered component HTML.
        """
        child_props = self._parse_attributes(attrs_raw, parent_context)
        if inner_html.strip() != "":
            child_props["children"] = inner_html
        return self._render_component(component_name, child_props)

    def _parse_attributes(self, attrs_raw: str, context: Mapping[str, Any]) -> dict[str, Any]:
        """Parse HTML attributes and interpolate their values.

        Args:
            attrs_raw: Raw attribute string.
            context: Rendering context for expression evaluation.

        Returns:
            Dict mapping attribute names to interpolated values.
        """
        parsed: dict[str, Any] = {}
        for match in _ATTR_PATTERN.finditer(attrs_raw):
            name = match.group(1)
            value = match.group(2) if match.group(2) is not None else match.group(3)
            resolved = interpolate(value, context)
            if name == "__props" and isinstance(resolved, str):
                payload = resolved[9:] if resolved.startswith("__json__:") else resolved
                try:
                    parsed_payload = json.loads(payload)
                except json.JSONDecodeError:
                    parsed_payload = {}
                if isinstance(parsed_payload, Mapping):
                    parsed.update(dict(parsed_payload))
                continue
            if isinstance(resolved, str) and resolved.startswith("__json__:"):
                try:
                    parsed[name] = json.loads(resolved[9:])
                except json.JSONDecodeError:
                    parsed[name] = resolved
            else:
                parsed[name] = resolved
        return parsed
