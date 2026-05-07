from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from lua_spa.scope import (
    _build_client_factory,
    _coerce_setup_result,
    _extract_class_properties,
    _extract_object_properties,
    _normalize_method_callable,
    _normalize_setup_action_callable,
    _extract_mapping_value,
    _rewire_callable_closure,
    _invoke_setup_with_locals,
    execute_setup_server_callable,
    infer_action_methods,
    invoke_method_callable,
    load_python_scope,
    normalize_client_spec,
    normalize_context_result,
    normalize_state_item,
    normalize_props_source,
    normalize_state_source,
    resolve_component_instance,
    resolve_component_callables,
    resolve_methods_actions,
    swap_attribute,
)
from lua_spa.trace import _TraceState
from lua_spa.types import Component, StateField


def test_scope_resolve_component_callables_with_python_spec() -> None:
    source = """
class Counter(Component):
    def setup(self, props):
        state = {"count": 0}

        def inc():
            state["count"] += 1

        return {
            "props": {"title": props.get("title", "default")},
            "state": state,
            "data": {},
            "actions": {"inc": inc},
            "lifecycle": {},
        }
"""
    scope = load_python_scope(source)
    context_fn, client_fn = resolve_component_callables(scope)

    assert callable(context_fn)
    assert callable(client_fn)


def test_scope_normalize_client_spec_class_only() -> None:
    state = {
        "count": 0,
        "qty": {"from_prop": "initialQty", "default": 1, "cast": "int"},
    }

    def inc() -> dict[str, Any]:
        return {"op": "add", "state": "count", "value": 1}

    props, state, actions, lifecycle = normalize_client_spec(
        {
            "__setup_mapped__": True,
            "props": {"title": "hello"},
            "state": state,
            "data": {},
            "actions": {"inc": inc},
            "lifecycle": {},
        }
    )

    assert props["title"] == "hello"
    assert state["count"] == 0
    assert state["qty"]["from_prop"] == "initialQty"
    assert actions["inc"]["op"] == "server_call"
    assert actions["inc"]["kind"] == "action"
    assert lifecycle["mounted"] == []


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


def test_scope_invoke_method_callable_tracing_and_logs(capsys: pytest.CaptureFixture[str]) -> None:
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
    captured = capsys.readouterr()

    assert result["op"] in {"multi", "add"}
    assert "hello" in captured.out
    if result["op"] == "multi":
        assert any(
            step.get("op") == "log" and step.get("value") == "hello"
            for step in result.get("steps", [])
            if isinstance(step, dict)
        )


def test_scope_lifecycle_and_helpers() -> None:
    class Actions(Component):
        def public_action(self) -> None:
            return None

    assert "public_action" in infer_action_methods(Actions())
    assert _extract_mapping_value({"a": 1}, ["x", "a"], 0) == 1


def test_scope_rejects_non_canonical_lifecycle_name() -> None:
    with pytest.raises(ValueError, match="Unknown lifecycle hook"):
        normalize_client_spec(
            {
                "__setup_mapped__": True,
                "props": {},
                "state": {},
                "data": {},
                "actions": {},
                "lifecycle": {"Mounted": "run"},
            }
        )


def test_scope_setup_mapping_is_normalized_automatically() -> None:
    source = """
class Features(Component):
    def setup(self, props):
        props = {"title": "lua-spa", **props}
        state = {"mounted": False, "reload_count": 0, "status": "idle"}
        data = {"pypi": {"available": True, "latest": "1.0.0"}}

        def reload_packages():
            return {"op": "log", "value": "reload"}

        def mounted():
            return {"op": "log", "value": "mounted"}

        return {
            "props": props,
            "state": state,
            "data": data,
            "actions": {"reload_packages": reload_packages},
            "lifecycle": {"mounted": mounted},
        }
"""

    scope = load_python_scope(source)
    context_fn, client_fn = resolve_component_callables(scope)

    assert callable(context_fn)
    assert callable(client_fn)

    context = context_fn({})
    assert context["pypi"]["available"] is True

    props, state, actions, lifecycle = normalize_client_spec(client_fn({}))
    assert props["title"] == "lua-spa"
    assert props["pypi"]["latest"] == "1.0.0"
    assert state["reload_count"] == 0
    assert actions["reload_packages"]["op"] == "server_call"
    assert actions["reload_packages"]["name"] == "reload_packages"
    assert lifecycle["mounted"][0]["op"] == "server_call"


def test_scope_setup_automatic_mapping_without_return() -> None:
    source = """
class Card(Component):
    def setup(self, props):
        price = props.get("price", 0)
        self.props = props
        self.state = {}
        self.data = {
            "display": f"${price:.2f}",
            "is_cheap": price < 10,
        }
        self.actions = {}
        self.lifecycle = {}
"""

    scope = load_python_scope(source)
    context_fn, client_fn = resolve_component_callables(scope)

    context = context_fn({"price": 7})
    props, state, actions, lifecycle = normalize_client_spec(client_fn({"price": 7}))

    assert context["display"] == "$7.00"
    assert context["is_cheap"] is True
    assert props["price"] == 7
    assert state == {}
    assert actions == {}
    assert lifecycle["mounted"] == []


def test_scope_setup_infers_actions_and_lifecycle_from_local_functions() -> None:
    source = """
class Features(Component):
    def setup(self, props):
        state = {"count": 0}
        data = {"title": "x"}

        def reload_packages():
            state["count"] += 1

        def mounted():
            reload_packages()
"""

    scope = load_python_scope(source)
    context_fn, client_fn = resolve_component_callables(scope)
    assert callable(context_fn)
    assert callable(client_fn)

    context = context_fn({})
    props, state, actions, lifecycle = normalize_client_spec(client_fn({}))

    assert context["title"] == "x"
    assert state["count"] == 0
    assert actions["reload_packages"]["op"] == "server_call"
    assert actions["reload_packages"]["kind"] == "action"
    assert lifecycle["mounted"][0]["op"] == "server_call"


def test_scope_lifecycle_merges_nested_action_results_without_return() -> None:
    source = """
class Features(Component):
    def setup(self, props):
        state = {"mounted": False, "reload_count": 0, "status": "idle"}

        def reload_packages():
            state["reload_count"] += 1
            state["status"] = "updated"
            return {"pypi": {"available": True, "latest": "1.2.3"}}

        def mounted():
            state["mounted"] = True
            reload_packages()

        return {
            "props": props,
            "state": state,
            "data": {"pypi": {"available": False, "latest": ""}},
            "actions": {"reload_packages": reload_packages},
            "lifecycle": {"mounted": mounted},
        }
"""

    patch = execute_setup_server_callable(
        source,
        kind="lifecycle",
        name="mounted",
        props={},
        state={},
    )

    assert patch["state"]["mounted"] is True
    assert patch["state"]["reload_count"] == 1
    assert patch["state"]["status"] == "updated"
    assert patch["props"]["pypi"]["available"] is True
    assert patch["props"]["pypi"]["latest"] == "1.2.3"


def test_scope_lifecycle_captures_print_logs() -> None:
    source = """
class Features(Component):
    def setup(self, props):
        state = {"count": 0}

        def increment():
            print("incrementing counter")
            state["count"] += 1

        def mounted():
            print("component mounted")
            increment()
            print("finished mounting")

        return {
            "props": props,
            "state": state,
            "actions": {"increment": increment},
            "lifecycle": {"mounted": mounted},
        }
"""

    patch = execute_setup_server_callable(
        source,
        kind="lifecycle",
        name="mounted",
        props={},
        state={},
    )

    assert patch["state"]["count"] == 1
    assert "__lua_logs__" in patch["props"]
    assert isinstance(patch["props"]["__lua_logs__"], list)
    assert "component mounted" in patch["props"]["__lua_logs__"]
    assert "incrementing counter" in patch["props"]["__lua_logs__"]
    assert "finished mounting" in patch["props"]["__lua_logs__"]


def test_scope_action_mutating_data_without_return_updates_props_patch() -> None:
    source = """
class Features(Component):
    def setup(self, props):
        state = {"count": 0}
        data = {"pypi": {"latest": "", "available": False}}

        def reload_packages():
            state["count"] += 1
            data["pypi"] = {"latest": "1.2.3", "available": True}

"""

    patch = execute_setup_server_callable(
        source,
        kind="action",
        name="reload_packages",
        props={},
        state={},
    )

    assert patch["state"]["count"] == 1
    assert patch["props"]["pypi"]["latest"] == "1.2.3"
    assert patch["props"]["pypi"]["available"] is True


def test_scope_normalize_context_result_variants() -> None:
    assert normalize_context_result(None) == {}
    assert normalize_context_result({"a": 1}) == {"a": 1}

    class Obj:
        def __init__(self) -> None:
            self.public = 2
            self._private = 9

    assert normalize_context_result(Obj()) == {"public": 2}

    with pytest.raises(ValueError, match=r"context\(props\) must return"):
        normalize_context_result(123)


def test_scope_resolve_component_instance_error_paths() -> None:
    def component() -> Any:
        raise TypeError("boom")

    with pytest.raises(ValueError, match=r"component\(\) must be callable"):
        resolve_component_instance({"component": component})

    class BadComponent(Component):
        def __init__(self, required: int) -> None:
            self.required = required

    with pytest.raises(ValueError, match="instantiable without arguments"):
        resolve_component_instance({"Component": BadComponent})


def test_scope_build_client_factory_and_coerce_result() -> None:
    value_factory = _build_client_factory(10)
    assert callable(value_factory)
    assert value_factory() == 10

    with pytest.raises(ValueError, match="must return a mapping or None"):
        _coerce_setup_result(SimpleNamespace(), 1, {}, {})


def test_scope_invoke_setup_with_locals_captures_frame_locals() -> None:
    class C:
        def setup(self, props: dict[str, Any]) -> dict[str, Any]:
            state = {"count": props.get("seed", 0)}
            return {"state": state}

    result, captured = _invoke_setup_with_locals(C().setup, {"seed": 3})
    assert isinstance(result, dict)
    assert "state" in captured


def test_scope_normalize_setup_action_callable_with_multi_steps() -> None:
    state_backing = {"count": 1}

    def action() -> dict[str, Any]:
        state_backing["count"] = 3
        return {"status": "ok"}

    operation = _normalize_setup_action_callable("inc", action, state_backing)
    assert operation["op"] == "multi"
    assert state_backing["count"] == 1


def test_scope_state_item_and_method_resolution_errors() -> None:
    with pytest.raises(ValueError, match="State list items cannot be dicts"):
        normalize_state_item({"name": "x"}, owner=None)

    with pytest.raises(ValueError, match="String state items require"):
        normalize_state_item("StateRef", owner=None)

    with pytest.raises(ValueError, match="Unknown state class reference"):
        normalize_state_item("Missing", owner=SimpleNamespace())

    class NeedsArg:
        def __init__(self, n: int) -> None:
            self.n = n

    with pytest.raises(ValueError, match="instantiable without arguments"):
        normalize_state_item(NeedsArg, owner=None)

    with pytest.raises(ValueError, match="must define a string 'name' attribute"):
        normalize_state_item(SimpleNamespace(name=""), owner=None)

    with pytest.raises(ValueError, match="must be a callable function"):
        _normalize_method_callable("run", 42, owner=None)


def test_scope_swap_extract_and_rewire_helpers() -> None:
    owner = SimpleNamespace()
    restore = swap_attribute(owner, "temp", 1)
    assert owner.temp == 1
    assert callable(restore)
    restore()
    assert not hasattr(owner, "temp")

    class A:
        visible = 1
        _hidden = 2

        def method(self) -> None:
            return None

    class_props = _extract_class_properties(A)
    assert class_props == {"visible": 1}

    obj_props = _extract_object_properties(SimpleNamespace(visible=3, _x=9))
    assert obj_props["visible"] == 3

    def plain() -> dict[str, Any]:
        return {"ok": True}

    assert _rewire_callable_closure(plain, {}) is plain


def test_scope_execute_server_callable_error_paths() -> None:
    source = """
class Demo(Component):
    def setup(self, props):
        return {
            "props": props,
            "state": {},
            "actions": {},
            "lifecycle": {"mounted": 123},
        }
"""

    with pytest.raises(ValueError, match="Unsupported lifecycle hook value"):
        execute_setup_server_callable(source, kind="lifecycle", name="mounted", props={}, state={})

    with pytest.raises(ValueError, match="Unknown action"):
        execute_setup_server_callable(source, kind="action", name="missing", props={}, state={})
