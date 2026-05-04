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


def test_scope_additional_component_and_callable_error_paths() -> None:
    # Given: component subclass requiring args and invalid top-level context callable
    class BadComp(Component):
        def __init__(self, required: int) -> None:
            self.required = required

    try:
        resolve_component_instance({"BadComp": BadComp})
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

    try:
        resolve_component_callables({"context": 1})
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


def test_scope_client_spec_mapping_and_instance_branches() -> None:
    # Given: mapping-based client spec including Methods and lifecycle
    mapping_spec = {
        "props": {"a": 1},
        "state": {"count": {"default": 0}},
        "actions": {"set": {"op": "set", "state": "count", "value": 1}},
        "Methods": {"log": {"op": "log", "value": "ok"}},
        "lifecycle": {"on_mount": ["log"]},
    }
    props, state, actions, lifecycle = normalize_client_spec(mapping_spec)
    assert props["a"] == 1
    assert "log" in actions
    assert lifecycle["onMount"] == ["log"]

    # Given: instance spec exercising lower-case attrs and callable overrides
    class StateObj:
        name = "counter"
        default = 1
        cast = "int"

        def init(self) -> int:
            return 2

    class Spec:
        props = {"x": 1}
        state = [StateObj]
        methods = ["do"]
        lifecycle = {"mounted": ["do"]}

        def state(self) -> list[Any]:
            return [StateObj()]

        def actions(self) -> None:
            return None

        def methods(self) -> None:
            return None

        def lifecycle(self) -> dict[str, list[str]]:
            return {"updated": ["do"]}

        def do(self) -> dict[str, Any]:
            return {"op": "log", "value": "x"}

    props2, state2, actions2, lifecycle2 = normalize_client_spec(Spec())
    assert props2["x"] == 1
    assert state2["counter"]["default"] == 1
    assert "do" in actions2
    assert lifecycle2["onUpdate"] == []


def test_scope_state_methods_and_infer_helpers_extra_paths() -> None:
    # Given / When: normalize_state_source receives invalid shape
    try:
        normalize_state_source(123, owner=None)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

    # Given / When: state item string requires owner and must exist
    try:
        normalize_state_item("StateCls", None)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

    try:
        normalize_state_item("Missing", SimpleNamespace())
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

    class BadState:
        default = 1

    try:
        normalize_state_item(BadState(), None)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

    class GoodState:
        name = "count"
        default = 1

        def init(self) -> int:
            return 2

    out = normalize_state_item(GoodState(), None)
    assert callable(out["init"])

    # Given / When: methods resolver branches
    assert resolve_methods_actions(None, owner=None) == {}
    assert resolve_methods_actions({"a": {"op": "log", "value": 1}}, owner=None)["a"]["op"] == "log"
    try:
        resolve_methods_actions([1], owner=SimpleNamespace())
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")
    try:
        resolve_methods_actions(1, owner=None)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

    # Given / When: normalize method callable resolves callable and string refs
    owner = SimpleNamespace(run=lambda: {"op": "log", "value": "ok"})
    assert callable(_normalize_method_callable("run", owner.run, owner))
    assert callable(_normalize_method_callable("run", "run", owner))

    # Given / When: infer_action_methods skips type attributes
    class O:
        ValueType = dict

        def act(self) -> None:
            return None

    assert infer_action_methods(O()) == ["act"]


def test_scope_invoke_method_and_lifecycle_noop_paths() -> None:
    # Given: method callable with custom __builtins__ object forcing non-dict restoration path
    class BuiltinsObj:
        pass

    class CallableObj:
        __globals__ = {"__builtins__": BuiltinsObj()}

        def __call__(self) -> None:
            raise TypeError("force second call")

    result = invoke_method_callable("x", CallableObj(), owner=None)
    assert result["state"] == "__noop__"

    # Given: lifecycle hook returning no-op should be filtered
    class Owner:
        def onCreate(self) -> None:
            return None

    lifecycle = normalize_lifecycle_methods(Owner())
    assert lifecycle["onCreate"] == []

    # Given / When: normalize_lifecycle_spec receives None
    lifecycle_spec = normalize_lifecycle_spec(None)
    assert lifecycle_spec["onMount"] == []


def test_scope_remaining_normalization_paths() -> None:
    # Given / When: raw_spec None branch
    props, state, actions, lifecycle = normalize_client_spec(None)
    assert props == {}
    assert state == {}
    assert actions == {}
    assert lifecycle["onCreate"] == []

    # Given / When: props/state/methods/lifecycle lower-case attribute branches
    class SpecAttr:
        props = {"a": 1}
        state = [StateField(name="count", default=0, cast="int")]
        methods = ["do"]
        lifecycle = {"on_mount": ["do"]}

        def do(self) -> dict[str, Any]:
            return {"op": "log", "value": "ok"}

    props2, state2, actions2, lifecycle2 = normalize_client_spec(SpecAttr())
    assert props2["a"] == 1
    assert state2["count"]["cast"] == "int"
    assert "do" in actions2
    assert lifecycle2["onMount"] == []

    # Given / When: props callable branch
    class SpecPropsMethod:
        def props(self) -> dict[str, int]:
            return {"m": 2}

    props3, _, _, _ = normalize_client_spec(SpecPropsMethod())
    assert props3["m"] == 2

    # Given / When: lifecycle attr (non-callable) is normalized
    class SpecLifecycleAttr:
        lifecycle = {"created": ["x"]}

    _, _, _, lifecycle3 = normalize_client_spec(SpecLifecycleAttr())
    assert lifecycle3["onCreate"] == []

    # Given / When: props source branches
    class PropsClass:
        x = 1

    assert normalize_props_source(None) == {}
    assert normalize_props_source(PropsClass)["x"] == 1
    assert normalize_props_source(SimpleNamespace(y=2))["y"] == 2
    try:
        normalize_props_source(1)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

    # Given / When: mapping methods callable normalization branch
    owner = SimpleNamespace(do=lambda: {"op": "set", "state": "a", "value": 1})
    actions_map = resolve_methods_actions({"do": "do"}, owner)
    assert actions_map["do"]["op"] == "set"
