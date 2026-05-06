"""Router utilities for composing SPA component trees from route configs.

Implements a React Router-like config with nested routes, index routes, params,
and wildcard fallbacks. Produces cascaded HTML component tags suitable for
server-side rendering and client-side hydration.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class RouteComponent:
    """Component declaration used by the router."""

    name: str
    props: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RouteMatch:
    """Resolved route target for a given path."""

    path: str
    components: list[RouteComponent]
    params: dict[str, str]


@dataclass(frozen=True)
class RouteNode:
    """Route definition node."""

    path: str | None = None
    component: str | None = None
    props: dict[str, Any] = field(default_factory=dict)
    children: list["RouteNode"] = field(default_factory=list)
    index: bool = False
    guard: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


class Router:
    """Router that resolves paths to cascaded component tags."""

    def __init__(self, routes: Iterable[RouteNode]) -> None:
        self._routes = list(routes)

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> "Router":
        routes_cfg = config.get("routes", [])
        return cls(_normalize_routes(routes_cfg))

    def resolve(self, path: str) -> RouteMatch:
        normalized = _normalize_path(path)
        segments = _split_path(normalized)
        match = _match_routes(self._routes, segments, {})
        if match is None:
            raise KeyError(f"Route not found: {normalized}")
        components, params = match
        return RouteMatch(path=normalized, components=components, params=params)

    def render(self, match: RouteMatch) -> str:
        """Render a matched route into cascaded component tags."""
        return _render_component_stack(match.components, match.params)


def _normalize_routes(routes_cfg: Any) -> list[RouteNode]:
    if routes_cfg is None:
        return []
    if isinstance(routes_cfg, Mapping):
        routes_cfg = [routes_cfg]
    if not isinstance(routes_cfg, (list, tuple)):
        raise ValueError("router.routes must be a list of route objects")
    result: list[RouteNode] = []
    for entry in routes_cfg:
        if not isinstance(entry, Mapping):
            raise ValueError("route entry must be a mapping")
        node = RouteNode(
            path=entry.get("path"),
            component=entry.get("component"),
            props=dict(entry.get("props", {}) or {}),
            index=bool(entry.get("index", False)),
            guard=entry.get("guard"),
            meta=dict(entry.get("meta", {}) or {}),
            children=_normalize_routes(entry.get("children", [])),
        )
        result.append(node)
    return result


def _match_routes(
    routes: list[RouteNode],
    segments: list[str],
    params: dict[str, str],
) -> tuple[list[RouteComponent], dict[str, str]] | None:
    for route in routes:
        if route.index:
            if len(segments) == 0:
                components = _components_for_route(route, params)
                return components, dict(params)
            continue

        match = _match_path(route.path, segments)
        if match is None:
            continue
        consumed, new_params = match
        remaining = segments[consumed:]
        merged_params = {**params, **new_params}

        components = _components_for_route(route, merged_params)

        if route.children:
            child_match = _match_routes(route.children, remaining, merged_params)
            if child_match is not None:
                child_components, child_params = child_match
                return components + child_components, child_params

        if len(remaining) == 0 or route.path in {"*", "/*"}:
            return components, merged_params
    return None


def _components_for_route(route: RouteNode, params: dict[str, str]) -> list[RouteComponent]:
    if not route.component:
        return []
    merged_props = dict(route.props or {})
    merged_props.setdefault("routeParams", params)
    if route.meta:
        merged_props.setdefault("routeMeta", route.meta)
    return [RouteComponent(name=str(route.component), props=merged_props)]


def _match_path(path: str | None, segments: list[str]) -> tuple[int, dict[str, str]] | None:
    if path is None or path == "":
        return 0, {}
    if path in {"*", "/*"}:
        return len(segments), {}
    normalized = path
    if normalized.startswith("/"):
        normalized = normalized[1:]
    route_segments = [seg for seg in normalized.split("/") if seg]
    if len(route_segments) > len(segments):
        return None
    params: dict[str, str] = {}
    for index, route_seg in enumerate(route_segments):
        current = segments[index]
        if route_seg.startswith(":"):
            params[route_seg[1:]] = current
            continue
        if route_seg != current:
            return None
    return len(route_segments), params


def _render_component_stack(components: list[RouteComponent], params: dict[str, str]) -> str:
    inner = ""
    for component in reversed(components):
        props = dict(component.props)
        props.setdefault("routeParams", params)
        inner = _render_component_tag(component.name, props, inner)
    return inner


def _render_component_tag(name: str, props: Mapping[str, Any], inner_html: str) -> str:
    payload = "__json__:" + json.dumps(dict(props), ensure_ascii=True)
    attrs = f' __props="{_escape_attr(payload)}"'
    if inner_html:
        return f"<{name}{attrs}>\n{inner_html}\n</{name}>"
    return f"<{name}{attrs} />"


def _split_path(path: str) -> list[str]:
    normalized = _normalize_path(path)
    if normalized == "/":
        return []
    return [segment for segment in normalized.strip("/").split("/") if segment]


def _normalize_path(path: str) -> str:
    if not path:
        return "/"
    if not path.startswith("/"):
        path = "/" + path
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return path


def _escape_attr(value: Any) -> str:
    text = str(value)
    return (
        text.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
    )


def _encode_attr_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return "__json__:" + json.dumps(value, ensure_ascii=True)
    return str(value)
