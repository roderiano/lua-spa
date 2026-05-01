from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from lua_spa.scope import (
    _build_client_factory,
    _extract_class_properties,
    _extract_mapping_value,
    _extract_object_properties,
    _normalize_method_callable,
    canonical_lifecycle_name,
    infer_action_methods,
    invoke_method_callable,
    load_python_scope,
    normalize_action_names,
    normalize_client_spec,
    normalize_context_result,
    normalize_lifecycle_methods,
    normalize_lifecycle_spec,
    normalize_props_source,
    normalize_state_item,
    normalize_state_source,
    resolve_component_callables,
    resolve_component_instance,
    resolve_methods_actions,
    swap_attribute,
)
from lua_spa.trace import _TraceState
from lua_spa.types import Component, StateField


def test_load_scope_and_component_callables() -> None:
    # Given: a Python source block defining an App component with context and client
    source = """
class App(Component):
    def context(self, props):
        return {"title": props.get("title", "x")}

    def client(self):
        return {"props": {"count": 1}, "state": {"count": {"default": 1}}, "actions": {}}
"""

    # When: the scope is loaded and callables are resolved
    scope = load_python_scope(source)
    context_fn, client_fn = resolve_component_callables(scope)

    # Then: both context and client functions are callable
    assert callable(context_fn)
    assert callable(client_fn)


def test_scope_normalization_variants_and_errors() -> None:
    # Given: various context results, prop sources, state sources, and an invalid state item

    # When: normalization functions process each input

    # Then: outputs match expectations and invalid input raises ValueError
    assert normalize_context_result(None) == {}
    assert normalize_context_result({"a": 1})["a"] == 1
    obj = SimpleNamespace(a=2, _hidden=3)
    assert normalize_context_result(obj) == {"a": 2}

    assert normalize_props_source({"x": 1})["x"] == 1
    state = normalize_state_source([StateField(name="count", default=0, cast="int")], owner=None)
    assert state["count"]["cast"] == "int"

    try:
        normalize_state_item({"default": 1}, None)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


class _ClientSample:
    Props = {"start": 0}
    State = [StateField(name="count", from_prop="start", default=0, cast="int")]
    Methods = ["inc"]

    def inc(self) -> dict[str, Any]:
        return {"op": "add", "state": "count", "value": 1}


def test_scope_client_spec_and_method_resolution() -> None:
    # Given: a sample client class and a method owner namespace

    # When: client spec and method actions are resolved
    props, state, actions, lifecycle = normalize_client_spec(_ClientSample())
    method_owner = SimpleNamespace(increment=lambda: {"op": "add", "state": "count", "value": 1})
    actions2 = resolve_methods_actions(["increment"], method_owner)

    # Then: props, state, actions and lifecycle match the class definition
    assert props["start"] == 0
    assert "count" in state
    assert actions["inc"]["op"] == "add"
    assert set(lifecycle.keys()) == {"onCreate", "onMount", "onUpdate", "onUnmount"}
    assert actions2["increment"]["op"] == "add"


def test_scope_invoke_methods_lifecycle_and_attribute_swap() -> None:
    # Given: a Component owner with traced state, a lifecycle hook, and action methods
    class Owner(Component):
        value = 1

        def __init__(self) -> None:
            self.state = _TraceState()
            self.props = SimpleNamespace()

        def method(self) -> None:
            self.state.count += 1  # type: ignore[operator]

        def created(self) -> dict[str, Any]:
            return {"op": "log", "value": "created"}

        def do(self) -> None:
            return

    owner = Owner()

    # When: method is invoked, lifecycle is normalized, attribute is swapped, and action methods are inferred
    result = invoke_method_callable("method", owner.method, owner)
    life = normalize_lifecycle_methods(owner)
    restore = swap_attribute(owner, "value", 5)
    methods = infer_action_methods(owner)

    # Then: traced state produces an add op, lifecycle maps correctly, swap is reversible
    assert result["op"] == "add"
    assert life["onCreate"][0]["op"] == "log"
    assert callable(restore)
    restore()
    assert owner.value == 1
    assert "do" in methods


def test_scope_lifecycle_name_and_actions_normalization() -> None:
    # Given: lifecycle spec dicts, hook name strings, and action name inputs

    # When: normalization and canonical name helpers are called
    lifecycle = normalize_lifecycle_spec({"created": ["init"], "on_update": "refresh"})

    # Then: names are mapped to camelCase and invalid hooks raise ValueError
    assert lifecycle["onCreate"] == ["init"]
    assert lifecycle["onUpdate"] == ["refresh"]
    assert canonical_lifecycle_name("on_mount") == "onMount"
    assert normalize_action_names("save") == ["save"]

    try:
        canonical_lifecycle_name("unknown_hook")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


def test_scope_component_instance_paths() -> None:
    # Given: a zero-arg component class and one that requires arguments
    class Good(Component):
        pass

    class Bad(Component):
        def __init__(self, value: int) -> None:
            self.value = value

    # When: resolve_component_instance is called for each

    # Then: Good instantiates successfully; Bad raises ValueError
    assert isinstance(resolve_component_instance({"Component": Good}), Good)
    try:
        resolve_component_instance({"Component": Bad})
    except ValueError:
        return
    raise AssertionError("Expected ValueError")


def test_scope_branch_coverage_for_factories_and_errors() -> None:
    # Given: blank source, a class, a literal value, and various invalid client specs

    # When: factory and normalization helpers process each input

    # Then: each edge case is handled correctly or raises ValueError
    assert load_python_scope("   ") == {}

    class C:
        pass

    assert _build_client_factory(C) is C
    fn = _build_client_factory(123)
    assert callable(fn)
    assert fn() == 123

    try:
        normalize_client_spec({"actions": []})
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

    class BadClient:
        def actions(self) -> list[int]:
            return [1]

    try:
        normalize_client_spec(BadClient())
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

    class BadMethods:
        def methods(self) -> list[int]:
            return [1]

    try:
        normalize_client_spec(BadMethods())
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

    try:
        resolve_methods_actions(["missing"], SimpleNamespace())
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

    try:
        _normalize_method_callable("x", "y", None)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

    assert swap_attribute(None, "x", 1) is None


def test_scope_extract_helpers_and_state_item_strings() -> None:
    # Given: state classes, prop classes, namespaces, and mappings
    class StateCls:
        name = "count"
        default = 1
        cast = "int"

    class NeedArg:
        def __init__(self, x: int) -> None:
            self.x = x

    class PropsClass:
        a = 1
        _b = 2

    owner = SimpleNamespace(StateCls=StateCls)

    # When: extract and normalize helpers are called
    item = normalize_state_item("StateCls", owner)

    # Then: properties are extracted correctly and invalid inputs raise ValueError
    assert item["name"] == "count"

    try:
        normalize_state_item(NeedArg, None)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

    assert _extract_class_properties(PropsClass)["a"] == 1
    assert _extract_object_properties(SimpleNamespace(a=2, _x=1))["a"] == 2
    assert _extract_mapping_value({"x": 1}, ["y", "x"], 0) == 1


def test_scope_more_error_branches_and_lifecycle() -> None:
    # Given: a bad component callable, invalid callables dict, a lifecycle owner, and invalid specs
    def bad_component(required: int) -> int:
        return required

    class Owner:
        def onCreate(self) -> None:
            return None

        def on_mount(self) -> dict[str, Any]:
            return {"op": "log", "value": "m"}

    # When: resolution and normalization helpers process each input

    # Then: invalid shapes raise ValueError; valid lifecycle maps correctly
    try:
        resolve_component_instance({"component": bad_component})
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

    try:
        resolve_component_callables({"client": 1})
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

    lifecycle = normalize_lifecycle_methods(Owner())
    assert "onMount" in lifecycle

    try:
        normalize_lifecycle_spec([])
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

    try:
        normalize_action_names([1])
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


def test_scope_invoke_method_callable_additional_paths() -> None:
    # Given: an owner with methods that print, trace state, return truthy, and return None
    class Owner:
        def __init__(self) -> None:
            self.state = _TraceState()
            self.props = SimpleNamespace()

        def with_print(self) -> None:
            print("hello")

        def returns_mapping_and_traces(self) -> dict[str, Any]:
            self.state.count += 1  # type: ignore[operator]
            return {"op": "set", "state": "count", "value": 2}

        def returns_truthy(self) -> int:
            return 1

        def returns_none(self) -> None:
            return None

    owner = Owner()

    # When: each method callable is invoked via invoke_method_callable
    result_log = invoke_method_callable("with_print", owner.with_print, owner)
    result_multi = invoke_method_callable(
        "returns_mapping_and_traces", owner.returns_mapping_and_traces, owner
    )
    result_truthy = invoke_method_callable("returns_truthy", owner.returns_truthy, owner)
    result_none = invoke_method_callable("returns_none", owner.returns_none, owner)

    # Then: each returns the expected op type or noop marker
    assert result_log["op"] in {"log", "set", "multi"}
    assert result_multi["op"] == "multi"
    assert result_truthy["state"] == "__noop__"
    assert result_none["state"] == "__noop__"
