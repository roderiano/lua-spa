from __future__ import annotations

from lua_spa.router import (
    Router,
    _components_for_route,
    _encode_attr_value,
    _escape_attr,
    _match_path,
    _normalize_path,
    _normalize_routes,
    _split_path,
    RouteNode,
)


def test_router_resolve_and_render_nested_params() -> None:
    # Given: a router configured with a nested route containing a URL parameter
    router = Router.from_config(
        {
            "routes": [
                {
                    "path": "/users/:id",
                    "component": "UserLayout",
                    "children": [{"index": True, "component": "UserHome"}],
                }
            ]
        }
    )

    # When: resolving a concrete URL path
    match = router.resolve("/users/42")
    html = router.render(match)

    # Then: params are extracted and nested components are rendered
    assert match.params["id"] == "42"
    assert "<UserLayout" in html
    assert "<UserHome" in html
    assert "routeParams" in html


def test_router_helpers() -> None:
    # Given: various path and attribute strings

    # When: helper functions process them

    # Then: normalization, splitting, matching, escaping, and encoding produce expected results
    assert _normalize_path("a/b/") == "/a/b"
    assert _split_path("/a/b") == ["a", "b"]
    assert _match_path("/a/:id", ["a", "10"]) == (2, {"id": "10"})
    assert _escape_attr('a"<b>') == "a&quot;&lt;b&gt;"
    encoded = _encode_attr_value({"x": 1})
    assert encoded.startswith("__json__:")


def test_router_not_found() -> None:
    # Given: a router with only a root path
    router = Router.from_config({"routes": [{"path": "/", "component": "Home"}]})

    # When: resolving an unknown path

    # Then: a KeyError is raised
    try:
        router.resolve("/not-found")
    except KeyError:
        return
    raise AssertionError("Expected KeyError")


def test_router_validation_and_path_edge_helpers() -> None:
    # Given: various route configs and path inputs

    # When: normalization and matching helpers process them

    # Then: each edge case produces the expected result or raises
    assert _normalize_routes(None) == []
    assert len(_normalize_routes({"path": "/", "component": "A"})) == 1

    for invalid in ["bad", 123]:
        try:
            _normalize_routes(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError")

    try:
        _normalize_routes([1])
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

    assert _components_for_route(RouteNode(path="/", component=None), {}) == []
    comp = _components_for_route(RouteNode(path="/", component="X", meta={"a": 1}), {})
    assert comp[0].props["routeMeta"]["a"] == 1

    assert _match_path(None, ["a"]) == (0, {})
    assert _match_path("*", ["a", "b"]) == (2, {})
    assert _match_path("/a/b/c", ["a"]) is None
    assert _match_path("/a/b", ["a", "x"]) is None

    assert _normalize_path("") == "/"
    assert _encode_attr_value(1) == "1"
