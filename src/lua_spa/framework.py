"""Core backend primitives to render and serve a SPA view."""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping

from lua_spa.runtime_assets import SPA_RUNTIME_JS

_IMPORT_PATTERN = re.compile(r"^\s*@import\s+([A-Za-z_][A-Za-z0-9_]*)\s+from\s+['\"](.+?)['\"]\s*$")
_TEMPLATE_PATTERN = re.compile(r"<template>(.*?)</template>", re.IGNORECASE | re.DOTALL)
_SCRIPT_PATTERN = re.compile(r"<script>(.*?)</script>", re.IGNORECASE | re.DOTALL)
_ATTR_PATTERN = re.compile(
    r"([:@A-Za-z_][A-Za-z0-9_:\-]*)\s*=\s*(?:\"([^\"]*)\"|'([^']*)')"
)
_EXPR_PATTERN = re.compile(r"{{\s*(.*?)\s*}}")


@dataclass(frozen=True)
class ComponentDefinition:
    """Represents a HTML component source file."""

    name: str
    template: str
    script: str
    imports: Mapping[str, str]


class ComponentLoader:
    """Loads components and their import graph from HTML files."""

    def __init__(self, components_dir: Path) -> None:
        self._components_dir = components_dir
        self._loaded: dict[str, ComponentDefinition] = {}

    @property
    def components(self) -> Mapping[str, ComponentDefinition]:
        return self._loaded

    def load_entry(self, entry_component: str) -> Mapping[str, ComponentDefinition]:
        entry_file = self._components_dir / f"{entry_component}.html"
        self._load_component(entry_component, entry_file)
        return self._loaded

    def _load_component(self, component_name: str, file_path: Path) -> None:
        normalized = file_path.resolve()
        if component_name in self._loaded:
            return

        if not normalized.exists():
            raise FileNotFoundError(f"Component file not found: {normalized}")

        source = normalized.read_text(encoding="utf-8")
        imports, body = self._extract_imports(source)
        template = self._extract_template(body)
        script = self._extract_script(body)

        self._loaded[component_name] = ComponentDefinition(
            name=component_name,
            template=template,
            script=script,
            imports={alias: alias for alias in imports},
        )

        for alias, relative_path in imports.items():
            imported_file = (normalized.parent / relative_path).resolve()
            self._load_component(alias, imported_file)

    def _extract_imports(self, source: str) -> tuple[dict[str, str], str]:
        imports: dict[str, str] = {}
        body_lines: list[str] = []

        for line in source.splitlines():
            match = _IMPORT_PATTERN.match(line)
            if match is None:
                body_lines.append(line)
                continue
            imports[match.group(1)] = match.group(2)

        return imports, "\n".join(body_lines)

    def _extract_template(self, body: str) -> str:
        match = _TEMPLATE_PATTERN.search(body)
        if match is None:
            return body.strip()
        return match.group(1).strip()

    def _extract_script(self, body: str) -> str:
        match = _SCRIPT_PATTERN.search(body)
        if match is None:
            return ""
        return match.group(1).strip()


class SpaFramework:
    """Backend framework that builds a SPA HTML view and serves it."""

    def __init__(
        self,
        view_file: Path,
        components_dir: Path,
        entry_component: str = "App",
        mount_id: str = "app",
    ) -> None:
        self._view_file = view_file
        self._components_dir = components_dir
        self.entry_component = entry_component
        self.mount_id = mount_id

        if not self._view_file.exists():
            raise FileNotFoundError(f"View file not found: {self._view_file}")

        loader = ComponentLoader(self._components_dir)
        loaded = loader.load_entry(entry_component)
        self._components: dict[str, ComponentDefinition] = dict(loaded)

    @property
    def component_names(self) -> tuple[str, ...]:
        return tuple(self._components.keys())

    def build_view(self, props: Mapping[str, Any] | None = None) -> str:
        page_shell = self._view_file.read_text(encoding="utf-8")
        initial_props = dict(props or {})

        spa_outlet = self._render_component(self.entry_component, initial_props)
        bootstrap = self._build_bootstrap_block(initial_props)

        page = page_shell.replace("{{ SPA_OUTLET }}", spa_outlet)
        page = page.replace("{{ SPA_BOOTSTRAP }}", bootstrap)
        return page

    def serve(self, host: str = "127.0.0.1", port: int = 8000) -> None:
        framework = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                if self.path not in {"/", "/index.html"}:
                    self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
                    return

                body = framework.build_view(
                    {
                        "title": "Lua SPA Framework",
                        "subtitle": "Hydrated component tree with hook-based state.",
                        "start": 0,
                    }
                )
                payload = body.encode("utf-8")

                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format: str, *args: Any) -> None:
                return

        server = ThreadingHTTPServer((host, port), Handler)
        with server:
            server.serve_forever()

    def _build_bootstrap_block(self, props: Mapping[str, Any]) -> str:
        registry = {
            name: {
                "template": component.template,
                "script": component.script,
                "imports": component.imports,
            }
            for name, component in self._components.items()
        }
        config = {
            "mountId": self.mount_id,
            "entry": self.entry_component,
            "props": dict(props),
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
        raw_json = json.dumps(payload, ensure_ascii=True)
        return html.escape(raw_json).replace("</", "<\\/")

    def _render_component(self, name: str, props: Mapping[str, Any]) -> str:
        if name not in self._components:
            raise ValueError(f"Unknown component: {name}")

        component = self._components[name]
        context: dict[str, Any] = {
            "props": dict(props),
            "state": {},
        }

        html_fragment = self._interpolate(component.template, context)
        expanded = self._expand_child_components(html_fragment, context)
        return expanded

    def _expand_child_components(self, template: str, context: Mapping[str, Any]) -> str:
        rendered = template

        for component_name in sorted(self._components.keys(), key=len, reverse=True):
            open_close_pattern = re.compile(
                rf"<{component_name}\\b([^>]*)>(.*?)</{component_name}>",
                flags=re.DOTALL,
            )
            self_closing_pattern = re.compile(
                rf"<{component_name}\\b([^>]*)/>",
                flags=re.DOTALL,
            )

            rendered = open_close_pattern.sub(
                lambda match: self._render_tag_match(component_name, match.group(1), match.group(2), context),
                rendered,
            )
            rendered = self_closing_pattern.sub(
                lambda match: self._render_tag_match(component_name, match.group(1), "", context),
                rendered,
            )

        return rendered

    def _render_tag_match(
        self,
        component_name: str,
        attrs_raw: str,
        inner_html: str,
        parent_context: Mapping[str, Any],
    ) -> str:
        child_props = self._parse_attributes(attrs_raw, parent_context)
        if inner_html.strip() != "":
            child_props["children"] = inner_html
        return self._render_component(component_name, child_props)

    def _parse_attributes(self, attrs_raw: str, context: Mapping[str, Any]) -> dict[str, Any]:
        parsed: dict[str, Any] = {}
        for match in _ATTR_PATTERN.finditer(attrs_raw):
            name = match.group(1)
            value = match.group(2) if match.group(2) is not None else match.group(3)
            parsed[name] = self._interpolate(value, context)
        return parsed

    def _interpolate(self, template: str, context: Mapping[str, Any]) -> str:
        scoped = {
            "props": _to_namespace(context.get("props", {})),
            "state": _to_namespace(context.get("state", {})),
        }

        def replace_expression(match: re.Match[str]) -> str:
            expression = match.group(1)
            try:
                value = eval(expression, {"__builtins__": {}}, scoped)  # noqa: S307
            except Exception:
                return ""
            if value is None:
                return ""
            return str(value)

        return _EXPR_PATTERN.sub(replace_expression, template)


def _to_namespace(value: Any) -> Any:
    if isinstance(value, Mapping):
        data = {key: _to_namespace(item) for key, item in value.items()}
        return SimpleNamespace(**data)
    if isinstance(value, list):
        return [_to_namespace(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_to_namespace(item) for item in value)
    return value
