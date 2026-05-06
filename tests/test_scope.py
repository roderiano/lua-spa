from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from lua_spa.scope import (
    _coerce_setup_result,
    _normalize_setup_action_callable,
    _normalize_setup_spec,
    _rewire_callable_closure,
    _extract_mapping_value,
    canonical_lifecycle_name,
    execute_setup_server_callable,
    infer_action_methods,
    invoke_method_callable,
    load_python_scope,
    normalize_context_result,
    normalize_action_names,
    normalize_client_spec,
    normalize_lifecycle_spec,
    normalize_state_item,
    normalize_lifecycle_methods,
    normalize_props_source,
    normalize_state_source,
    resolve_component_callables,
    resolve_component_instance,
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
    assert lifecycle["onMount"][0]["op"] == "server_call"


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
    assert lifecycle["onMount"] == []


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
    assert lifecycle["onMount"][0]["op"] == "server_call"


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


def test_scope_context_normalization_mapping_object_and_invalid() -> None:
    class ContextObject:
        def __init__(self) -> None:
            self.visible = 1
            self._hidden = 2

    assert normalize_context_result(None) == {}
    assert normalize_context_result({"a": 1}) == {"a": 1}
    assert normalize_context_result(ContextObject()) == {"visible": 1}
    with pytest.raises(ValueError, match="context\(props\) must return"):
        normalize_context_result(123)


def test_scope_resolve_component_instance_errors_for_invalid_construction() -> None:
    with pytest.raises(ValueError, match="component\(\) must be callable without arguments"):
        resolve_component_instance({"component": lambda x: x})

    class Broken(Component):
        def __init__(self, required: int) -> None:
            self.required = required

    with pytest.raises(ValueError, match="Component class must be instantiable"):
        resolve_component_instance({"Component": Broken})


def test_scope_resolve_component_callables_rejects_non_component_scope() -> None:
    with pytest.raises(ValueError, match="must define a Component subclass"):
        resolve_component_callables({"x": 1})


def test_scope_coerce_setup_result_invalid_non_mapping() -> None:
    with pytest.raises(ValueError, match="must return a mapping or None"):
        _coerce_setup_result(SimpleNamespace(), 1, {}, {})


def test_scope_normalize_setup_spec_variants_and_errors() -> None:
    def callable_hook() -> dict[str, Any]:
        return {"ok": True}

    normalized = _normalize_setup_spec(
        {
            "props": SimpleNamespace(title="demo"),
            "state": SimpleNamespace(count=1),
            "actions": {"save": {"op": "set", "state": "x", "value": 1}},
            "lifecycle": {
                "mounted": "save",
                "updated": {"op": "log", "value": "updated"},
                "unmounted": [callable_hook, "save", {"op": "log", "value": "bye"}],
            },
        }
    )

    props, state, actions, lifecycle = normalized
    assert props["title"] == "demo"
    assert state["count"] == 1
    assert actions["save"]["op"] == "set"
    assert lifecycle["onMount"] == ["save"]
    assert lifecycle["onUpdate"][0]["op"] == "log"
    assert len(lifecycle["onUnmount"]) == 3

    with pytest.raises(ValueError, match="setup\(\)\.actions must be a mapping"):
        _normalize_setup_spec({"actions": 1})

    with pytest.raises(ValueError, match="setup\(\)\.lifecycle must be a mapping"):
        _normalize_setup_spec({"lifecycle": 1})

    with pytest.raises(ValueError, match="must be callable or mapping"):
        _normalize_setup_spec({"actions": {"bad": 1}})


def test_scope_execute_setup_server_callable_error_paths() -> None:
    source_unknown_action = """
class Features(Component):
    def setup(self, props):
        return {"props": props, "state": {}, "actions": {}, "lifecycle": {}}
"""
    with pytest.raises(ValueError, match="Unknown action"):
        execute_setup_server_callable(source_unknown_action, "action", "missing", {}, {})

    source_lifecycle_bad = """
class Features(Component):
    def setup(self, props):
        return {
            "props": props,
            "state": {},
            "actions": {},
            "lifecycle": {"mounted": 1},
        }
"""
    with pytest.raises(ValueError, match="Unsupported lifecycle hook value"):
        execute_setup_server_callable(source_lifecycle_bad, "lifecycle", "mounted", {}, {})


def test_scope_normalize_setup_action_callable_and_helpers() -> None:
    state_backing = {"count": 1, "mode": "idle"}

    def action() -> dict[str, Any]:
        state_backing["count"] += 2
        state_backing["mode"] = "done"
        return {"toast": "ok"}

    op = _normalize_setup_action_callable("action", action, state_backing)
    assert op["op"] == "multi"
    assert state_backing == {"count": 1, "mode": "idle"}

    class Owner:
        pass

    owner = Owner()
    restore = swap_attribute(owner, "temp", 10)
    assert owner.temp == 10
    assert restore is not None
    restore()
    assert not hasattr(owner, "temp")


def test_scope_normalize_state_item_and_lifecycle_spec_errors() -> None:
    class Stateful:
        name = "qty"
        from_prop = "initialQty"
        default = 1
        cast = "int"

        def init(self) -> int:
            return 1

    owner = SimpleNamespace(Stateful=Stateful)
    normalized = normalize_state_item("Stateful", owner)
    assert normalized["name"] == "qty"
    assert callable(normalized.get("init"))

    with pytest.raises(ValueError, match="String state items require a client instance"):
        normalize_state_item("Stateful", None)

    with pytest.raises(ValueError, match="Unknown state class reference"):
        normalize_state_item("MissingState", owner)

    with pytest.raises(ValueError, match="client\(\)\.lifecycle must be a mapping"):
        normalize_lifecycle_spec(1)

    with pytest.raises(ValueError, match="Lifecycle action names must be strings"):
        normalize_action_names(["ok", 1])


def test_scope_rewire_callable_closure_keeps_callable_when_unmodified() -> None:
    def outer() -> Any:
        value = 1

        def inner() -> int:
            return value

        return inner

    callable_obj = outer()
    rewired = _rewire_callable_closure(callable_obj, {})
    assert rewired is callable_obj
