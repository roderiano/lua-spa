from __future__ import annotations

import builtins
from types import SimpleNamespace
from typing import Any

import pytest
import moon_spa.scope as scope_module

from moon_spa.scope import (
    _build_client_factory,
    _coerce_setup_result,
    _extract_class_properties,
    _extract_object_properties,
    _normalize_method_callable,
    _normalize_state_attributes,
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
from moon_spa.trace import _TraceState
from moon_spa.types import Component, StateField


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


def test_scope_invoke_method_callable_tracing_and_logs(
    capsys: pytest.CaptureFixture[str],
) -> None:
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
        props = {"title": "moon-spa", **props}
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
    assert props["title"] == "moon-spa"
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
    assert "__moon_logs__" in patch["props"]
    assert isinstance(patch["props"]["__moon_logs__"], list)
    assert "component mounted" in patch["props"]["__moon_logs__"]
    assert "incrementing counter" in patch["props"]["__moon_logs__"]
    assert "finished mounting" in patch["props"]["__moon_logs__"]


def test_scope_mounted_preserves_incoming_payload_data() -> None:
    source = """
class Features(Component):
    def setup(self, props):
        state = {"mounted": False, "reload_count": 0, "status": "idle"}
        data = {
            "pypi": {
                "available": False,
                "error": "",
                "versions": [],
                "latest": "",
                "author": "",
                "maintainer": "",
                "owner_matches": False,
            }
        }

        def mounted():
            state["mounted"] = True

        return {
            "props": props,
            "state": state,
            "data": data,
            "actions": {},
            "lifecycle": {"mounted": mounted},
        }
"""

    patch = execute_setup_server_callable(
        source,
        kind="lifecycle",
        name="mounted",
        props={
            "__moon_logs__": [
                "[features] fetching pypi payload for moon-spa",
                "[features] payload returned",
            ],
            "pypi": {
                "available": True,
                "error": "",
                "versions": ["1.2.0"],
                "latest": "1.2.0",
                "author": "Gabriel da Rosa Silveira",
                "maintainer": "",
                "owner_matches": False,
            },
        },
        state={"mounted": False, "reload_count": 1, "status": "updated"},
    )

    assert patch["state"]["mounted"] is True
    assert patch["state"]["reload_count"] == 1
    assert patch["state"]["status"] == "updated"
    assert patch["props"]["pypi"]["available"] is True
    assert patch["props"]["pypi"]["latest"] == "1.2.0"


def test_scope_created_overrides_incoming_default_payload_data() -> None:
    source = """
class Features(Component):
    def setup(self, props):
        state = {"mounted": False, "reload_count": 0, "status": "idle"}
        data = {
            "pypi": {
                "available": False,
                "error": "",
                "versions": [],
                "latest": "",
                "author": "",
                "maintainer": "",
                "owner_matches": False,
            }
        }

        def reload_packages():
            state["reload_count"] += 1
            state["status"] = "updated"
            data["pypi"] = {
                "available": True,
                "error": "",
                "versions": ["1.2.0"],
                "latest": "1.2.0",
                "author": "Gabriel da Rosa Silveira",
                "maintainer": "",
                "owner_matches": False,
            }

        def created():
            reload_packages()

        return {
            "props": props,
            "state": state,
            "data": data,
            "actions": {"reload_packages": reload_packages},
            "lifecycle": {"created": created},
        }
"""

    patch = execute_setup_server_callable(
        source,
        kind="lifecycle",
        name="created",
        props={
            "pypi": {
                "available": False,
                "error": "",
                "versions": [],
                "latest": "",
                "author": "",
                "maintainer": "",
                "owner_matches": False,
            }
        },
        state={"mounted": False, "reload_count": 0, "status": "idle"},
    )

    assert patch["state"]["reload_count"] == 1
    assert patch["state"]["status"] == "updated"
    assert patch["props"]["pypi"]["available"] is True
    assert patch["props"]["pypi"]["latest"] == "1.2.0"


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
        execute_setup_server_callable(
            source, kind="lifecycle", name="mounted", props={}, state={}
        )

    with pytest.raises(ValueError, match="Unknown action"):
        execute_setup_server_callable(
            source, kind="action", name="missing", props={}, state={}
        )


def test_scope_resolve_component_callables_requires_component_subclass() -> None:
    with pytest.raises(ValueError, match="must define a Component subclass"):
        resolve_component_callables({"any": 1})


def test_scope_normalize_client_spec_additional_error_paths() -> None:
    with pytest.raises(ValueError, match="must return a mapping"):
        normalize_client_spec(None)

    with pytest.raises(ValueError, match=r"Only setup\(self, props\) mapping output"):
        normalize_client_spec(123)

    with pytest.raises(ValueError, match=r"setup\(\)\.actions must be a mapping"):
        normalize_client_spec(
            {
                "__setup_mapped__": True,
                "props": {},
                "state": {},
                "data": {},
                "actions": 1,
                "lifecycle": {},
            }
        )

    with pytest.raises(ValueError, match=r"setup\(\)\.lifecycle must be a mapping"):
        normalize_client_spec(
            {
                "__setup_mapped__": True,
                "props": {},
                "state": {},
                "data": {},
                "actions": {},
                "lifecycle": 1,
            }
        )

    with pytest.raises(
        ValueError, match="entries must be callables, strings, or mappings"
    ):
        normalize_client_spec(
            {
                "__setup_mapped__": True,
                "props": {},
                "state": {},
                "data": {},
                "actions": {},
                "lifecycle": {"mounted": [1]},
            }
        )

    with pytest.raises(
        ValueError, match="values must be callable, string, list, or mapping"
    ):
        normalize_client_spec(
            {
                "__setup_mapped__": True,
                "props": {},
                "state": {},
                "data": {},
                "actions": {},
                "lifecycle": {"mounted": 1},
            }
        )


def test_scope_normalize_client_spec_with_non_mapping_props_state_sources() -> None:
    class Props:
        title = "hello"

    class QtyState:
        name = "qty"
        from_prop = "initialQty"
        default = 1
        cast = "int"

        def init(self) -> int:
            return 1

    def created_hook() -> dict[str, Any]:
        return {"ok": True}

    props, state, actions, lifecycle = normalize_client_spec(
        {
            "__setup_mapped__": True,
            "props": Props,
            "state": [QtyState],
            "data": {"subtitle": "world"},
            "actions": None,
            "lifecycle": {
                "created": {"op": "log", "value": "created"},
                "mounted": [created_hook, "created", {"op": "log", "value": "mounted"}],
            },
        }
    )

    assert props["title"] == "hello"
    assert props["subtitle"] == "world"
    assert state["qty"]["cast"] == "int"
    assert "init" in state["qty"]
    assert actions == {}
    assert lifecycle["created"][0]["op"] == "log"
    assert lifecycle["mounted"][0]["op"] == "server_call"


def test_scope_execute_setup_server_callable_lifecycle_string_and_list_paths() -> None:
    source = """
class Demo(Component):
    def setup(self, props):
        state = {"calls": 0}
        data = {"status": "idle"}

        def takes_payload(payload):
            print("payload", payload)
            state["calls"] += 1
            return {"status": "done", "payload_is_none": payload is None}

        def inline(payload):
            state["calls"] += 1
            return {"inline_payload_none": payload is None}

        return {
            "props": props,
            "state": state,
            "data": data,
            "actions": {"takes_payload": takes_payload},
            "lifecycle": {
                "mounted": "takes_payload",
                "updated": [inline, "takes_payload"],
            },
        }
"""

    mounted_patch = execute_setup_server_callable(
        source,
        kind="lifecycle",
        name="mounted",
        props={},
        state={},
    )
    updated_patch = execute_setup_server_callable(
        source,
        kind="lifecycle",
        name="updated",
        props={},
        state={},
    )

    assert mounted_patch["state"]["calls"] == 1
    assert mounted_patch["props"]["payload_is_none"] is True
    assert "payload None" in mounted_patch["props"]["__moon_logs__"]

    assert updated_patch["state"]["calls"] == 2
    assert updated_patch["props"]["inline_payload_none"] is True
    assert updated_patch["props"]["payload_is_none"] is True


def test_scope_execute_setup_server_callable_component_contract_errors() -> None:
    with pytest.raises(ValueError, match="must define a Component subclass"):
        execute_setup_server_callable(
            "",
            kind="action",
            name="any",
            props={},
            state={},
        )

    source_without_setup = """
class Demo(Component):
    pass
"""
    with pytest.raises(ValueError, match=r"must define setup\(self, props\)"):
        execute_setup_server_callable(
            source_without_setup,
            kind="action",
            name="any",
            props={},
            state={},
        )


def test_scope_execute_setup_server_callable_actions_mapping_errors() -> None:
    source_string_lifecycle = """
class Demo(Component):
    def setup(self, props):
        return {
            "props": props,
            "state": {},
            "actions": 1,
            "lifecycle": {"mounted": "missing"},
        }
"""
    with pytest.raises(ValueError, match="Unknown lifecycle action"):
        execute_setup_server_callable(
            source_string_lifecycle,
            kind="lifecycle",
            name="mounted",
            props={},
            state={},
        )

    source_list_lifecycle = """
class Demo(Component):
    def setup(self, props):
        return {
            "props": props,
            "state": {},
            "actions": 1,
            "lifecycle": {"mounted": ["missing"]},
        }
"""
    patch = execute_setup_server_callable(
        source_list_lifecycle,
        kind="lifecycle",
        name="mounted",
        props={},
        state={},
    )
    assert patch["state"] == {}
    assert patch["props"] == {}


def test_scope_state_methods_and_inference_additional_paths() -> None:
    class QtyState:
        name = "qty"
        from_prop = "initialQty"
        default = 1
        cast = "int"

        def init(self) -> int:
            return 1

    owner = SimpleNamespace(QtyState=QtyState)
    state = normalize_state_source(
        ["QtyState", StateField(name="enabled", default=False)], owner
    )
    assert state["qty"]["from_prop"] == "initialQty"
    assert "init" in state["qty"]
    assert state["enabled"]["default"] is False

    class Methods:
        def inc(self) -> dict[str, Any]:
            return {"op": "add", "state": "count", "value": 1}

    resolved_from_class = resolve_methods_actions(Methods, owner=SimpleNamespace())
    assert resolved_from_class["inc"]["op"] == "add"

    methods_obj = SimpleNamespace(
        dec=lambda: {"op": "sub", "state": "count", "value": 1}
    )
    resolved_from_object = resolve_methods_actions(methods_obj, owner=SimpleNamespace())
    assert resolved_from_object["dec"]["op"] == "sub"

    with pytest.raises(ValueError, match="must contain method names as strings"):
        resolve_methods_actions([1], owner=SimpleNamespace())

    with pytest.raises(ValueError, match="require a client object instance"):
        resolve_methods_actions(["inc"], owner=None)

    with pytest.raises(ValueError, match="unknown callable"):
        resolve_methods_actions(["missing"], owner=SimpleNamespace())

    class ActionOwner:
        Props = lambda self: None
        Factory = dict

        def run(self) -> None:
            return None

    actions = infer_action_methods(ActionOwner())
    assert actions == ["run"]


def test_scope_invoke_callable_and_helpers_additional_paths() -> None:
    def method_for_owner(self: Any, payload: Any) -> None:
        del self
        del payload

    result = invoke_method_callable("broken", method_for_owner, owner=SimpleNamespace())
    assert result == {"op": "set", "state": "__noop__", "value": None}

    owner = SimpleNamespace(call=lambda: "value")
    callable_ref = _normalize_method_callable("call", "call", owner)
    assert callable(callable_ref)

    class NoDict:
        __slots__ = ()

    assert _extract_object_properties(NoDict()) == {}
    assert _extract_mapping_value({"a": 1}, ["x", "y"], 7) == 7


def test_scope_misc_remaining_branches() -> None:
    assert normalize_props_source(None) == {}
    assert normalize_props_source(SimpleNamespace(title="ok"))["title"] == "ok"

    assert normalize_state_source(None, owner=None) == {}
    assert normalize_state_source(SimpleNamespace(count=1), owner=None)["count"] == 1

    assert resolve_methods_actions(None, owner=None) == {}

    with pytest.raises(ValueError, match="Methods must be a class/object"):
        resolve_methods_actions(42, owner=SimpleNamespace())

    class ObjMethods:
        def __init__(self) -> None:
            self._hidden = lambda: {"op": "set", "state": "x", "value": 1}
            self.visible = lambda: {"op": "set", "state": "x", "value": 1}

    resolved = resolve_methods_actions(ObjMethods(), owner=SimpleNamespace())
    assert "visible" in resolved

    with pytest.raises(ValueError, match="without client instance"):
        _normalize_method_callable("visible", "visible", owner=None)

    assert swap_attribute(None, "any", 1) is None

    filtered = _extract_object_properties(SimpleNamespace(ok=1, skip=lambda: None))
    assert filtered == {"ok": 1}


def test_scope_normalize_setup_action_callable_extra_variants() -> None:
    state_backing = {"count": 2}

    def decrement(payload: Any) -> None:
        del payload
        state_backing["count"] = 1

    op_sub = _normalize_setup_action_callable("decrement", decrement, state_backing)
    assert op_sub == {"op": "sub", "state": "count", "value": 1}

    noop_state = {"enabled": True}

    def noop() -> None:
        return None

    op_noop = _normalize_setup_action_callable("noop", noop, noop_state)
    assert op_noop == {"op": "set", "state": "__noop__", "value": None}

    set_state = {"mode": "a"}

    def set_mode() -> None:
        set_state["mode"] = "b"

    op_set = _normalize_setup_action_callable("set_mode", set_mode, set_state)
    assert op_set == {"op": "set", "state": "mode", "value": "b"}


def test_scope_component_callables_and_factory_branches() -> None:
    context_fn, client_fn = resolve_component_callables({})
    assert context_fn is None
    assert client_fn is None

    source = """
class Demo(Component):
    def setup(self, props):
        return 1
"""
    scope = load_python_scope(source)
    context_fn, client_fn = resolve_component_callables(scope)
    assert callable(context_fn)
    assert callable(client_fn)
    assert context_fn({"x": 1}) == {}
    with pytest.raises(ValueError, match="must return a mapping or None"):
        client_fn({"x": 1})

    assert _build_client_factory(dict) is dict

    def factory() -> dict[str, Any]:
        return {"ok": True}

    assert _build_client_factory(factory) is factory


def test_scope_coerce_and_normalize_setup_spec_extra_paths() -> None:
    component = SimpleNamespace()
    coalesced = _coerce_setup_result(
        component,
        None,
        {"title": "x"},
        {
            "actions": {"noop": {"op": "set", "state": "x", "value": 1}},
            "lifecycle": {"mounted": "noop"},
        },
    )
    assert coalesced["actions"]["noop"]["op"] == "set"
    assert coalesced["lifecycle"]["mounted"] == "noop"

    mapped = normalize_client_spec(
        {
            "__setup_mapped__": True,
            "props": {},
            "state": {},
            "data": {},
            "actions": {"set_title": {"op": "set_prop", "prop": "title", "value": "x"}},
            "lifecycle": None,
        }
    )
    assert mapped[2]["set_title"]["op"] == "set_prop"
    assert mapped[3]["mounted"] == []

    mapped_lifecycle = normalize_client_spec(
        {
            "__setup_mapped__": True,
            "props": {},
            "state": {},
            "data": {},
            "actions": {},
            "lifecycle": {"mounted": "set_title"},
        }
    )
    assert mapped_lifecycle[3]["mounted"] == ["set_title"]

    with pytest.raises(ValueError, match="must be callable or mapping"):
        normalize_client_spec(
            {
                "__setup_mapped__": True,
                "props": {},
                "state": {},
                "data": {},
                "actions": {"bad": 1},
                "lifecycle": {},
            }
        )


def test_scope_rewire_and_state_attribute_internal_branches() -> None:
    class CallableObject:
        def __call__(self) -> dict[str, Any]:
            return {"ok": True}

    callable_obj = CallableObject()
    rewired_non_function = _rewire_callable_closure(callable_obj, {1: lambda: None})
    assert rewired_non_function is callable_obj

    def plain() -> dict[str, Any]:
        return {"ok": True}

    rewired_plain = _rewire_callable_closure(plain, {1: lambda: None})
    assert rewired_plain is plain

    def outer_with_empty_cell() -> Any:
        value = "temp"

        def inner() -> Any:
            return value

        del value
        return inner

    empty_cell_callable = outer_with_empty_cell()
    rewired_empty_cell = _rewire_callable_closure(
        empty_cell_callable, {1: lambda: None}
    )
    assert callable(rewired_empty_cell)

    def make_bound_method() -> tuple[Any, Any]:
        def dependency() -> dict[str, Any]:
            return {"source": "old"}

        def run(self: Any) -> dict[str, Any]:
            del self
            return dependency()

        return run, dependency

    run_method, dependency = make_bound_method()

    class Owner:
        run = run_method

    owner = Owner()

    def replacement() -> dict[str, Any]:
        return {"source": "new"}

    rewired_bound = _rewire_callable_closure(owner.run, {id(dependency): replacement})
    assert rewired_bound()["source"] == "new"

    class QtyType:
        name = "qty"
        from_prop = "initialQty"
        default = 1
        cast = "int"

        def init(self) -> int:
            return 1

    normalized_state = _normalize_state_attributes({"qty": QtyType})
    assert normalized_state["qty"]["cast"] == "int"
    assert "init" in normalized_state["qty"]


def test_scope_invoke_method_callable_additional_operation_shapes() -> None:
    globals_dict: dict[str, Any] = {"__builtins__": builtins}
    exec(
        "def method_with_result(self):\n"
        "    self.state.count += 1\n"
        "    return {'ok': True}\n",
        globals_dict,
    )
    method_with_result = globals_dict["method_with_result"]

    multi_result = invoke_method_callable(
        "method_with_result",
        method_with_result,
        owner=SimpleNamespace(),
    )
    assert multi_result["op"] == "multi"
    assert multi_result["steps"][-1] == {"ok": True}

    def method_single_op(self: Any) -> None:
        self.state.count += 1

    single_result = invoke_method_callable(
        "method_single_op",
        method_single_op,
        owner=SimpleNamespace(),
    )
    assert single_result["op"] == "add"

    def method_non_mapping(self: Any) -> int:
        del self
        return 1

    noop_result = invoke_method_callable(
        "method_non_mapping",
        method_non_mapping,
        owner=SimpleNamespace(),
    )
    assert noop_result == {"op": "set", "state": "__noop__", "value": None}


def test_scope_execute_server_callable_monkeypatched_edges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummyComponent:
        def setup(self, props: dict[str, Any]) -> None:
            del props
            return None

    dummy = DummyComponent()

    monkeypatch.setattr(
        scope_module, "load_python_scope", lambda _: {"__builtins__": 7}
    )
    monkeypatch.setattr(scope_module, "resolve_component_instance", lambda _: dummy)
    monkeypatch.setattr(scope_module, "_invoke_setup_with_locals", lambda *_: ({}, {}))
    monkeypatch.setattr(
        scope_module,
        "_coerce_setup_result",
        lambda *_: {"state": {}, "data": {}, "actions": {}, "lifecycle": {}},
    )

    patch = execute_setup_server_callable("ignored", "lifecycle", "mounted", {}, {})
    assert patch == {"state": {}, "props": {}}

    class WeirdMapping:
        def __init__(self, payload: dict[str, Any]) -> None:
            self._payload = payload

        def __getitem__(self, key: str) -> Any:
            return self._payload[key]

        def __iter__(self) -> Any:
            return iter(self._payload)

        def __len__(self) -> int:
            return len(self._payload)

        def get(self, key: str, default: Any = None) -> Any:
            return self._payload.get(key, default)

    monkeypatch.setattr(
        scope_module,
        "_coerce_setup_result",
        lambda *_: WeirdMapping(
            {"state": {}, "data": {}, "actions": 1, "lifecycle": {}}
        ),
    )
    with pytest.raises(ValueError, match=r"setup\(\)\.actions must be a mapping"):
        execute_setup_server_callable("ignored", "action", "run", {}, {})

    monkeypatch.setattr(
        scope_module,
        "_coerce_setup_result",
        lambda *_: WeirdMapping(
            {"state": {}, "data": {}, "actions": {}, "lifecycle": 1}
        ),
    )
    with pytest.raises(ValueError, match=r"setup\(\)\.lifecycle must be a mapping"):
        execute_setup_server_callable("ignored", "lifecycle", "mounted", {}, {})

    monkeypatch.setattr(
        scope_module,
        "_coerce_setup_result",
        lambda *_: WeirdMapping(
            {
                "state": {},
                "data": {},
                "actions": 1,
                "lifecycle": {"mounted": "run", "updated": ["run"]},
            }
        ),
    )
    with pytest.raises(ValueError, match=r"setup\(\)\.actions must be a mapping"):
        execute_setup_server_callable("ignored", "lifecycle", "mounted", {}, {})

    list_patch = execute_setup_server_callable(
        "ignored", "lifecycle", "updated", {}, {}
    )
    assert list_patch == {"state": {}, "props": {}}


def test_scope_execute_setup_server_callable_typeerror_fallback_paths() -> None:
    source = """
class Demo(Component):
    def setup(self, props):
        state = {"runs": 0}

        def needs_payload(payload):
            state["runs"] += 1
            return {"payload_is_none": payload is None}

        return {
            "props": props,
            "state": state,
            "data": {},
            "actions": {"needs_payload": needs_payload, "raw": 1},
            "lifecycle": {"mounted": needs_payload},
        }
"""

    action_patch = execute_setup_server_callable(
        source,
        kind="action",
        name="needs_payload",
        props={},
        state={},
    )
    lifecycle_patch = execute_setup_server_callable(
        source,
        kind="lifecycle",
        name="mounted",
        props={},
        state={},
    )

    assert action_patch["state"]["runs"] == 1
    assert action_patch["props"]["payload_is_none"] is True
    assert lifecycle_patch["state"]["runs"] == 1
    assert lifecycle_patch["props"]["payload_is_none"] is True
