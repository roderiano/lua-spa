"""Client-side code generation: converts Python specs into JavaScript setup() function.

Generates the JavaScript code that sets up component state, actions, and lifecycle
hooks on the client side by analyzing the Python component definition.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, Mapping

from lua_spa.scope import (
    load_python_scope,
    normalize_client_spec,
    resolve_component_callables,
)
from lua_spa.trace import _BinaryExpression, _CastReference, _PropReference


def build_client_script(python_block: str) -> str:
    """Generate the client-side setup() function from a component's Python block.

    Analyzes the component spec and generates a JavaScript function that:
    - Accepts useState and props
    - Defines state hooks
    - Defines action functions
    - Sets up lifecycle hooks
    - Returns { props, state, actions, lifecycle }

    Args:
        python_block: The <python> block source code.

    Returns:
        JavaScript code defining a setup() function, or empty string if no client() found.
    """
    local_scope = load_python_scope(python_block)
    _, client_factory = resolve_component_callables(local_scope)
    if client_factory is None:
        return ""

    raw_spec = client_factory()
    props_spec, state_spec, actions_spec, lifecycle_spec = normalize_client_spec(raw_spec)

    state_fields = list(state_spec.items())
    lines: list[str] = ["function setup({ useState, props }) {"]
    props_literal = _js_literal(props_spec)
    lines.append(f"  const resolvedProps = Object.assign({{}}, {props_literal}, props || {{}});")

    for prop_name, default_value in props_spec.items():
        prop_key = _js_literal(str(prop_name))
        if isinstance(default_value, bool):
            lines.append(
                "  if (Object.prototype.hasOwnProperty.call(resolvedProps, "
                + prop_key
                + ")) { resolvedProps["
                + prop_key
                + "] = Boolean(resolvedProps["
                + prop_key
                + "]); }"
            )
        elif isinstance(default_value, (int, float)):
            lines.append(
                "  if (Object.prototype.hasOwnProperty.call(resolvedProps, "
                + prop_key
                + ")) { resolvedProps["
                + prop_key
                + "] = Number(resolvedProps["
                + prop_key
                + "]); }"
            )
    setter_by_state: dict[str, str] = {}
    value_by_state: dict[str, str] = {}

    for index, (state_name_raw, state_cfg) in enumerate(state_fields):
        state_name = str(state_name_raw)
        value_var = f"__state_{index}"
        setter_var = f"__set_state_{index}"
        initial_expr = _js_initial_state_expression(state_cfg, "resolvedProps")
        lines.append(f"  const [{value_var}, {setter_var}] = useState({initial_expr});")
        setter_by_state[state_name] = setter_var
        value_by_state[state_name] = value_var

    lines.append("  const actions = {")

    for action_name_raw, action_cfg in actions_spec.items():
        action_name = str(action_name_raw)
        action_operation = _normalize_action_operation(action_cfg)
        action_body = _js_action_statement(action_operation, setter_by_state, value_by_state)
        lines.append(f"      {action_name}: function () {{")
        lines.append(f"        {action_body}")
        lines.append("      },")

    lines.append("  };")
    lines.append("  function __callAction(actionName, event) {")
    lines.append("    var action = actions[actionName];")
    lines.append("    if (typeof action === 'function') {")
    lines.append("      action(event);")
    lines.append("    }")
    lines.append("  }")

    lines.append("  const lifecycle = {")
    for hook_name in ["onCreate", "onMount", "onUpdate", "onUnmount"]:
        operations = lifecycle_spec.get(hook_name, [])
        lines.append(f"    {hook_name}: function () {{")
        for lifecycle_operation in operations:
            if isinstance(lifecycle_operation, Mapping):
                statement = _js_action_statement(
                    lifecycle_operation, setter_by_state, value_by_state
                )
                lines.append(f"      {statement}")
            else:
                lines.append(f"      __callAction({_js_literal(lifecycle_operation)});")
        lines.append("    },")
    lines.append("  };")

    state_pairs = [f"{key}: {value_by_state[key]}" for key in value_by_state]
    lines.append("  const state = {" + ", ".join(state_pairs) + "};")

    lines.append("  return {")
    lines.append("    props: resolvedProps,")
    lines.append("    state: state,")
    lines.append("    actions: actions,")
    lines.append("    lifecycle: lifecycle,")
    lines.append("  };")
    lines.append("}")

    return "\n".join(lines)


def _js_initial_state_expression(config: Any, prop_var_name: str) -> str:
    """Generate a JavaScript expression for a state field's initial value.

    Handles init() callables, from_prop references, default values, and type casting.

    Args:
        config: State config dict or scalar value.
        prop_var_name: Name of the props variable in the generated JS.

    Returns:
        A JavaScript expression evaluating to the initial state value.
    """
    if isinstance(config, Mapping):
        init_candidate = config.get("init")
        if callable(init_candidate):
            expression_value = _evaluate_state_init_callable(init_candidate)
            return _js_runtime_value_expression(expression_value, prop_var_name)

        from_prop = config.get("from_prop")
        default_value = config.get("default")
        cast_kind = str(config.get("cast", "raw"))
        if from_prop is None:
            return _js_literal(default_value)

        prop_expr = f"{prop_var_name}[{_js_literal(str(from_prop))}]"
        fallback = _js_literal(default_value)
        base_expr = (
            f"(({prop_expr}) !== undefined && ({prop_expr}) !== null ? ({prop_expr}) : {fallback})"
        )

        if cast_kind == "int":
            return f"Number({base_expr})"
        if cast_kind == "float":
            return f"Number({base_expr})"
        if cast_kind == "str":
            return f"String({base_expr})"
        if cast_kind == "bool":
            return f"Boolean({base_expr})"
        return base_expr

    return _js_runtime_value_expression(config, prop_var_name)


def _evaluate_state_init_callable(init_callable: Any) -> Any:
    """Execute an init() callable to capture its state/prop accesses.

    Args:
        init_callable: A method that accepts self (with .props and .state).

    Returns:
        The value returned by the callable (may include _PropReference objects).
    """
    from lua_spa.trace import _TraceProps

    trace_self = SimpleNamespace(props=_TraceProps(), state=SimpleNamespace())
    try:
        return init_callable(trace_self)
    except TypeError:
        if hasattr(init_callable, "__func__"):
            return init_callable.__func__(trace_self)
        return init_callable()


def _normalize_action_operation(action_cfg: Any) -> dict[str, Any]:
    """Normalize an action config dict into a standard operation dict.

    Validates and extracts op, state, value fields. Handles multi-step operations.
    Preserves conditional information if present.

    Args:
        action_cfg: Action config mapping.

    Returns:
        A normalized operation dict with op, state, value (and steps for multi ops, cond for conditionals).

    Raises:
        ValueError: If format is invalid.
    """
    if not isinstance(action_cfg, Mapping):
        raise ValueError("Each action config must be a mapping")

    op_kind = str(action_cfg.get("op", "set"))
    if op_kind == "multi":
        steps = action_cfg.get("steps")
        if not isinstance(steps, list):
            raise ValueError("multi action requires list field 'steps'")
        return {"op": "multi", "steps": steps}

    if op_kind == "log":
        return {"op": "log", "value": action_cfg.get("value")}

    state_name = action_cfg.get("state")
    if state_name is None:
        raise ValueError("Action config must include 'state'")

    operation: dict[str, Any] = {
        "op": op_kind,
        "state": str(state_name),
        "value": action_cfg.get("value", 0),
    }
    if "cond" in action_cfg:
        operation["cond"] = action_cfg["cond"]
    return operation


def _js_action_statement(
    operation: Mapping[str, Any],
    setter_by_state: Mapping[str, str],
    value_by_state: Mapping[str, str] | None = None,
) -> str:
    """Generate a JavaScript statement for an action operation.

    Converts Python operation dicts into JS setter calls, with optional conditional wrapper.

    Args:
        operation: Operation dict (op, state, value, steps, and optional cond).
        setter_by_state: Mapping of state name -> JS setter variable name.
        value_by_state: Mapping of state name -> JS value variable name (for conditions).

    Returns:
        A JavaScript statement (e.g., "__set_count(c => c + 1);").

    Raises:
        ValueError: If the operation references unknown state.
    """
    if str(operation.get("op", "")).lower() == "multi":
        steps = operation.get("steps", [])
        if not isinstance(steps, list):
            raise ValueError("multi action requires list 'steps'")
        statements: list[str] = []
        for step in steps:
            if not isinstance(step, Mapping):
                raise ValueError("multi action step must be a mapping")
            statements.append(_js_action_statement(step, setter_by_state, value_by_state))
        return " ".join(statements)

    if str(operation.get("op", "")) == "log":
        value_literal = _js_runtime_value_expression(operation.get("value"), "resolvedProps")
        return f"console.log('[lua-spa]', {value_literal});"

    if str(operation.get("op", "")) == "js":
        js_code = operation.get("value")
        if not isinstance(js_code, str):
            raise ValueError("js action requires string field 'value'")
        return js_code

    state_name = str(operation["state"])
    if state_name not in setter_by_state:
        raise ValueError(f"Action references unknown state field: {state_name}")

    setter = setter_by_state[state_name]
    op_kind = str(operation.get("op", "set"))
    value_literal = _js_runtime_value_expression(operation.get("value"), "resolvedProps")

    if op_kind == "add":
        statement = f"{setter}(function (value) {{ return value + {value_literal}; }});"
    elif op_kind == "sub":
        statement = f"{setter}(function (value) {{ return value - {value_literal}; }});"
    elif op_kind == "toggle":
        statement = f"{setter}(function (value) {{ return !value; }});"
    else:
        statement = f"{setter}(function () {{ return {value_literal}; }});"

    condition = operation.get("cond")
    if condition is not None and value_by_state is not None:
        cond_left = str(condition.get("left", ""))
        cond_op = str(condition.get("op", ""))
        cond_right = condition.get("right")

        if cond_left in value_by_state:
            left_var = value_by_state[cond_left]
            right_expr = _js_runtime_value_expression(cond_right, "resolvedProps")
            statement = f"if ({left_var} {cond_op} {right_expr}) {{ {statement} }}"

    return statement


def _js_runtime_value_expression(value: Any, prop_var_name: str) -> str:
    """Generate a JavaScript expression for a runtime value.

    Handles _PropReference (prop access with fallback) and _CastReference
    (type casting) by generating appropriate JS code.

    Args:
        value: A scalar, _PropReference, or _CastReference.
        prop_var_name: Name of the props variable in the generated JS.

    Returns:
        A JavaScript expression.
    """
    if isinstance(value, _PropReference):
        prop_name = _js_literal(value.name)
        default_literal = _js_literal(value.default)
        return (
            f"(({prop_var_name}[{prop_name}]) !== undefined && ({prop_var_name}[{prop_name}]) !== null"
            f" ? ({prop_var_name}[{prop_name}]) : {default_literal})"
        )

    if isinstance(value, _CastReference):
        inner_expression = _js_runtime_value_expression(value.value, prop_var_name)
        if value.cast == "int" or value.cast == "float":
            return f"Number({inner_expression})"
        if value.cast == "str":
            return f"String({inner_expression})"
        if value.cast == "bool":
            return f"Boolean({inner_expression})"
        return inner_expression

    if isinstance(value, _BinaryExpression):
        left_expr = _js_runtime_value_expression(value.left, prop_var_name)
        right_expr = _js_runtime_value_expression(value.right, prop_var_name)
        if value.op == "//":
            return f"Math.floor(({left_expr}) / ({right_expr}))"
        if value.op == "**":
            return f"Math.pow({left_expr}, {right_expr})"
        return f"({left_expr} {value.op} {right_expr})"

    return _js_literal(value)


def _js_literal(value: Any) -> str:
    """Convert a Python value to a JSON JavaScript literal.

    Args:
        value: A Python scalar, list, or dict.

    Returns:
        A JSON string suitable for embedding in JavaScript.
    """
    return json.dumps(value, ensure_ascii=True)
