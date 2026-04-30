"""Execution scope for component Python code with safe built-in access and spec normalization.

This module loads and executes component Python blocks in a restricted environment,
then inspects and normalizes the resulting client specs (props, state, actions, lifecycle).
"""

from __future__ import annotations

import builtins
from typing import Any, Mapping

from lua_spa.types import Component, ComponentDefinition, StateField
from lua_spa.trace import _CastReference, _PropReference, _TraceProps, _TraceState, _py_bool, _py_float, _py_int, _py_str

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
    """Extract context() and client() callables from the component.

    Returns a (context_factory, client_factory) tuple. Looks for top-level
    context() and client() functions, or methods on a component instance.
    Raises ValueError if the callables are not actually callable.
    """
    context_factory = local_scope.get("context")
    client_factory = local_scope.get("client")

    component_instance = resolve_component_instance(local_scope)
    if component_instance is not None:
        method_context = getattr(component_instance, "context", None)
        if callable(method_context):
            context_factory = method_context

        client_attr = getattr(component_instance, "client", None)
        if client_attr is not None:
            client_factory = _build_client_factory(client_attr)

        method_client = getattr(component_instance, "client", None)
        if callable(method_client):
            client_factory = method_client

    if context_factory is not None and not callable(context_factory):
        raise ValueError("Component python block must define callable context(props)")
    if client_factory is not None and not callable(client_factory):
        raise ValueError("Component python block must define callable client()")

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


def normalize_client_spec(raw_spec: Any) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, list[str]]]:
    """Normalize a client spec into (props, state, actions, lifecycle) dicts.

    Inspects a client instance or class and extracts:
    - props: public class/instance attributes (non-callable, non-reserved)
    - state: list of StateField-like objects or State attribute
    - actions/methods: public methods (excluding lifecycle and reserved names)
    - lifecycle: onCreate, onMount, onUpdate, onUnmount hooks

    Returns empty dicts if raw_spec is None. Raises ValueError if format is invalid.
    """
    if raw_spec is None:
        return {}, {}, {}, {"onCreate": [], "onMount": [], "onUpdate": [], "onUnmount": []}

    if isinstance(raw_spec, Mapping):
        props_spec = normalize_props_source(_extract_mapping_value(raw_spec, ["props", "Props"], {}))
        state_spec = normalize_state_source(_extract_mapping_value(raw_spec, ["state", "State"], {}), owner=None)
        actions_spec = _extract_mapping_value(raw_spec, ["actions", "methods"], {})
        methods_spec = _extract_mapping_value(raw_spec, ["Methods"], None)
        lifecycle_spec_raw = _extract_mapping_value(raw_spec, ["lifecycle", "Lifecycle"], {})

        if not isinstance(actions_spec, Mapping):
            raise ValueError("client().actions must be a mapping")

        normalized_actions = dict(actions_spec)
        if methods_spec is not None:
            normalized_actions.update(resolve_methods_actions(methods_spec, owner=None))

        lifecycle_spec = normalize_lifecycle_spec(lifecycle_spec_raw)
        return props_spec, state_spec, normalized_actions, lifecycle_spec

    props_spec: dict[str, Any] = {}
    state_spec: dict[str, Any] = {}
    actions_spec: dict[str, Any] = {}
    lifecycle_spec: dict[str, list[str]] = {
        "onCreate": [],
        "onMount": [],
        "onUpdate": [],
        "onUnmount": [],
    }

    props_attr = getattr(raw_spec, "Props", None)
    if props_attr is None:
        lower_props_attr = getattr(raw_spec, "props", None)
        if lower_props_attr is not None and not callable(lower_props_attr):
            props_spec = normalize_props_source(lower_props_attr)
        else:
            props_spec = _extract_object_properties(raw_spec)
    else:
        props_spec = normalize_props_source(props_attr)

    props_method = getattr(raw_spec, "props", None)
    if callable(props_method):
        method_props = props_method()
        props_spec = normalize_props_source(method_props)

    state_attr = getattr(raw_spec, "State", None)
    if state_attr is None:
        lower_state_attr = getattr(raw_spec, "state", None)
        if lower_state_attr is not None and not callable(lower_state_attr):
            state_attr = lower_state_attr
    state_spec = normalize_state_source(state_attr, owner=raw_spec)
    state_method = getattr(raw_spec, "state", None)
    if callable(state_method):
        method_state = state_method()
        state_spec = normalize_state_source(method_state, owner=raw_spec)

    actions_method = getattr(raw_spec, "actions", None)
    if callable(actions_method):
        method_actions = actions_method()
        if method_actions is None:
            method_actions = {}
        if not isinstance(method_actions, Mapping):
            raise ValueError("client().actions() must return a mapping")
        actions_spec.update(dict(method_actions))

    methods_method = getattr(raw_spec, "methods", None)
    if callable(methods_method):
        method_actions = methods_method()
        if method_actions is None:
            method_actions = {}
        if not isinstance(method_actions, Mapping):
            raise ValueError("client().methods() must return a mapping")
        actions_spec.update(dict(method_actions))

    methods_attr = getattr(raw_spec, "Methods", None)
    if methods_attr is None:
        lower_methods_attr = getattr(raw_spec, "methods", None)
        if lower_methods_attr is not None and not callable(lower_methods_attr):
            methods_attr = lower_methods_attr
    if methods_attr is not None:
        actions_spec.update(resolve_methods_actions(methods_attr, owner=raw_spec))
    else:
        inferred_methods = infer_action_methods(raw_spec)
        if len(inferred_methods) > 0:
            actions_spec.update(resolve_methods_actions(inferred_methods, owner=raw_spec))

    lifecycle_attr = getattr(raw_spec, "Lifecycle", None)
    if lifecycle_attr is None:
        lower_lifecycle_attr = getattr(raw_spec, "lifecycle", None)
        if lower_lifecycle_attr is not None and not callable(lower_lifecycle_attr):
            lifecycle_attr = lower_lifecycle_attr
    if lifecycle_attr is not None:
        lifecycle_spec = normalize_lifecycle_spec(lifecycle_attr)

    lifecycle_method = getattr(raw_spec, "lifecycle", None)
    if callable(lifecycle_method):
        lifecycle_spec = normalize_lifecycle_spec(lifecycle_method())

    method_lifecycle = normalize_lifecycle_methods(raw_spec)
    for hook_name, action_names in method_lifecycle.items():
        lifecycle_spec[hook_name] = action_names

    return props_spec, state_spec, actions_spec, lifecycle_spec


def normalize_props_source(raw_props: Any) -> dict[str, Any]:
    """Normalize props source (class, instance, or mapping) into a dict."""
    if raw_props is None:
        return {}
    if isinstance(raw_props, Mapping):
        return dict(raw_props)
    if isinstance(raw_props, type):
        return _extract_class_properties(raw_props)
    if hasattr(raw_props, "__dict__"):
        return _extract_object_properties(raw_props)
    raise ValueError("client().props must be mapping or object with public variables")


def normalize_state_source(raw_state: Any, owner: Any | None) -> dict[str, Any]:
    """Normalize state source (list, mapping, or class) into a state dict.

    Each state item becomes a dict with keys: name, from_prop, default, cast, (init).
    Raises ValueError if format is invalid.
    """
    if raw_state is None:
        return {}

    if isinstance(raw_state, Mapping):
        return dict(raw_state)

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

    raise ValueError("State must be a mapping or a list of state classes")


def normalize_state_item(item: Any, owner: Any | None) -> dict[str, Any]:
    """Normalize a single state item (dict, StateField, or class) into a spec dict.

    Returns a dict with keys: name, from_prop, default, cast, (init).
    Raises ValueError if the item is malformed.
    """
    if isinstance(item, Mapping):
        name = item.get("name")
        if not isinstance(name, str) or name.strip() == "":
            raise ValueError("State item mapping must include a string 'name'")
        result = {
            "name": name,
            "from_prop": item.get("from_prop"),
            "default": item.get("default"),
            "cast": str(item.get("cast", "raw")),
        }
        if "init" in item and callable(item.get("init")):
            result["init"] = item.get("init")
        return result

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
        for action_name, action_callable in methods_spec.items():
            action_name_str = str(action_name)
            if isinstance(action_callable, Mapping):
                resolved[action_name_str] = action_callable
                continue
            callable_ref = _normalize_method_callable(action_name_str, action_callable, owner)
            resolved[action_name_str] = invoke_method_callable(action_name_str, callable_ref, owner)
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

    raise ValueError("Methods must be a mapping of callables or a list of method names")


def _normalize_method_callable(action_name: str, candidate: Any, owner: Any | None) -> Any:
    """Resolve a method callable reference into an actual callable.

    If candidate is already callable, return it. If it's a string, look it up
    on owner. Raises ValueError if not found or not callable.
    """
    if callable(candidate):
        return candidate

    if isinstance(candidate, str):
        if owner is None:
            raise ValueError(f"Methods entry '{action_name}' references a name without client instance")
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
    try:
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
        if restore_state is not None:
            restore_state()
        if restore_props is not None:
            restore_props()

    # If method returns a mapping, use it as the operation
    if result is not None:
        if isinstance(result, Mapping):
            return result
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


def normalize_lifecycle_spec(raw_lifecycle: Any) -> dict[str, list[str]]:
    """Normalize a lifecycle mapping into canonical hook names and action lists.

    Accepts a mapping with keys like "onCreate", "created", "on_create" etc.,
    normalizing them to the canonical forms: onCreate, onMount, onUpdate, onUnmount.
    Raises ValueError if not a mapping.
    """
    normalized: dict[str, list[str]] = {
        "onCreate": [],
        "onMount": [],
        "onUpdate": [],
        "onUnmount": [],
    }

    if raw_lifecycle is None:
        return normalized
    if not isinstance(raw_lifecycle, Mapping):
        raise ValueError("client().lifecycle must be a mapping")

    for key, value in raw_lifecycle.items():
        hook_name = canonical_lifecycle_name(str(key))
        normalized[hook_name] = normalize_action_names(value)

    return normalized


def normalize_lifecycle_methods(owner: Any) -> dict[str, list[str]]:
    """Extract lifecycle method names from a client instance.

    Looks for methods like created(), mounted(), on_create(), etc.,
    normalizing to onCreate, onMount, onUpdate, onUnmount.
    Returns a dict mapping hook name to list of action names returned by the method.
    """
    mapping = {
        "created": "onCreate",
        "on_create": "onCreate",
        "onCreate": "onCreate",
        "mounted": "onMount",
        "on_mount": "onMount",
        "onMount": "onMount",
        "updated": "onUpdate",
        "on_update": "onUpdate",
        "onUpdate": "onUpdate",
        "unmounted": "onUnmount",
        "on_unmount": "onUnmount",
        "onUnmount": "onUnmount",
    }
    normalized: dict[str, list[str]] = {}

    for method_name, hook_name in mapping.items():
        candidate = getattr(owner, method_name, None)
        if not callable(candidate):
            continue
        normalized[hook_name] = normalize_action_names(candidate())

    return normalized


def canonical_lifecycle_name(name: str) -> str:
    """Normalize a lifecycle hook name to a canonical form.

    Accepts variations like "onCreate", "created", "on_create" etc.
    Returns one of: onCreate, onMount, onUpdate, onUnmount.
    Raises ValueError for unknown names.
    """
    lowered = name.replace("_", "").replace("-", "").lower()
    if lowered in {"oncreate", "create", "created"}:
        return "onCreate"
    if lowered in {"onmount", "mount"}:
        return "onMount"
    if lowered in {"onupdate", "update"}:
        return "onUpdate"
    if lowered in {"onunmount", "unmount", "destroy"}:
        return "onUnmount"
    raise ValueError(f"Unknown lifecycle hook: {name}")


def normalize_action_names(raw_value: Any) -> list[str]:
    """Normalize a value into a list of action name strings.

    Accepts None (empty list), a single string, or a list/tuple of strings.
    Raises ValueError if not one of these formats.
    """
    if raw_value is None:
        return []
    if isinstance(raw_value, str):
        return [raw_value]
    if isinstance(raw_value, (list, tuple)):
        result: list[str] = []
        for item in raw_value:
            if not isinstance(item, str):
                raise ValueError("Lifecycle action names must be strings")
            result.append(item)
        return result
    raise ValueError("Lifecycle hook value must be string or list of strings")


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
