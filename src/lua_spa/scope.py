"""Execution scope for component Python code with safe built-in access and spec normalization.

This module loads and executes component Python blocks in a restricted environment,
then inspects and normalizes the resulting client specs (props, state, actions, lifecycle).
"""

from __future__ import annotations

import builtins
import sys
from types import FunctionType
from typing import Any, Mapping

from lua_spa.trace import (
    _py_bool,
    _py_float,
    _py_int,
    _py_str,
    _TraceProps,
    _TraceState,
)
from lua_spa.types import Component, StateField

_CLIENT_RESERVED_NAMES = {
    "Props",
    "State",
    "Methods",
    "Lifecycle",
    "props",
    "state",
    "methods",
    "actions",
    "lifecycle",
}

_LIFECYCLE_HOOK_NAMES = {
    "created",
    "mounted",
    "updated",
    "unmounted",
}


def load_python_scope(python_block: str) -> dict[str, Any]:
    """Execute a component's Python block with full Python access.

    Returns a dict with the executed namespace. If python_block is empty,
    returns an empty dict. Supports unrestricted imports and all built-in functions.
    """
    if python_block.strip() == "":
        return {}

    builtin_overrides: dict[str, Any] = {
        "int": _py_int,
        "float": _py_float,
        "str": _py_str,
        "bool": _py_bool,
    }
    full_builtins = {**vars(builtins), **builtin_overrides}

    shared_scope: dict[str, Any] = {
        "__builtins__": full_builtins,
        "__name__": "__lspa_component__",
        "ClientMethods": Component,  # Alias for backwards compatibility
        "Client": Component,
        "Component": Component,
        "StateField": StateField,
    }
    exec(python_block, shared_scope, shared_scope)  # noqa: S102
    shared_scope["__print_ref__"] = None  # placeholder for print injection
    return shared_scope


def resolve_component_instance(local_scope: Mapping[str, Any]) -> Any | None:
    """Extract a component instance from the executed scope.

    Looks for: component() callable, explicit Component subclass, or inferred
    Component subclass. Returns the instantiated component or None if not found.
    Raises ValueError if instantiation fails.
    """
    component_factory = local_scope.get("component")
    if component_factory is not None and callable(component_factory):
        try:
            return component_factory()
        except TypeError as error:
            raise ValueError("component() must be callable without arguments") from error

    explicit_component = local_scope.get("Component")
    if isinstance(explicit_component, type) and explicit_component is not Component:
        try:
            return explicit_component()
        except TypeError as error:
            raise ValueError("Component class must be instantiable without arguments") from error

    concrete_components: list[type[Any]] = []
    for value in local_scope.values():
        if not isinstance(value, type):
            continue
        if value is Component:
            continue
        if issubclass(value, Component):
            concrete_components.append(value)

    if len(concrete_components) > 0:
        component_class = concrete_components[-1]
        try:
            return component_class()
        except TypeError as error:
            raise ValueError("Component subclass must be instantiable without arguments") from error

    return None


def resolve_component_callables(local_scope: Mapping[str, Any]) -> tuple[Any | None, Any | None]:
    """Extract setup-derived context/client factories from a Component instance.

    Returns a (context_factory, client_factory) tuple created from
    `Component.setup(self, props)`. Legacy styles (top-level setup/context/client)
    are not supported.
    """
    context_factory = None
    client_factory = None

    component_instance = resolve_component_instance(local_scope)
    if component_instance is None:
        if len(local_scope) == 0:
            return None, None
        raise ValueError(
            "Component python block must define a Component subclass with setup(self, props)"
        )

    method_setup = getattr(component_instance, "setup", None)
    if not callable(method_setup):
        raise ValueError(
            "Component python block must define setup(self, props); context()/client()/top-level setup are not supported"
        )

    def _context_from_setup(props: Any) -> Any:
        setup_props = dict(props) if isinstance(props, Mapping) else {}
        try:
            setup_result_raw, setup_locals = _invoke_setup_with_locals(method_setup, setup_props)
            setup_result = _coerce_setup_result(
                component_instance,
                setup_result_raw,
                setup_props,
                setup_locals,
            )
        except ValueError:
            return {}
        if isinstance(setup_result, Mapping):
            setup_data = setup_result.get("data", {})
            if isinstance(setup_data, Mapping):
                return setup_data
        return {}

    def _client_from_setup(props: Any | None = None) -> Any:
        setup_props = dict(props) if isinstance(props, Mapping) else {}
        setup_result_raw, setup_locals = _invoke_setup_with_locals(method_setup, setup_props)
        setup_result = _coerce_setup_result(
            component_instance,
            setup_result_raw,
            setup_props,
            setup_locals,
        )
        if not isinstance(setup_result, Mapping):
            raise ValueError(
                "setup(self, props) must return a mapping or set component props/state/data/actions/lifecycle attributes"
            )
        mapped_result = dict(setup_result)
        mapped_result["__setup_mapped__"] = True
        return mapped_result

    context_factory = _context_from_setup
    client_factory = _client_from_setup

    if context_factory is not None and not callable(context_factory):
        raise ValueError("Component python block must define callable setup(self, props)")
    if client_factory is not None and not callable(client_factory):
        raise ValueError("Component python block must define callable setup(self, props)")

    return context_factory, client_factory


def _build_client_factory(client_attr: Any) -> Any:
    """Wrap a client attribute or type into a factory callable.

    If client_attr is a type, return it as-is. If callable, return it.
    Otherwise, wrap it in a lambda that returns the value.
    """
    if isinstance(client_attr, type):
        return client_attr
    if callable(client_attr):
        return client_attr

    def _value_factory() -> Any:
        return client_attr

    return _value_factory


def _coerce_setup_result(
    component_instance: Any,
    setup_result: Any,
    setup_props: Mapping[str, Any],
    setup_locals: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    """Normalize setup output, supporting implicit component attribute mapping."""
    if isinstance(setup_result, Mapping):
        return setup_result

    if setup_result is not None:
        raise ValueError(
            "setup(self, props) must return a mapping or None when using component attributes"
        )

    setup_locals_map = dict(setup_locals or {})

    mapped_props = getattr(component_instance, "props", None)
    if mapped_props is None and "props" in setup_locals_map:
        mapped_props = setup_locals_map.get("props")

    mapped_state = getattr(component_instance, "state", None)
    if mapped_state is None and "state" in setup_locals_map:
        mapped_state = setup_locals_map.get("state")

    mapped_data = getattr(component_instance, "data", None)
    if mapped_data is None and "data" in setup_locals_map:
        mapped_data = setup_locals_map.get("data")

    mapped_actions = getattr(component_instance, "actions", None)
    if mapped_actions is None and "actions" in setup_locals_map:
        mapped_actions = setup_locals_map.get("actions")

    mapped_lifecycle = getattr(component_instance, "lifecycle", None)
    if mapped_lifecycle is None and "lifecycle" in setup_locals_map:
        mapped_lifecycle = setup_locals_map.get("lifecycle")

    local_callables: dict[str, Any] = {
        name: value
        for name, value in setup_locals_map.items()
        if isinstance(name, str) and not name.startswith("_") and callable(value)
    }

    inferred_lifecycle: dict[str, Any] = {}
    for callable_name, callable_ref in local_callables.items():
        if callable_name not in _LIFECYCLE_HOOK_NAMES:
            continue
        inferred_lifecycle[callable_name] = callable_ref

    if mapped_lifecycle is None:
        mapped_lifecycle = inferred_lifecycle

    if mapped_actions is None:
        mapped_actions = {
            callable_name: callable_ref
            for callable_name, callable_ref in local_callables.items()
            if callable_name not in inferred_lifecycle
        }

    return {
        "props": dict(setup_props) if mapped_props is None else mapped_props,
        "state": {} if mapped_state is None else mapped_state,
        "data": {} if mapped_data is None else mapped_data,
        "actions": {} if mapped_actions is None else mapped_actions,
        "lifecycle": {} if mapped_lifecycle is None else mapped_lifecycle,
    }


def _invoke_setup_with_locals(
    method_setup: Any,
    setup_props: Mapping[str, Any],
) -> tuple[Any, dict[str, Any]]:
    """Execute setup and capture local variables from its return frame."""
    setup_callable = getattr(method_setup, "__func__", method_setup)
    setup_code = getattr(setup_callable, "__code__", None)
    captured_locals: dict[str, Any] = {}

    previous_profile = sys.getprofile()

    def _profile(frame: Any, event: str, arg: Any) -> Any:
        if event == "return" and setup_code is not None and frame.f_code is setup_code:
            captured_locals.update(dict(frame.f_locals))
        return _profile

    sys.setprofile(_profile)
    try:
        setup_result = method_setup(dict(setup_props))
    finally:
        sys.setprofile(previous_profile)

    return setup_result, captured_locals


def normalize_context_result(result: Any) -> dict[str, Any]:
    """Normalize the return value of context(props) into a dict.

    Accepts None (returns empty dict), Mapping (converts to dict), or an object
    with __dict__ (extracts public attributes). Raises ValueError otherwise.
    """
    if result is None:
        return {}

    if isinstance(result, Mapping):
        return dict(result)

    if hasattr(result, "__dict__"):
        values = vars(result)
        return {key: value for key, value in values.items() if not str(key).startswith("_")}

    raise ValueError("context(props) must return a mapping or object with attributes")


def normalize_client_spec(
    raw_spec: Any,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, list[Any]]]:
    """Normalize a client spec into (props, state, actions, lifecycle) dicts.

    Inspects a client instance or class and extracts:
    - props: public class/instance attributes (non-callable, non-reserved)
    - state: list of StateField-like objects or State attribute
    - actions/methods: public methods (excluding lifecycle and reserved names)
    - lifecycle: created, mounted, updated, unmounted hooks

    Returns empty dicts if raw_spec is None. Raises ValueError if format is invalid.
    """
    if raw_spec is None:
        raise ValueError(
            "setup(self, props) must return a mapping with props/state/data/actions/lifecycle"
        )

    if isinstance(raw_spec, Mapping):
        if raw_spec.get("__setup_mapped__") is True:
            return _normalize_setup_spec(raw_spec)
        raise ValueError(
            "client() must return a Python object/class instance; declarative dict specs are not supported"
        )

    raise ValueError("Only setup(self, props) mapping output is supported")


def _normalize_setup_spec(
    raw_spec: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, list[Any]]]:
    """Normalize setup(self, props) mapping output into client spec tuple."""
    props_spec: dict[str, Any] = {}
    state_spec: dict[str, Any] = {}
    actions_spec: dict[str, Any] = {}
    lifecycle_spec: dict[str, list[Any]] = {
        "created": [],
        "mounted": [],
        "updated": [],
        "unmounted": [],
    }

    raw_props = raw_spec.get("props", {})
    if isinstance(raw_props, Mapping):
        props_spec = dict(raw_props)
    else:
        props_spec = normalize_props_source(raw_props)

    raw_data = raw_spec.get("data", {})
    if isinstance(raw_data, Mapping):
        for key, value in raw_data.items():
            key_name = str(key)
            if key_name not in props_spec:
                props_spec[key_name] = value

    raw_state = raw_spec.get("state", {})
    if isinstance(raw_state, Mapping):
        state_spec = dict(raw_state)
    else:
        state_spec = normalize_state_source(raw_state, owner=None)

    raw_actions = raw_spec.get("actions", {})
    if raw_actions is None:
        raw_actions = {}
    if not isinstance(raw_actions, Mapping):
        raise ValueError("setup().actions must be a mapping")

    for action_name, action_value in raw_actions.items():
        action_name_str = str(action_name)
        if callable(action_value):
            actions_spec[action_name_str] = {
                "op": "server_call",
                "kind": "action",
                "name": action_name_str,
            }
            continue
        if isinstance(action_value, Mapping):
            actions_spec[action_name_str] = dict(action_value)
            continue
        raise ValueError(f"setup().actions['{action_name_str}'] must be callable or mapping")

    raw_lifecycle = raw_spec.get("lifecycle", {})
    if raw_lifecycle is None:
        raw_lifecycle = {}
    if not isinstance(raw_lifecycle, Mapping):
        raise ValueError("setup().lifecycle must be a mapping")

    for hook_name_raw, hook_value in raw_lifecycle.items():
        hook_name = str(hook_name_raw)
        if hook_name not in _LIFECYCLE_HOOK_NAMES:
            raise ValueError(f"Unknown lifecycle hook: {hook_name_raw}")

        if callable(hook_value):
            lifecycle_spec[hook_name] = [
                {
                    "op": "server_call",
                    "kind": "lifecycle",
                    "name": str(hook_name_raw),
                }
            ]
            continue

        if isinstance(hook_value, str):
            lifecycle_spec[hook_name] = [hook_value]
            continue

        if isinstance(hook_value, Mapping):
            lifecycle_spec[hook_name] = [dict(hook_value)]
            continue

        if isinstance(hook_value, (list, tuple)):
            normalized_items: list[Any] = []
            for item in hook_value:
                if callable(item):
                    normalized_items.append(
                        {
                            "op": "server_call",
                            "kind": "lifecycle",
                            "name": str(hook_name_raw),
                        }
                    )
                    continue
                if isinstance(item, (str, Mapping)):
                    normalized_items.append(item)
                    continue
                raise ValueError(
                    "setup().lifecycle entries must be callables, strings, or mappings"
                )
            lifecycle_spec[hook_name] = normalized_items
            continue

        raise ValueError("setup().lifecycle values must be callable, string, list, or mapping")

    return props_spec, state_spec, actions_spec, lifecycle_spec


def execute_setup_server_callable(
    python_block: str,
    kind: str,
    name: str,
    props: Mapping[str, Any] | None,
    state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Execute a setup action/lifecycle callable at request time.

    Returns a patch payload containing updated state and props updates.
    """
    local_scope = load_python_scope(python_block)
    component_instance = resolve_component_instance(local_scope)
    if component_instance is None:
        raise ValueError("Component python block must define a Component subclass")

    method_setup = getattr(component_instance, "setup", None)
    if not callable(method_setup):
        raise ValueError("Component must define setup(self, props)")

    setup_props = dict(props or {})
    setup_result_raw, setup_locals = _invoke_setup_with_locals(method_setup, setup_props)
    setup_result = _coerce_setup_result(
        component_instance,
        setup_result_raw,
        setup_props,
        setup_locals,
    )

    # Inject print ref into the local scope so nested functions see changes
    if isinstance(local_scope, dict):
        local_scope["__print_ref__"] = None

    setup_state_obj = setup_result.get("state", {})
    setup_state: dict[str, Any] = (
        dict(setup_state_obj) if isinstance(setup_state_obj, Mapping) else {}
    )
    setup_data_obj = setup_result.get("data", {})

    if isinstance(state, Mapping):
        for key, value in state.items():
            key_name = str(key)
            if key_name in setup_state:
                setup_state[key_name] = value
        if isinstance(setup_state_obj, dict):
            setup_state_obj.clear()
            setup_state_obj.update(setup_state)

    props_patch: dict[str, Any] = {}
    tracked_action_results: list[Any] = []
    trace_logs: list[Any] = []
    original_print = builtins.print

    def _trace_print(*args: Any, **kwargs: Any) -> None:
        sep = kwargs.get("sep", " ")
        message = sep.join(str(item) for item in args)
        trace_logs.append(message)
        original_print(*args, **kwargs)

    def _merge_result(result: Any) -> None:
        if isinstance(result, Mapping):
            for key, value in result.items():
                props_patch[str(key)] = value

    # Inject trace_print into locals scope so nested functions use it
    if isinstance(local_scope, dict):
        builtin_ref = local_scope.get("__builtins__")
        if isinstance(builtin_ref, dict):
            builtin_ref["print"] = _trace_print
        elif hasattr(builtin_ref, "__dict__"):
            builtin_ref.__dict__["print"] = _trace_print
        else:
            try:
                setattr(builtin_ref, "print", _trace_print)
            except (TypeError, AttributeError):
                pass
        local_scope["__print_ref__"] = _trace_print

    actions_original = setup_result.get("actions", {})
    actions_for_execution: dict[str, Any] = {}
    action_replacements_by_id: dict[int, Any] = {}
    if isinstance(actions_original, Mapping):
        for action_key, action_value in actions_original.items():
            action_name = str(action_key)
            if callable(action_value):

                def _wrap_callable(fn: Any) -> Any:
                    def _wrapped(*args: Any, **kwargs: Any) -> Any:
                        old_print = builtins.print
                        builtins.print = _trace_print
                        try:
                            result = fn(*args, **kwargs)
                            tracked_action_results.append(result)
                            return result
                        finally:
                            builtins.print = old_print

                    return _wrapped

                wrapped_callable = _wrap_callable(action_value)
                actions_for_execution[action_name] = wrapped_callable
                action_replacements_by_id[id(action_value)] = wrapped_callable
            else:
                actions_for_execution[action_name] = action_value

    if isinstance(setup_result, dict):
        setup_result["actions"] = actions_for_execution

    if kind == "action":
        actions = setup_result.get("actions", {})
        if not isinstance(actions, Mapping):
            raise ValueError("setup().actions must be a mapping")
        target = actions.get(name)
        if not callable(target):
            raise ValueError(f"Unknown action: {name}")
        builtins.print = _trace_print
        try:
            result = target()
        except TypeError:
            result = target(None)
        finally:
            builtins.print = original_print
        _merge_result(result)
    elif kind == "lifecycle":
        lifecycle = setup_result.get("lifecycle", {})
        if not isinstance(lifecycle, Mapping):
            raise ValueError("setup().lifecycle must be a mapping")
        hook_value = lifecycle.get(name)
        if callable(hook_value):
            hook_callable = _rewire_callable_closure(hook_value, action_replacements_by_id)
            builtins.print = _trace_print
            try:
                result = hook_callable()
            except TypeError:
                result = hook_callable(None)
            finally:
                builtins.print = original_print
            _merge_result(result)
        elif isinstance(hook_value, str):
            actions = setup_result.get("actions", {})
            if not isinstance(actions, Mapping):
                raise ValueError("setup().actions must be a mapping")
            action_callable = actions.get(hook_value)
            if not callable(action_callable):
                raise ValueError(f"Unknown lifecycle action: {hook_value}")
            try:
                result = action_callable()
            except TypeError:
                result = action_callable(None)
            _merge_result(result)
        elif isinstance(hook_value, (list, tuple)):
            actions = setup_result.get("actions", {})
            if not isinstance(actions, Mapping):
                actions = {}
            for entry in hook_value:
                if callable(entry):
                    entry_callable = _rewire_callable_closure(entry, action_replacements_by_id)
                    try:
                        result = entry_callable()
                    except TypeError:
                        result = entry_callable(None)
                    _merge_result(result)
                    continue
                if isinstance(entry, str):
                    action_callable = actions.get(entry)
                    if callable(action_callable):
                        try:
                            result = action_callable()
                        except TypeError:
                            result = action_callable(None)
                        _merge_result(result)
        elif hook_value is not None:
            raise ValueError(f"Unsupported lifecycle hook value for {name}")
    for message in trace_logs:
        if "__lua_logs__" not in props_patch:
            props_patch["__lua_logs__"] = []
        props_patch["__lua_logs__"].append(message)

    for tracked in tracked_action_results:
        _merge_result(tracked)

    if isinstance(setup_data_obj, Mapping):
        for data_key, data_value in setup_data_obj.items():
            data_key_str = str(data_key)
            if data_key_str not in props_patch:
                props_patch[data_key_str] = data_value

    current_state = dict(setup_state_obj) if isinstance(setup_state_obj, Mapping) else setup_state
    return {
        "state": current_state,
        "props": props_patch,
    }


def _make_closure_cell(value: Any) -> Any:
    """Create a writable closure cell carrying the provided value."""
    closure = (lambda: value).__closure__
    if closure:
        return closure[0]
    return None


def _rewire_callable_closure(callable_obj: Any, replacements_by_id: Mapping[int, Any]) -> Any:
    """Replace closure callables by identity so lifecycle hooks call wrapped actions."""
    if len(replacements_by_id) == 0:
        return callable_obj

    bound_self = getattr(callable_obj, "__self__", None)
    function_obj = getattr(callable_obj, "__func__", callable_obj)
    if not isinstance(function_obj, FunctionType):
        return callable_obj

    closure = getattr(function_obj, "__closure__", None)
    if not closure:
        return callable_obj

    changed = False
    new_cells: list[Any] = []
    for cell in closure:
        try:
            cell_value = cell.cell_contents
        except ValueError:
            new_cells.append(cell)
            continue

        replacement = replacements_by_id.get(id(cell_value))
        if replacement is None:
            new_cells.append(cell)
            continue

        new_cells.append(_make_closure_cell(replacement))
        changed = True

    if not changed:
        return callable_obj

    rewired = FunctionType(
        function_obj.__code__,
        function_obj.__globals__,
        name=function_obj.__name__,
        argdefs=function_obj.__defaults__,
        closure=tuple(new_cells),
    )
    rewired.__kwdefaults__ = function_obj.__kwdefaults__
    rewired.__annotations__ = getattr(function_obj, "__annotations__", {})
    rewired.__dict__.update(getattr(function_obj, "__dict__", {}))

    if bound_self is not None:
        return rewired.__get__(bound_self, type(bound_self))
    return rewired


def _normalize_setup_action_callable(
    action_name: str,
    action_callable: Any,
    state_backing: dict[str, Any],
) -> dict[str, Any]:
    """Execute setup action callable once and convert effects to action operations."""
    before_state = dict(state_backing)

    try:
        result = action_callable()
    except TypeError:
        result = action_callable(None)

    after_state = dict(state_backing)

    # Restore setup state backing so one action does not affect others during normalization.
    state_backing.clear()
    state_backing.update(before_state)

    steps: list[dict[str, Any]] = []

    for state_name, before_value in before_state.items():
        after_value = after_state.get(state_name)
        if after_value != before_value:
            if isinstance(before_value, (int, float)) and isinstance(after_value, (int, float)):
                delta = after_value - before_value
                if delta > 0:
                    steps.append({"op": "add", "state": str(state_name), "value": delta})
                    continue
                if delta < 0:
                    steps.append({"op": "sub", "state": str(state_name), "value": abs(delta)})
                    continue
            steps.append({"op": "set", "state": str(state_name), "value": after_value})

    if isinstance(result, Mapping):
        for key, value in result.items():
            steps.append({"op": "set_prop", "prop": str(key), "value": value})

    if len(steps) == 0:
        return {"op": "set", "state": "__noop__", "value": None}

    if len(steps) == 1:
        return steps[0]

    return {"op": "multi", "steps": steps}


def normalize_props_source(raw_props: Any) -> dict[str, Any]:
    """Normalize props source (class, instance, or mapping) into a dict."""
    if raw_props is None:
        return {}
    if isinstance(raw_props, Mapping):
        raise ValueError(
            "Declarative props dicts are not supported. Use a Props class or props() returning an object"
        )
    if isinstance(raw_props, type):
        return _extract_class_properties(raw_props)
    if hasattr(raw_props, "__dict__"):
        return _extract_object_properties(raw_props)
    raise ValueError("client().props must be a class or object with public variables")


def normalize_state_source(raw_state: Any, owner: Any | None) -> dict[str, Any]:
    """Normalize state source (list, mapping, or class) into a state dict.

    Each state item becomes a dict with keys: name, from_prop, default, cast, (init).
    Raises ValueError if format is invalid.
    """
    if raw_state is None:
        return {}

    if isinstance(raw_state, Mapping):
        raise ValueError(
            "Declarative state dicts are not supported. Use a State class/object or a list of StateField/classes"
        )

    if isinstance(raw_state, type):
        return _normalize_state_attributes(_extract_class_properties(raw_state))

    if hasattr(raw_state, "__dict__"):
        return _normalize_state_attributes(_extract_object_properties(raw_state))

    if isinstance(raw_state, (list, tuple, set)):
        normalized: dict[str, Any] = {}
        for item in raw_state:
            state_item = normalize_state_item(item, owner=owner)
            normalized[state_item["name"]] = {
                "from_prop": state_item["from_prop"],
                "default": state_item["default"],
                "cast": state_item["cast"],
            }
            if "init" in state_item:
                normalized[state_item["name"]]["init"] = state_item["init"]
        return normalized

    raise ValueError("State must be a class/object or a list of StateField/classes")


def _normalize_state_attributes(values: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize class/object state attributes into a state spec mapping."""
    normalized: dict[str, Any] = {}
    for name, value in values.items():
        if isinstance(value, StateField):
            normalized_name = (
                value.name if isinstance(value.name, str) and value.name.strip() != "" else name
            )
            normalized[normalized_name] = {
                "from_prop": value.from_prop,
                "default": value.default,
                "cast": value.cast,
            }
            continue
        if isinstance(value, type):
            state_item = normalize_state_item(value, owner=None)
            normalized[state_item["name"]] = {
                "from_prop": state_item["from_prop"],
                "default": state_item["default"],
                "cast": state_item["cast"],
            }
            if "init" in state_item:
                normalized[state_item["name"]]["init"] = state_item["init"]
            continue
        normalized[name] = value
    return normalized


def normalize_state_item(item: Any, owner: Any | None) -> dict[str, Any]:
    """Normalize a single state item (dict, StateField, or class) into a spec dict.

    Returns a dict with keys: name, from_prop, default, cast, (init).
    Raises ValueError if the item is malformed.
    """
    if isinstance(item, Mapping):
        raise ValueError("State list items cannot be dicts. Use StateField or state classes")

    if isinstance(item, StateField):
        return {
            "name": item.name,
            "from_prop": item.from_prop,
            "default": item.default,
            "cast": item.cast,
        }

    state_source = item
    if isinstance(item, str):
        if owner is None:
            raise ValueError("String state items require a client instance")
        state_source = getattr(owner, item, None)
        if state_source is None:
            raise ValueError(f"Unknown state class reference: {item}")

    if isinstance(state_source, type):
        try:
            state_source = state_source()
        except TypeError as error:
            raise ValueError("State classes must be instantiable without arguments") from error

    name = getattr(state_source, "name", None)
    if not isinstance(name, str) or name.strip() == "":
        raise ValueError("State class must define a string 'name' attribute")

    cast_value = getattr(state_source, "cast", "raw")
    result = {
        "name": name,
        "from_prop": getattr(state_source, "from_prop", None),
        "default": getattr(state_source, "default", None),
        "cast": str(cast_value),
    }
    init_candidate = getattr(state_source, "init", None)
    if callable(init_candidate):
        result["init"] = init_candidate
    return result


def resolve_methods_actions(methods_spec: Any, owner: Any | None) -> dict[str, Any]:
    """Resolve a methods spec (mapping, list, or names) into action operation dicts.

    If methods_spec is a mapping: value callables are invoked to get operation dicts.
    If methods_spec is a list of strings: methods are looked up on owner and invoked.
    Raises ValueError if format is invalid or methods can't be found.
    """
    resolved: dict[str, Any] = {}

    if methods_spec is None:
        return resolved

    if isinstance(methods_spec, Mapping):
        raise ValueError(
            "methods/actions mappings are not supported. Use methods list (names) or methods objects/classes"
        )

    if isinstance(methods_spec, type):
        for action_name, action_callable in vars(methods_spec).items():
            if action_name.startswith("_"):
                continue
            callable_ref = _normalize_method_callable(action_name, action_callable, owner)
            resolved[action_name] = invoke_method_callable(action_name, callable_ref, owner)
        return resolved

    if hasattr(methods_spec, "__dict__") and not isinstance(methods_spec, str):
        for action_name, action_callable in vars(methods_spec).items():
            if action_name.startswith("_"):
                continue
            callable_ref = _normalize_method_callable(action_name, action_callable, owner)
            resolved[action_name] = invoke_method_callable(action_name, callable_ref, owner)
        return resolved

    if isinstance(methods_spec, (list, tuple, set)):
        for item in methods_spec:
            if not isinstance(item, str):
                raise ValueError("Methods iterable must contain method names as strings")
            if owner is None:
                raise ValueError("Methods names require a client object instance")
            method_ref = getattr(owner, item, None)
            if not callable(method_ref):
                raise ValueError(f"Methods references unknown callable: {item}")
            resolved[item] = invoke_method_callable(item, method_ref, owner)
        return resolved

    raise ValueError("Methods must be a class/object of callables or a list of method names")


def _normalize_method_callable(action_name: str, candidate: Any, owner: Any | None) -> Any:
    """Resolve a method callable reference into an actual callable.

    If candidate is already callable, return it. If it's a string, look it up
    on owner. Raises ValueError if not found or not callable.
    """
    if callable(candidate):
        return candidate

    if isinstance(candidate, str):
        if owner is None:
            raise ValueError(
                f"Methods entry '{action_name}' references a name without client instance"
            )
        method_ref = getattr(owner, candidate, None)
        if callable(method_ref):
            return method_ref

    raise ValueError(f"Methods entry '{action_name}' must be a callable function")


def invoke_method_callable(action_name: str, method_callable: Any, owner: Any | None) -> Any:
    """Invoke a method callable with full Python execution, capturing state mutations.

    Executes the method with tracing proxies to record state mutations. Allows
    arbitrary Python code including conditionals, loops, etc. If the method
    returns a mapping, that's the operation. Otherwise, returns the traced operations.

    If no operations are traced and no return value is provided, returns an empty
    operation (no-op).
    """
    trace_state = _TraceState()
    props_proxy = _TraceProps()

    restore_props = swap_attribute(owner, "props", props_proxy) if owner is not None else None
    restore_state = swap_attribute(owner, "state", trace_state) if owner is not None else None

    result = None
    trace_logs: list[Any] = []
    original_print = builtins.print
    original_globals_print = None
    globals_builtins = None

    def _trace_print(*args: Any, **kwargs: Any) -> None:
        sep = kwargs.get("sep", " ")
        message = sep.join(str(item) for item in args)
        trace_logs.append(message)
        original_print(*args, **kwargs)

    try:
        builtins.print = _trace_print
        globals_builtins = getattr(method_callable, "__globals__", {}).get("__builtins__")
        if isinstance(globals_builtins, dict):
            original_globals_print = globals_builtins.get("print", builtins.print)
            globals_builtins["print"] = _trace_print
        elif globals_builtins is not None:
            original_globals_print = getattr(globals_builtins, "print", builtins.print)
            setattr(globals_builtins, "print", _trace_print)
        # Try calling without arguments first (for unbound functions)
        try:
            result = method_callable()
        except TypeError:
            # If that fails, try calling with owner as self (for bound methods)
            try:
                result = method_callable(owner)
            except TypeError:
                # If both fail, just skip (method might be bound already)
                pass
    finally:
        builtins.print = original_print
        if globals_builtins is not None and original_globals_print is not None:
            if isinstance(globals_builtins, dict):
                globals_builtins["print"] = original_globals_print
            else:
                setattr(globals_builtins, "print", original_globals_print)
        if restore_state is not None:
            restore_state()
        if restore_props is not None:
            restore_props()

    for message in trace_logs:
        trace_state.add_log(message)

    # If method returns a mapping, use it as the operation
    if result is not None:
        if isinstance(result, Mapping):
            if len(trace_state.operations) == 0:
                return result
            return {"op": "multi", "steps": [*trace_state.operations, result]}
        # If result is truthy but not a mapping, treat as no-op
        return {"op": "set", "state": "__noop__", "value": None}

    # If no result, return traced operations
    if len(trace_state.operations) == 0:
        # No operations traced - return a no-op that doesn't break the client
        return {"op": "set", "state": "__noop__", "value": None}

    if len(trace_state.operations) == 1:
        return trace_state.operations[0]

    return {"op": "multi", "steps": trace_state.operations}


def swap_attribute(owner: Any | None, attribute_name: str, replacement: Any) -> Any | None:
    """Temporarily swap an attribute on owner, returning a restore function.

    If owner is None, returns None. Otherwise returns a callable that restores
    the original value (or deletes if it wasn't present).
    """
    if owner is None:
        return None

    sentinel = object()
    original = getattr(owner, attribute_name, sentinel)
    setattr(owner, attribute_name, replacement)

    def restore() -> None:
        if original is sentinel:
            delattr(owner, attribute_name)
            return
        setattr(owner, attribute_name, original)

    return restore


def infer_action_methods(owner: Any) -> list[str]:
    """Infer action method names from a client instance.

    Returns a list of public, callable attributes (non-reserved, non-lifecycle).
    """
    excluded = {
        "add",
        "sub",
        "set",
        "toggle",
        "created",
        "mounted",
        "updated",
        "unmounted",
        "on_create",
        "on_mount",
        "on_update",
        "on_unmount",
        "context",
        "client",
        "state",
        "props",
        "actions",
        "methods",
        "lifecycle",
    }
    result: list[str] = []

    for name in dir(owner):
        if name.startswith("_") or name in excluded:
            continue
        if name in _CLIENT_RESERVED_NAMES:
            continue

        value = getattr(owner, name)
        if isinstance(value, type):
            continue
        if callable(value):
            result.append(name)

    return result


def _extract_class_properties(source_class: type[Any]) -> dict[str, Any]:
    """Extract public, non-callable class attributes.

    Skips private attrs (starting with _) and reserved names.
    """
    result: dict[str, Any] = {}
    for name, value in vars(source_class).items():
        if name.startswith("_") or name in _CLIENT_RESERVED_NAMES:
            continue
        if callable(value):
            continue
        result[name] = value
    return result


def _extract_object_properties(source_object: Any) -> dict[str, Any]:
    """Extract public, non-callable attributes from an instance or class.

    Combines class properties with instance __dict__ attributes.
    """
    result = _extract_class_properties(type(source_object))
    try:
        instance_values = vars(source_object)
    except TypeError:
        instance_values = {}

    for name, value in instance_values.items():
        if name.startswith("_") or name in _CLIENT_RESERVED_NAMES:
            continue
        if callable(value):
            continue
        result[name] = value

    return result


def _extract_mapping_value(source: Mapping[str, Any], keys: list[str], default: Any) -> Any:
    """Return the first value from source[key] for key in keys, or default."""
    for key in keys:
        if key in source:
            return source[key]
    return default
