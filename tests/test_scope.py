from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from lua_spa.scope import (
    _extract_mapping_value,
    canonical_lifecycle_name,
    infer_action_methods,
    invoke_method_callable,
    load_python_scope,
    normalize_action_names,
    normalize_client_spec,
    normalize_lifecycle_methods,
    normalize_props_source,
    normalize_state_source,
    resolve_component_callables,
    resolve_methods_actions,
)
from lua_spa.trace import _TraceState
from lua_spa.types import Component, StateField


def test_scope_resolve_component_callables_with_python_spec() -> None:
    source = """
class Counter(Component):
    def context(self, props):
        return {"title": props.get("title", "default")}

    def client(self):
        class Props:
            title = "default"

        class State:
            count = 0

        class ClientSpec:
            Props = Props
            State = State
            Methods = ["inc"]

        return ClientSpec()

    def inc(self):
        self.state.count += 1
"""
    scope = load_python_scope(source)
    context_fn, client_fn = resolve_component_callables(scope)

    assert callable(context_fn)
    assert callable(client_fn)


def test_scope_normalize_client_spec_class_only() -> None:
    class ClientSpec:
        class Props:
            title = "hello"

        class State:
            count = 0
            qty = StateField(name="qty", from_prop="initialQty", default=1, cast="int")

        Methods = ["inc"]

        def inc(self) -> None:
            self.state.count += 1  # type: ignore[operator]

    props, state, actions, lifecycle = normalize_client_spec(ClientSpec())

    assert props["title"] == "hello"
    assert state["count"] == 0
    assert state["qty"]["from_prop"] == "initialQty"
    assert actions["inc"]["op"] == "add"
    assert lifecycle["onMount"] == []


def test_scope_rejects_declarative_dict_client_specs() -> None:
    with pytest.raises(ValueError, match="declarative dict specs"):
        normalize_client_spec({"props": {"title": "x"}})


@pytest.mark.parametrize(
    "invalid_props",
    [
        {"title": "x"},
        1,
        "bad",
    ],
)
def test_scope_props_source_validation(invalid_props: Any) -> None:
    if isinstance(invalid_props, dict):
        with pytest.raises(ValueError, match="Declarative props dicts"):
            normalize_props_source(invalid_props)
    else:
        with pytest.raises(ValueError):
            normalize_props_source(invalid_props)


@pytest.mark.parametrize(
    "invalid_state",
    [
        {"count": 0},
        1,
        "bad",
    ],
)
def test_scope_state_source_validation(invalid_state: Any) -> None:
    if isinstance(invalid_state, dict):
        with pytest.raises(ValueError, match="Declarative state dicts"):
            normalize_state_source(invalid_state, owner=None)
    else:
        with pytest.raises(ValueError):
            normalize_state_source(invalid_state, owner=None)


def test_scope_state_source_from_class_and_statefield() -> None:
    class State:
        count = 0
        enabled = True
        qty = StateField(name="qty", from_prop="initialQty", default=1, cast="int")

    state = normalize_state_source(State, owner=None)

    assert state["count"] == 0
    assert state["enabled"] is True
    assert state["qty"]["cast"] == "int"


def test_scope_resolve_methods_actions_no_mappings() -> None:
    owner = SimpleNamespace(
        up=lambda: {"op": "add", "state": "count", "value": 1},
        down=lambda: {"op": "sub", "state": "count", "value": 1},
    )

    resolved = resolve_methods_actions(["up", "down"], owner)
    assert resolved["up"]["op"] == "add"
    assert resolved["down"]["op"] == "sub"

    with pytest.raises(ValueError, match="not supported"):
        resolve_methods_actions({"up": "up"}, owner)


def test_scope_invoke_method_callable_tracing_and_logs() -> None:
    class Owner(Component):
        def __init__(self) -> None:
            self.state = _TraceState()
            self.props = SimpleNamespace()

        def apply(self) -> None:
            print("hello")
            if self.state.count < 3:  # type: ignore[operator]
                self.state.count += 1  # type: ignore[operator]

    owner = Owner()
    result = invoke_method_callable("apply", owner.apply, owner)

    assert result["op"] in {"multi", "add"}


def test_scope_lifecycle_and_helpers() -> None:
    class Owner:
        def mounted(self) -> dict[str, Any]:
            return {"op": "log", "value": "mounted"}

    lifecycle = normalize_lifecycle_methods(Owner())

    assert canonical_lifecycle_name("on_mount") == "onMount"
    assert normalize_action_names("save") == ["save"]
    assert lifecycle["onMount"][0]["op"] == "log"

    class Actions(Component):
        def public_action(self) -> None:
            return None

    assert "public_action" in infer_action_methods(Actions())
    assert _extract_mapping_value({"a": 1}, ["x", "a"], 0) == 1
