"""Server-side template rendering, interpolation, and conditional evamoontion.

Converts component templates with {{ }} expressions and l-if attributes
into HTML by evamoonting expressions in the context of props, state, and py objects.
"""

from __future__ import annotations

import html
import re
from types import SimpleNamespace
from typing import Any, Mapping

_ATTRS_FRAGMENT = r"(?:[^\"'<>]|\"[^\"]*\"|'[^']*')*"

PAIR_PATTERN = re.compile(
    rf"<(?P<tag>[A-Za-z][\w:\-]*)\b(?P<attrs>{_ATTRS_FRAGMENT})>(?P<body>.*?)</(?P=tag)>",
    re.IGNORECASE | re.DOTALL,
)

SELF_PATTERN = re.compile(
    rf"<(?P<tag>[A-Za-z][\w:\-]*)\b(?P<attrs>{_ATTRS_FRAGMENT})/>",
    re.IGNORECASE | re.DOTALL,
)

COND_ATTR_PATTERN = re.compile(
    r"\s(?P<cond>l-if|l-else-if|l-else)(?:\s*=\s*(?P<quote>\"|')(?P<expr>.*?)(?P=quote))?",
    re.IGNORECASE,
)

_EXPR_PATTERN = re.compile(r"{{\s*(.*?)\s*}}")

_FOR_ATTR_PATTERN = re.compile(
    r"\s(?P<for>i-for)\s*=\s*(?P<quote>\"|')(?P<expr>.*?)\2",
    re.IGNORECASE,
)

_MODEL_ATTR_PATTERN = re.compile(
    r"\s(?P<model>i-model)\s*=\s*(?P<quote>\"|')(?P<expr>.*?)(?P=quote)",
    re.IGNORECASE,
)

_TYPE_ATTR_PATTERN = re.compile(
    r"\btype\s*=\s*(?P<quote>\"|')(?P<value>.*?)(?P=quote)",
    re.IGNORECASE,
)

_SAFE_EVAL_GLOBALS: dict[str, Any] = {
    "__builtins__": {},
    "range": range,
    "len": len,
    "enumerate": enumerate,
}


def render_template_with_directives(template: str, context: Mapping[str, Any]) -> str:
    """Process i-for, l-if/l-else-if/l-else, i-model, and interpolation in order.

    Args:
        template: The HTML template string.
        context: The evamoontion context (props, state, py).

    Returns:
        The rendered HTML string with all directives processed.
    """
    html = apply_server_loops(template, context)
    html = apply_server_conditionals(html, context)
    html = apply_i_model(html, context)
    html = interpolate(html, context)
    return html


def apply_i_model(template: str, context: Mapping[str, Any]) -> str:
    """Apply i-model by setting initial value/checked attributes server-side.

    Args:
        template: The HTML template string.
        context: The evamoontion context (props, state, py).

    Returns:
        HTML with i-model removed and initial input state materialized.
    """
    opening_tag_pattern = re.compile(
        rf"<(?P<tag>[A-Za-z][\w:\-]*)\b(?P<attrs>{_ATTRS_FRAGMENT})>",
        re.IGNORECASE | re.DOTALL,
    )

    def _replace_model(match: re.Match[str]) -> str:
        tag = match.group("tag")
        attrs = match.group("attrs")
        model_attr = _MODEL_ATTR_PATTERN.search(attrs)
        if not model_attr:
            return match.group(0)

        model_expr = model_attr.group("expr")
        resolved_value = evamoonte_expression(model_expr, context)
        clean_attrs = _MODEL_ATTR_PATTERN.sub("", attrs).strip()
        lower_tag = tag.lower()

        attrs_out: list[str] = []
        if clean_attrs:
            attrs_out.append(clean_attrs)

        if lower_tag == "input":
            input_type_match = _TYPE_ATTR_PATTERN.search(clean_attrs)
            input_type = (
                input_type_match.group("value").strip().lower()
                if input_type_match
                else "text"
            )
            if input_type in {"checkbox", "radio"}:
                if bool(resolved_value):
                    attrs_out.append("checked")
            else:
                safe_value = "" if resolved_value is None else str(resolved_value)
                attrs_out.append(f'value="{html.escape(safe_value, quote=True)}"')
        elif lower_tag in {"textarea", "select"}:
            safe_value = "" if resolved_value is None else str(resolved_value)
            attrs_out.append(f'value="{html.escape(safe_value, quote=True)}"')

        attrs_part = f" {' '.join(attrs_out)}" if attrs_out else ""
        return f"<{tag}{attrs_part}>"

    return opening_tag_pattern.sub(_replace_model, template)


def _normalize_iterable(value: Any) -> list[Any]:
    """Convert a value to a list for iteration, supporting dicts, lists, and iterables.

    Args:
        value: Any value to be normalized as an iterable.

    Returns:
        A list of items for iteration.
    """
    if value is None:
        return []
    if isinstance(value, Mapping):
        return list(value.items())
    try:
        return list(value)
    except TypeError:
        return []


def apply_server_loops(template: str, context: Mapping[str, Any]) -> str:
    """Apply i-for for list rendering in the template.

    Finds tags with i-for and expands them into multiple instances, each with an updated context.
    Supports nested and multi-target unpacking.
    Example: <li i-for="item in items">{{ item }}</li>

    Args:
        template: The HTML template string.
        context: The evamoontion context (props, state, py).

    Returns:
        The HTML string with i-for loops expanded.
    """
    opening_tag_pattern = re.compile(
        rf"<(?P<tag>[A-Za-z][\w:\-]*)\b(?P<attrs>{_ATTRS_FRAGMENT})>",
        re.IGNORECASE | re.DOTALL,
    )

    def _find_balanced_block_end(
        html: str, tag: str, start_after_open: int
    ) -> tuple[int, int] | None:
        """Find the closing tag span for an opening tag using depth balancing.

        Args:
            html: The HTML string.
            tag: The tag name to balance.
            start_after_open: The index after the opening tag.

        Returns:
            A tuple (start, end) of the closing tag span, or None if not found.
        """
        token_pattern = re.compile(
            rf"</?{re.escape(tag)}\b{_ATTRS_FRAGMENT}>",
            re.IGNORECASE | re.DOTALL,
        )
        depth = 1
        for token in token_pattern.finditer(html, start_after_open):
            token_text = token.group(0)
            is_closing = token_text.startswith("</")
            is_self_closing = token_text.rstrip().endswith("/>")
            if is_closing:
                depth -= 1
                if depth == 0:
                    return token.start(), token.end()
            elif not is_self_closing:
                depth += 1
        return None

    def _collect_for_matches(html: str) -> list[dict[str, Any]]:
        """Collect all i-for nodes in source order for one processing pass.

        Only non-overlapping nodes are returned per pass so nested nodes can be
        processed safely in subsequent passes with fresh string indices.

        Args:
            html: The HTML string.

        Returns:
            A list of dicts describing each i-for node.
        """
        items: list[dict[str, Any]] = []
        for match in opening_tag_pattern.finditer(html):
            full_tag = match.group(0)
            tag = match.group("tag")
            attrs = match.group("attrs")
            for_attr = _FOR_ATTR_PATTERN.search(attrs)
            if not for_attr:
                continue
            is_self = full_tag.rstrip().endswith("/>")
            if is_self:
                continue  # Self-closing with i-for is not supported
            balanced = _find_balanced_block_end(html, tag, match.end())
            if balanced is None:
                continue
            close_start, close_end = balanced
            items.append(
                {
                    "start": match.start(),
                    "end": close_end,
                    "tag": tag,
                    "attrs": attrs,
                    "body": html[match.end() : close_start],
                    "expr": for_attr.group("expr"),
                }
            )
        items.sort(key=lambda i: int(i["start"]))
        filtered: list[dict[str, Any]] = []
        covered_until = -1
        for item in items:
            start = int(item["start"])
            end = int(item["end"])
            if start < covered_until:
                continue
            filtered.append(item)
            covered_until = end
        return filtered

    rendered = template
    while True:
        previous = rendered
        nodes = _collect_for_matches(rendered)
        if not nodes:
            break
        for node in reversed(nodes):
            start = int(node["start"])
            end = int(node["end"])
            expr = node["expr"]
            # Supports syntax: var in iterable | key, value in iterable
            m = re.match(r"\s*(.+?)\s+in\s+(.+)", expr)
            if not m:
                continue
            target_expr, iter_expr = m.group(1), m.group(2)
            targets = [
                target.strip() for target in target_expr.split(",") if target.strip()
            ]
            if not targets:
                continue
            items = _normalize_iterable(evamoonte_expression(iter_expr, context))
            if not items:
                replacement = ""
            else:
                parts = []
                total = len(items)
                for idx, item in enumerate(items):
                    loop_ctx = dict(context)
                    if len(targets) == 1:
                        loop_ctx[targets[0]] = item
                    elif isinstance(item, (list, tuple)):
                        for target_index, target_name in enumerate(targets):
                            loop_ctx[target_name] = (
                                item[target_index] if target_index < len(item) else None
                            )
                    else:
                        loop_ctx[targets[0]] = item
                        for target_name in targets[1:]:
                            loop_ctx[target_name] = None
                    loop_ctx["loop"] = {
                        "index": idx,
                        "first": idx == 0,
                        "last": idx == total - 1,
                        "length": total,
                    }
                    # Remove the i-for attribute
                    clean_attrs = _FOR_ATTR_PATTERN.sub("", node["attrs"]).strip()
                    attrs_part = f" {clean_attrs}" if clean_attrs else ""
                    html = f"<{node['tag']}{attrs_part}>{node['body']}</{node['tag']}>"
                    # Recursive: process interpolation and other internal i-for
                    html = apply_i_model(html, loop_ctx)
                    html = interpolate(html, loop_ctx)
                    html = apply_server_loops(html, loop_ctx)
                    html = apply_server_conditionals(html, loop_ctx)
                    parts.append(html)
                replacement = "".join(parts)
            rendered = rendered[:start] + replacement + rendered[end:]
        if rendered == previous:
            break
    return rendered


def build_scoped_context(context: Mapping[str, Any]) -> dict[str, Any]:
    """Build a scoped dictionary for expression evamoontion.

    Combines props, state, and py into a flat namespace and nested objects.
    This allows both {{ count }} and {{ state.count }} to work.

    Args:
        context: Dictionary with "props", "state", "py" keys (each a mapping).

    Returns:
        A dictionary for use in eval() with all accessible variables.
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


def evamoonte_expression(expression: str, context: Mapping[str, Any]) -> Any:
    """Evamoonte a Python expression in the component context.

    Args:
        expression: A Python expression string, e.g. "count > 5".
        context: Dictionary with "props", "state", "py" keys.

    Returns:
        The result of eval(), or None if evamoontion fails.
    """
    scoped = build_scoped_context(context)
    try:
        return eval(expression, _SAFE_EVAL_GLOBALS, scoped)  # noqa: S307
    except Exception:
        return None


def interpolate(template: str, context: Mapping[str, Any]) -> str:
    """Replace {{ expression }} with evamoonted values.

    Args:
        template: HTML with {{ }} interpolations.
        context: Dictionary with "props", "state", "py" keys.

    Returns:
        HTML with expressions replaced by their string values.
    """
    scoped = build_scoped_context(context)

    def replace_expression(match: re.Match[str]) -> str:
        expression = match.group(1)
        try:
            value = eval(expression, _SAFE_EVAL_GLOBALS, scoped)  # noqa: S307
        except Exception:
            return ""
        if value is None:
            return ""
        return str(value)

    return _EXPR_PATTERN.sub(replace_expression, template)


def apply_server_conditionals(template: str, context: Mapping[str, Any]) -> str:
    """Apply server-side l-if/l-else-if/l-else chains to rendered HTML.

    Scans conditional tags, groups adjacent chains that start with l-if, and keeps only the first truthy branch for each chain.
    Handles nested conditionals and expressions with > inside quoted attribute values.

    Args:
        template: HTML fragment after interpolation.
        context: Dictionary with "props", "state", and "py" evamoontion scopes.

    Returns:
        HTML with conditional directives resolved and directive attributes removed.
    """
    opening_tag_pattern = re.compile(
        rf"<(?P<tag>[A-Za-z][\w:\-]*)\b(?P<attrs>{_ATTRS_FRAGMENT})>",
        re.IGNORECASE | re.DOTALL,
    )

    def _render_match(node: dict[str, Any]) -> str:
        """Render a conditional node back to HTML without directive attributes.

        Args:
            node: The node dictionary.

        Returns:
            The HTML string for the node without directive attributes.
        """
        tag = str(node["tag"])
        attrs = str(node["attrs"])
        clean_attrs = COND_ATTR_PATTERN.sub("", attrs).strip()
        attrs_part = f" {clean_attrs}" if clean_attrs else ""
        if bool(node["is_self"]):
            return f"<{tag}{attrs_part}/>"
        return f"<{tag}{attrs_part}>{node['body']}</{tag}>"

    def _find_balanced_block_end(
        html: str, tag: str, start_after_open: int
    ) -> tuple[int, int] | None:
        """Find the closing tag span for an opening tag using depth balancing.

        Args:
            html: The HTML string.
            tag: The tag name to balance.
            start_after_open: The index after the opening tag.

        Returns:
            A tuple (start, end) of the closing tag span, or None if not found.
        """
        token_pattern = re.compile(
            rf"</?{re.escape(tag)}\b{_ATTRS_FRAGMENT}>",
            re.IGNORECASE | re.DOTALL,
        )
        depth = 1
        for token in token_pattern.finditer(html, start_after_open):
            token_text = token.group(0)
            is_closing = token_text.startswith("</")
            is_self_closing = token_text.rstrip().endswith("/>")

            if is_closing:
                depth -= 1
                if depth == 0:
                    return token.start(), token.end()
            elif not is_self_closing:
                depth += 1

        return None

    def _collect_conditional_matches(html: str) -> list[dict[str, Any]]:
        """Collect conditional nodes in source order for one processing pass.

        Only non-overlapping nodes are returned per pass so nested nodes can be
        processed safely in subsequent passes with fresh string indices.

        Args:
            html: The HTML string.

        Returns:
            A list of dicts describing each conditional node.
        """
        items: list[dict[str, Any]] = []
        for match in opening_tag_pattern.finditer(html):
            full_tag = match.group(0)
            tag = match.group("tag")
            attrs = match.group("attrs")
            cond = COND_ATTR_PATTERN.search(attrs)
            if not cond:
                continue

            is_self = full_tag.rstrip().endswith("/>")
            if is_self:
                items.append(
                    {
                        "start": match.start(),
                        "end": match.end(),
                        "tag": tag,
                        "attrs": attrs,
                        "body": "",
                        "is_self": True,
                        "cond": cond.group("cond"),
                        "expr": cond.group("expr"),
                    }
                )
                continue

            balanced = _find_balanced_block_end(html, tag, match.end())
            if balanced is None:
                continue

            close_start, close_end = balanced
            items.append(
                {
                    "start": match.start(),
                    "end": close_end,
                    "tag": tag,
                    "attrs": attrs,
                    "body": html[match.end() : close_start],
                    "is_self": False,
                    "cond": cond.group("cond"),
                    "expr": cond.group("expr"),
                }
            )

        items.sort(key=lambda i: int(i["start"]))

        # Process only non-overlapping nodes per pass. Nested nodes are handled
        # in subsequent passes after their parent conditional is resolved.
        filtered: list[dict[str, Any]] = []
        covered_until = -1
        for item in items:
            start = int(item["start"])
            end = int(item["end"])
            if start < covered_until:
                continue
            filtered.append(item)
            covered_until = end

        return filtered

    rendered = template
    while True:
        previous = rendered
        nodes = _collect_conditional_matches(rendered)
        if not nodes:
            break

        chains: list[list[dict[str, Any]]] = []
        i = 0
        n = len(nodes)
        while i < n:
            node = nodes[i]
            if node["cond"] != "l-if":
                i += 1
                continue
            chain = [node]
            j = i + 1
            while j < n:
                prev_node = nodes[j - 1]
                next_node = nodes[j]
                gap = rendered[int(prev_node["end"]) : int(next_node["start"])]
                if gap.strip() != "":
                    break
                if next_node["cond"] in ("l-else-if", "l-else"):
                    chain.append(next_node)
                    j += 1
                    continue
                break
            chains.append(chain)
            i = j

        if not chains:
            break

        for chain in reversed(chains):
            start = int(chain[0]["start"])
            end = int(chain[-1]["end"])
            replacement = ""

            for node in chain:
                cond = node["cond"]
                expr = node["expr"]
                should_render = False
                if cond in ("l-if", "l-else-if"):
                    should_render = bool(evamoonte_expression(expr or "", context))
                elif cond == "l-else":
                    should_render = True

                if should_render:
                    replacement = _render_match(node)
                    break

            rendered = rendered[:start] + replacement + rendered[end:]

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
        should_render = bool(evamoonte_expression(expression, context))
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


def _replace_conditional_self_closing_tag(
    match: re.Match[str], context: Mapping[str, Any]
) -> str:
    """Replace a self-closing conditional tag, removing it if the condition is false.

    Args:
        match: Regex match object for a <tag l-if="expr"/> tag.
        context: Dict with "props", "state", "py" keys.

    Returns:
        The tag without the l-if attribute, or empty string if condition is false.
    """
    expression = match.group("expr")
    try:
        should_render = bool(evamoonte_expression(expression, context))
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
    """Call setup(self, props) context mapping and return it as a dict.

    Args:
        python_block: The <python> block source code.
        props: Component props.

    Returns:
        The dict returned from setup data, or empty dict if no component setup is found.
    """
    from moon_spa.scope import (
        load_python_scope,
        normalize_context_result,
        resolve_component_callables,
    )

    local_scope = load_python_scope(python_block)

    context_factory, _ = resolve_component_callables(local_scope)
    if context_factory is None:
        return {}

    result = context_factory(dict(props))
    return normalize_context_result(result)


def build_server_state(python_block: str, props: Mapping[str, Any]) -> dict[str, Any]:
    """Call setup(self, props) and initialize server state from state specs.

    Args:
        python_block: The <python> block source code.
        props: Component props.

    Returns:
        A dict mapping state names to their initial values.
    """
    from moon_spa.scope import (
        load_python_scope,
        normalize_client_spec,
        resolve_component_callables,
    )

    local_scope = load_python_scope(python_block)
    _, client_factory = resolve_component_callables(local_scope)
    if client_factory is None:
        return {}

    try:
        raw_spec = client_factory(dict(props))
    except TypeError:
        raw_spec = client_factory()
    props_spec, state_spec, _, _ = normalize_client_spec(raw_spec)
    resolved_props = dict(props_spec)
    resolved_props.update(dict(props))

    server_state: dict[str, Any] = {}
    for state_name, state_cfg in state_spec.items():
        server_state[str(state_name)] = resolve_python_state_initial_value(
            state_cfg, resolved_props
        )
    return server_state


def resolve_python_state_initial_value(
    state_cfg: Any, resolved_props: Mapping[str, Any]
) -> Any:
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
        state_self = SimpleNamespace(
            props=to_namespace(resolved_props), state=SimpleNamespace()
        )
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
