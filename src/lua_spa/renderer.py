"""Server-side template rendering, interpolation, and conditional evaluation.

Converts component templates with {{ }} expressions and l-if attributes
into HTML by evaluating expressions in the context of props, state, and py objects.
"""

from __future__ import annotations

import re
from types import SimpleNamespace
from typing import Any, Mapping

_EXPR_PATTERN = re.compile(r"{{\s*(.*?)\s*}}")


def build_scoped_context(context: Mapping[str, Any]) -> dict[str, Any]:
    """Build a scoped dict for expression evaluation.

    Combines props, state, and py into a flat namespace and nested objects.
    This allows {{ count }} and {{ state.count }} to both work.

    Args:
        context: Dict with "props", "state", "py" keys (each a mapping).

    Returns:
        A dict for use in eval() with all accessible variables.
    """
    props_map = dict(context.get("props", {}))
    state_map = dict(context.get("state", {}))
    py_map = dict(context.get("py", {}))

    scoped: dict[str, Any] = {
        "props": to_namespace(props_map),
        "state": to_namespace(state_map),
        "py": to_namespace(py_map),
    }

    flat_context: dict[str, Any] = {}
    for source in [props_map, py_map, state_map]:
        for key, value in source.items():
            if isinstance(key, str):
                flat_context[key] = value

    for key, value in flat_context.items():
        if key in {"props", "state", "py"}:
            continue
        scoped[key] = to_namespace(value)

    return scoped


def to_namespace(value: Any) -> Any:
    """Recursively convert dicts and sequences to SimpleNamespace for dot access.

    Allows {{ obj.prop }} to work on nested dicts by converting them to
    SimpleNamespace so getattr() works.

    Args:
        value: A dict, list, tuple, or scalar.

    Returns:
        A SimpleNamespace (for Mapping), list, tuple, or scalar.
    """
    if isinstance(value, Mapping):
        data = {key: to_namespace(item) for key, item in value.items()}
        return SimpleNamespace(**data)
    if isinstance(value, list):
        return [to_namespace(item) for item in value]
    if isinstance(value, tuple):
        return tuple(to_namespace(item) for item in value)
    return value


def evaluate_expression(expression: str, context: Mapping[str, Any]) -> Any:
    """Evaluate a Python expression in the component context.

    Args:
        expression: A Python expression string, e.g. "count > 5".
        context: Dict with "props", "state", "py" keys.

    Returns:
        The result of eval(), or None if evaluation fails.
    """
    scoped = build_scoped_context(context)
    try:
        return eval(expression, {"__builtins__": {}}, scoped)  # noqa: S307
    except Exception:
        return None


def interpolate(template: str, context: Mapping[str, Any]) -> str:
    """Replace {{ expression }} with evaluated values.

    Args:
        template: HTML with {{ }} interpolations.
        context: Dict with "props", "state", "py" keys.

    Returns:
        HTML with expressions replaced by their string values.
    """
    scoped = build_scoped_context(context)

    def replace_expression(match: re.Match[str]) -> str:
        expression = match.group(1)
        try:
            value = eval(expression, {"__builtins__": {}}, scoped)  # noqa: S307
        except Exception:
            return ""
        if value is None:
            return ""
        return str(value)

    return _EXPR_PATTERN.sub(replace_expression, template)


def apply_server_conditionals(template: str, context: Mapping[str, Any]) -> str:
    """Remove or keep tags with l-if conditions based on expression evaluation.

    Supports both paired <tag l-if="...">content</tag> and self-closing <tag l-if="..."/>.
    Recursively processes until no more conditionals are found (for nested conditions).

    Args:
        template: HTML with l-if attributes.
        context: Dict with "props", "state", "py" keys.

    Returns:
        HTML with conditional tags removed/kept based on evaluated expressions.
    """
    pair_pattern = re.compile(
        r"<(?P<tag>[A-Za-z][A-Za-z0-9:_\-]*)\b(?P<before>[^>]*)\sl-if\s*=\s*(?P<quote>\"|')(?P<expr>.*?)(?P=quote)(?P<after>[^>]*)>(?P<body>.*?)</(?P=tag)>",
        re.IGNORECASE | re.DOTALL,
    )
    self_closing_pattern = re.compile(
        r"<(?P<tag>[A-Za-z][A-Za-z0-9:_\-]*)\b(?P<before>[^>]*)\sl-if\s*=\s*(?P<quote>\"|')(?P<expr>.*?)(?P=quote)(?P<after>[^>]*)/>",
        re.IGNORECASE | re.DOTALL,
    )

    rendered = template
    while True:
        previous = rendered
        rendered = pair_pattern.sub(lambda match: _replace_conditional_tag(match, context), rendered)
        rendered = self_closing_pattern.sub(
            lambda match: _replace_conditional_self_closing_tag(match, context), rendered
        )
        if rendered == previous:
            break

    return rendered


def _replace_conditional_tag(match: re.Match[str], context: Mapping[str, Any]) -> str:
    """Replace a pair conditional tag, removing it if the condition is false.

    Args:
        match: Regex match object for a <tag l-if="expr">body</tag> tag.
        context: Dict with "props", "state", "py" keys.

    Returns:
        The tag without the l-if attribute, or empty string if condition is false.
    """
    expression = match.group("expr")
    try:
        should_render = bool(evaluate_expression(expression, context))
    except Exception:
        should_render = False

    if not should_render:
        return ""

    tag_name = match.group("tag")
    attrs = (match.group("before") + match.group("after")).strip()
    opening = f"<{tag_name}"
    if attrs:
        opening = f"{opening} {attrs}"
    opening = f"{opening}>"
    return f"{opening}{match.group('body')}</{tag_name}>"


def _replace_conditional_self_closing_tag(match: re.Match[str], context: Mapping[str, Any]) -> str:
    """Replace a self-closing conditional tag, removing it if the condition is false.

    Args:
        match: Regex match object for a <tag l-if="expr"/> tag.
        context: Dict with "props", "state", "py" keys.

    Returns:
        The tag without the l-if attribute, or empty string if condition is false.
    """
    expression = match.group("expr")
    try:
        should_render = bool(evaluate_expression(expression, context))
    except Exception:
        should_render = False

    if not should_render:
        return ""

    tag_name = match.group("tag")
    attrs = (match.group("before") + match.group("after")).strip()
    opening = f"<{tag_name}"
    if attrs:
        opening = f"{opening} {attrs}"
    return f"{opening}/>"


def build_python_context(python_block: str, props: Mapping[str, Any]) -> dict[str, Any]:
    """Call component.context(props) and return its result as a dict.

    Args:
        python_block: The <python> block source code.
        props: Component props.

    Returns:
        The dict returned by context(props), or empty dict if no context() found.
    """
    from lua_spa.scope import load_python_scope, resolve_component_callables, normalize_context_result

    local_scope = load_python_scope(python_block)

    context_factory, _ = resolve_component_callables(local_scope)
    if context_factory is None:
        return {}

    result = context_factory(dict(props))
    return normalize_context_result(result)


def build_server_state(python_block: str, props: Mapping[str, Any]) -> dict[str, Any]:
    """Call component.client() and initialize server state from state specs.

    Args:
        python_block: The <python> block source code.
        props: Component props.

    Returns:
        A dict mapping state names to their initial values.
    """
    from lua_spa.scope import load_python_scope, resolve_component_callables, normalize_client_spec

    local_scope = load_python_scope(python_block)
    _, client_factory = resolve_component_callables(local_scope)
    if client_factory is None:
        return {}

    raw_spec = client_factory()
    props_spec, state_spec, _, _ = normalize_client_spec(raw_spec)
    resolved_props = dict(props_spec)
    resolved_props.update(dict(props))

    server_state: dict[str, Any] = {}
    for state_name, state_cfg in state_spec.items():
        server_state[str(state_name)] = resolve_python_state_initial_value(state_cfg, resolved_props)
    return server_state


def resolve_python_state_initial_value(state_cfg: Any, resolved_props: Mapping[str, Any]) -> Any:
    """Resolve the initial value of a state field.

    Checks for init() callable, from_prop reference, or default value.
    Applies type casting based on the cast field.

    Args:
        state_cfg: State config dict with optional init, from_prop, default, cast.
        resolved_props: Component props (used by init() and from_prop).

    Returns:
        The initial state value.
    """
    if not isinstance(state_cfg, Mapping):
        return state_cfg

    init_candidate = state_cfg.get("init")
    if callable(init_candidate):
        state_self = SimpleNamespace(props=to_namespace(resolved_props), state=SimpleNamespace())
        try:
            return init_candidate(state_self)
        except TypeError:
            if hasattr(init_candidate, "__func__"):
                return init_candidate.__func__(state_self)
            return init_candidate()

    from_prop = state_cfg.get("from_prop")
    if from_prop is None:
        value = state_cfg.get("default")
    else:
        prop_name = str(from_prop)
        value = resolved_props.get(prop_name, state_cfg.get("default"))

    cast_kind = str(state_cfg.get("cast", "raw"))
    if cast_kind == "int":
        return int(value or 0)
    if cast_kind == "float":
        return float(value or 0)
    if cast_kind == "str":
        return str(value if value is not None else "")
    if cast_kind == "bool":
        return bool(value)
    return value
