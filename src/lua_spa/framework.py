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
_PYTHON_PATTERN = re.compile(r"<python>(.*?)</python>", re.IGNORECASE | re.DOTALL)
_ATTR_PATTERN = re.compile(
    r"([:@A-Za-z_][A-Za-z0-9_:\-]*)\s*=\s*(?:\"([^\"]*)\"|'([^']*)')"
)
_EXPR_PATTERN = re.compile(r"{{\s*(.*?)\s*}}")


@dataclass(frozen=True)
class ViewConfig:
    """Configuration loaded from the view directory."""

    entry_component: str
    mount_id: str
    initial_props: Mapping[str, Any]
    host: str
    port: int


@dataclass(frozen=True)
class ComponentDefinition:
    """Represents a .lspa component source file."""

    name: str
    template: str
    client_script: str
    python_block: str
    imports: Mapping[str, str]


class ComponentLoader:
    """Loads components and their import graph from .lspa files."""

    def __init__(self, components_dir: Path) -> None:
        self._components_dir = components_dir
        self._loaded: dict[str, ComponentDefinition] = {}

    @property
    def components(self) -> Mapping[str, ComponentDefinition]:
        return self._loaded

    def load_entry(self, entry_component: str) -> Mapping[str, ComponentDefinition]:
        entry_file = self._components_dir / f"{entry_component}.lspa"
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

        if "<script" in body.lower():
            raise ValueError(
                f"Component '{component_name}' uses <script>; use a <python> block with client() instead"
            )

        template = self._extract_template(body)
        python_block = self._extract_python(body)
        client_script = _build_client_script(python_block)

        self._loaded[component_name] = ComponentDefinition(
            name=component_name,
            template=template,
            client_script=client_script,
            python_block=python_block,
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

    def _extract_python(self, body: str) -> str:
        match = _PYTHON_PATTERN.search(body)
        if match is None:
            return ""
        return match.group(1).strip()


class SpaFramework:
    """Backend framework that builds a SPA HTML view and serves it."""

    @classmethod
    def from_view_directory(cls, view_dir: Path) -> SpaFramework:
        """Create a framework instance using only definitions under view/."""
        config = _load_view_config(view_dir / "spa.config.json")
        return cls(
            view_file=view_dir / "index.lspa",
            components_dir=view_dir / "components",
            entry_component=config.entry_component,
            mount_id=config.mount_id,
            default_props=config.initial_props,
            host=config.host,
            port=config.port,
        )

    def __init__(
        self,
        view_file: Path,
        components_dir: Path,
        entry_component: str = "App",
        mount_id: str = "app",
        default_props: Mapping[str, Any] | None = None,
        host: str = "127.0.0.1",
        port: int = 8000,
    ) -> None:
        self._view_file = view_file
        self._components_dir = components_dir
        self.entry_component = entry_component
        self.mount_id = mount_id
        self._default_props = dict(default_props or {})
        self._host = host
        self._port = port

        if not self._view_file.exists():
            raise FileNotFoundError(f"View file not found: {self._view_file}")

        loader = ComponentLoader(self._components_dir)
        loaded = loader.load_entry(entry_component)
        self._components: dict[str, ComponentDefinition] = dict(loaded)

    @property
    def component_names(self) -> tuple[str, ...]:
        return tuple(self._components.keys())

    @property
    def server_address(self) -> tuple[str, int]:
        return (self._host, self._port)

    def build_view(self, props: Mapping[str, Any] | None = None) -> str:
        page_shell = self._view_file.read_text(encoding="utf-8")
        initial_props = dict(self._default_props)
        initial_props.update(dict(props or {}))

        spa_outlet = self._render_component(self.entry_component, initial_props)
        bootstrap = self._build_bootstrap_block(initial_props)

        page = page_shell.replace("{{ SPA_MOUNT_ID }}", html.escape(self.mount_id, quote=True))
        page = page.replace("{{ SPA_OUTLET }}", spa_outlet)
        page = page.replace("{{ SPA_BOOTSTRAP }}", bootstrap)
        return page

    def serve(self, host: str | None = None, port: int | None = None) -> None:
        framework = self
        resolved_host = host if host is not None else self._host
        resolved_port = port if port is not None else self._port

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                if self.path not in {"/", "/index.html"}:
                    self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
                    return

                body = framework.build_view()
                payload = body.encode("utf-8")

                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format: str, *args: Any) -> None:
                return

        server = ThreadingHTTPServer((resolved_host, resolved_port), Handler)
        with server:
            server.serve_forever()

    def _build_bootstrap_block(self, props: Mapping[str, Any]) -> str:
        registry = {
            name: {
                "template": component.template,
                "script": component.client_script,
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
        return raw_json.replace("</", "<\\/")

    def _render_component(self, name: str, props: Mapping[str, Any]) -> str:
        if name not in self._components:
            raise ValueError(f"Unknown component: {name}")

        component = self._components[name]
        python_context = _build_python_context(component.python_block, props)
        context: dict[str, Any] = {
            "props": dict(props),
            "state": {},
            "py": python_context,
        }

        html_fragment = self._interpolate(component.template, context)
        expanded = self._expand_child_components(html_fragment, context)
        return expanded

    def _expand_child_components(self, template: str, context: Mapping[str, Any]) -> str:
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
            "py": _to_namespace(context.get("py", {})),
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


def _load_view_config(config_file: Path) -> ViewConfig:
    if not config_file.exists():
        raise FileNotFoundError(f"View config file not found: {config_file}")

    raw = config_file.read_text(encoding="utf-8")
    data = json.loads(raw)

    entry_component = str(data.get("entry_component", "App"))
    mount_id = str(data.get("mount_id", "app"))

    initial_props = data.get("initial_props", {})
    if not isinstance(initial_props, dict):
        raise ValueError("view config field 'initial_props' must be an object")

    server = data.get("server", {})
    if server is None:
        server = {}
    if not isinstance(server, dict):
        raise ValueError("view config field 'server' must be an object")

    host = str(server.get("host", "127.0.0.1"))
    raw_port = server.get("port", 8000)
    try:
        port = int(raw_port)
    except (TypeError, ValueError) as error:
        raise ValueError("view config field 'server.port' must be an integer") from error

    return ViewConfig(
        entry_component=entry_component,
        mount_id=mount_id,
        initial_props=initial_props,
        host=host,
        port=port,
    )


def _build_python_context(python_block: str, props: Mapping[str, Any]) -> dict[str, Any]:
    local_scope = _load_python_scope(python_block)

    context_factory = local_scope.get("context")
    if context_factory is None:
        return {}
    if not callable(context_factory):
        raise ValueError("Component python block must define a callable context(props)")

    result = context_factory(dict(props))
    if result is None:
        return {}
    if not isinstance(result, Mapping):
        raise ValueError("context(props) must return a mapping")

    return dict(result)


def _load_python_scope(python_block: str) -> dict[str, Any]:
    if python_block.strip() == "":
        return {}

    allowed_builtins: dict[str, Any] = {
        "bool": bool,
        "dict": dict,
        "float": float,
        "int": int,
        "len": len,
        "list": list,
        "max": max,
        "min": min,
        "str": str,
        "sum": sum,
    }
    local_scope: dict[str, Any] = {}
    exec(python_block, {"__builtins__": allowed_builtins}, local_scope)  # noqa: S102
    return local_scope


def _build_client_script(python_block: str) -> str:
    local_scope = _load_python_scope(python_block)
    client_factory = local_scope.get("client")
    if client_factory is None:
        return ""
    if not callable(client_factory):
        raise ValueError("Component python block field 'client' must be callable")

    raw_spec = client_factory()
    if raw_spec is None:
        return ""
    if not isinstance(raw_spec, Mapping):
        raise ValueError("client() must return a mapping")

    state_spec = raw_spec.get("state", {})
    actions_spec = raw_spec.get("actions", {})

    if not isinstance(state_spec, Mapping):
        raise ValueError("client().state must be a mapping")
    if not isinstance(actions_spec, Mapping):
        raise ValueError("client().actions must be a mapping")

    state_fields = list(state_spec.items())
    lines: list[str] = ["function setup({ useState, props }) {"]
    setter_by_state: dict[str, str] = {}
    value_by_state: dict[str, str] = {}

    for index, (state_name_raw, state_cfg) in enumerate(state_fields):
        state_name = str(state_name_raw)
        value_var = f"__state_{index}"
        setter_var = f"__set_state_{index}"
        initial_expr = _js_initial_state_expression(state_cfg)
        lines.append(f"  const [{value_var}, {setter_var}] = useState({initial_expr});")
        setter_by_state[state_name] = setter_var
        value_by_state[state_name] = value_var

    lines.append("  return {")

    state_pairs = [f"{key}: {value_by_state[key]}" for key in value_by_state]
    lines.append("    state: {" + ", ".join(state_pairs) + "},")
    lines.append("    actions: {")

    for action_name_raw, action_cfg in actions_spec.items():
        action_name = str(action_name_raw)
        operation = _normalize_action_operation(action_cfg)
        action_body = _js_action_statement(operation, setter_by_state)
        lines.append(f"      {action_name}: function () {{")
        lines.append(f"        {action_body}")
        lines.append("      },")

    lines.append("    },")
    lines.append("  };")
    lines.append("}")

    return "\n".join(lines)


def _js_initial_state_expression(config: Any) -> str:
    if isinstance(config, Mapping):
        from_prop = config.get("from_prop")
        default_value = config.get("default")
        cast_kind = str(config.get("cast", "raw"))
        if from_prop is None:
            return _js_literal(default_value)

        prop_expr = f"props[{_js_literal(str(from_prop))}]"
        fallback = _js_literal(default_value)
        base_expr = f"(({prop_expr}) !== undefined && ({prop_expr}) !== null ? ({prop_expr}) : {fallback})"

        if cast_kind == "int":
            return f"Number({base_expr})"
        if cast_kind == "float":
            return f"Number({base_expr})"
        if cast_kind == "str":
            return f"String({base_expr})"
        if cast_kind == "bool":
            return f"Boolean({base_expr})"
        return base_expr

    return _js_literal(config)


def _normalize_action_operation(action_cfg: Any) -> dict[str, Any]:
    if not isinstance(action_cfg, Mapping):
        raise ValueError("Each action config must be a mapping")

    op_kind = str(action_cfg.get("op", "set"))
    state_name = action_cfg.get("state")
    if state_name is None:
        raise ValueError("Action config must include 'state'")

    operation: dict[str, Any] = {
        "op": op_kind,
        "state": str(state_name),
        "value": action_cfg.get("value", 0),
    }
    return operation


def _js_action_statement(operation: Mapping[str, Any], setter_by_state: Mapping[str, str]) -> str:
    state_name = str(operation["state"])
    if state_name not in setter_by_state:
        raise ValueError(f"Action references unknown state field: {state_name}")

    setter = setter_by_state[state_name]
    op_kind = str(operation.get("op", "set"))
    value_literal = _js_literal(operation.get("value"))

    if op_kind == "add":
        return f"{setter}(function (value) {{ return value + {value_literal}; }});"
    if op_kind == "sub":
        return f"{setter}(function (value) {{ return value - {value_literal}; }});"
    if op_kind == "toggle":
        return f"{setter}(function (value) {{ return !value; }});"
    return f"{setter}(function () {{ return {value_literal}; }});"


def _js_literal(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True)
