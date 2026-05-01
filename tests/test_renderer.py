from __future__ import annotations

from typing import Any, Callable
import re

from lua_spa.renderer import (
    _normalize_iterable,
    apply_server_conditionals,
    apply_server_loops,
    build_python_context,
    build_scoped_context,
    build_server_state,
    evaluate_expression,
    interpolate,
    _replace_conditional_self_closing_tag,
    _replace_conditional_tag,
    render_template_with_directives,
    resolve_python_state_initial_value,
    to_namespace,
)


def _assert_raises(exc_type: type[BaseException], fn: Callable[..., Any], *args: Any) -> None:
    try:
        fn(*args)
    except exc_type:
        return
    raise AssertionError(f"Expected {exc_type.__name__} to be raised")


def test_render_template_with_directives_interpolates_value() -> None:
    # Given: a template with a {{ value }} expression

    # When: the template is rendered with a context containing value=42
    html = render_template_with_directives(
        "<div>{{ value }}</div>",
        {"props": {"value": 42}, "state": {}, "py": {}},
    )

    # Then: the value is interpolated in the output
    assert "42" in html


def test_render_template_with_directives_handles_conditionals() -> None:
    # Given: a template with l-if and l-else branches

    # When: rendered with count=2 (satisfying count > 1)
    html = render_template_with_directives(
        '<div><p l-if="count > 1">ok</p><p l-else>no</p></div>',
        {"props": {}, "state": {"count": 2}, "py": {}},
    )

    # Then: the true branch is included and the false branch is excluded
    assert "ok" in html
    assert "no" not in html


def test_renderer_helpers_and_expression_eval() -> None:
    # Given: a multi-layer context and an unknown variable expression

    # When: helpers build the scoped context and evaluate expressions
    scoped = build_scoped_context({"props": {"a": 1}, "state": {"b": 2}, "py": {"c": 3}})
    result = evaluate_expression(
        "a + b + c", {"props": {"a": 1}, "state": {"b": 2}, "py": {"c": 3}}
    )
    missing = evaluate_expression("unknown + 1", {"props": {}, "state": {}, "py": {}})

    # Then: scoped merges all layers; missing variables return None
    assert scoped["a"] == 1
    assert result == 6
    assert missing is None


def test_renderer_normalize_iterable_and_namespace() -> None:
    # Given: None, a list, and a nested dict

    # When: _normalize_iterable and to_namespace process them
    normalized_none = _normalize_iterable(None)
    normalized_list = _normalize_iterable([1, 2])
    ns = to_namespace({"x": {"y": 2}})

    # Then: None becomes [], list is unchanged, dict becomes nested namespace
    assert normalized_none == []
    assert normalized_list == [1, 2]
    assert ns.x.y == 2


def test_renderer_loops_and_conditionals_paths() -> None:
    # Given: contexts with items list and a false boolean prop
    ctx = {"props": {"items": [1, 2], "ok": False}, "state": {}, "py": {}}

    # When: server loops and conditionals are applied
    html = apply_server_loops('<ul><li i-for="item in items">x</li></ul>', ctx)
    cond_html = apply_server_conditionals(
        '<div><p l-if="ok">yes</p><p l-else>no</p></div>',
        ctx,
    )
    html_self = apply_server_loops(
        '<div><span i-for="x in items"/></div>',
        {"props": {"items": [1]}, "state": {}, "py": {}},
    )

    # Then: loops expand items, conditionals pick the right branch, self-closing stays unchanged
    assert html.count("<li") == 2
    assert "no" in cond_html
    assert html_self == '<div><span i-for="x in items"/></div>'


def test_renderer_interpolate_and_python_context_state() -> None:
    # Given: a template with a title placeholder and a Python component block
    py_block = """
class App(Component):
    def context(self, props):
        return {"title": props.get("title", "T")}

    def client(self):
        class S:
            State = [{"name": "count", "default": 1, "cast": "int"}]
        return S()
"""

    # When: interpolate, build_python_context, and build_server_state are called
    text = interpolate("<p>{{ title }}</p>", {"props": {"title": "A"}, "state": {}, "py": {}})
    context = build_python_context(py_block, {"title": "Z"})
    state = build_server_state(py_block, {})

    # Then: title is interpolated, context returns the prop value, state has the default count
    assert "A" in text
    assert context["title"] == "Z"
    assert state["count"] == 1


def test_renderer_resolve_python_state_initial_value_paths() -> None:
    # Given: various cast configuration dictionaries

    # When: resolve_python_state_initial_value processes each cast type

    # Then: values are cast to the correct Python types
    assert resolve_python_state_initial_value({"default": "1", "cast": "int"}, {}) == 1
    assert resolve_python_state_initial_value({"default": "1", "cast": "float"}, {}) == 1.0
    assert resolve_python_state_initial_value({"default": 1, "cast": "str"}, {}) == "1"
    assert resolve_python_state_initial_value({"default": 0, "cast": "bool"}, {}) is False
    assert resolve_python_state_initial_value({"default": 5, "cast": "raw"}, {}) == 5


def test_renderer_additional_branches() -> None:
    # Given: a template with l-else-if branch and a component that returns a non-dict context

    # When: conditionals are applied and build_python_context is called with bad context
    cond = apply_server_conditionals(
        '<div><p l-if="ok">a</p><p l-else-if="other">b</p><p l-else>c</p></div>',
        {"props": {"ok": False, "other": True}, "state": {}, "py": {}},
    )

    # Then: l-else-if branch is selected; invalid context raises ValueError
    assert "b" in cond

    _assert_raises(
        ValueError,
        build_python_context,
        """
class App(Component):
    def context(self, props):
        return 1
""",
        {},
    )


def test_renderer_private_conditional_replace_helpers() -> None:
    # Given: regex matches for l-if on paired and self-closing tags
    pair = re.search(
        r"<(?P<tag>p)(?P<before>.*?)l-if=\"(?P<expr>.*?)\"(?P<after>.*?)>(?P<body>.*?)</(?P=tag)>",
        '<p class="x" l-if="ok">A</p>',
    )
    assert pair is not None
    self_match = re.search(
        r"<(?P<tag>img)(?P<before>.*?)l-if=\"(?P<expr>.*?)\"(?P<after>.*?)/>",
        '<img alt="x" l-if="ok"/>',
    )
    assert self_match is not None

    # When: replace helpers are called with true and false contexts
    kept = _replace_conditional_tag(pair, {"props": {"ok": True}, "state": {}, "py": {}})
    removed = _replace_conditional_tag(pair, {"props": {"ok": False}, "state": {}, "py": {}})
    kept_self = _replace_conditional_self_closing_tag(
        self_match, {"props": {"ok": True}, "state": {}, "py": {}}
    )
    removed_self = _replace_conditional_self_closing_tag(
        self_match, {"props": {"ok": False}, "state": {}, "py": {}}
    )

    # Then: true context keeps the tag; false context removes it
    assert "<p" in kept
    assert removed == ""
    assert kept_self.startswith("<img")
    assert removed_self == ""


def test_renderer_state_init_callable_fallback_branch() -> None:
    # Given: an init callable that raises TypeError but has a __func__ fallback
    class InitWrap:
        def __call__(self, value: Any) -> Any:
            raise TypeError("x")

        def __func__(self, value: Any) -> Any:
            return value.props.count

    cfg = {"init": InitWrap(), "default": 1}

    # When: state initial value is resolved with props containing count=7
    resolved = resolve_python_state_initial_value(cfg, {"count": 7})

    # Then: the __func__ fallback returns the count value
    assert resolved == 7


def test_renderer_loop_multi_target_and_invalid_for_syntax() -> None:
    # Given: a multi-target loop template and an invalid i-for syntax

    # When: apply_server_loops is called for each
    html = apply_server_loops(
        '<ul><li i-for="k, v in items">{{ k }}={{ v }}</li></ul>',
        {"props": {"items": [["a", 1], ["b", 2]]}, "state": {}, "py": {}},
    )
    unchanged = apply_server_loops(
        '<ul><li i-for="bad syntax">x</li></ul>',
        {"props": {}, "state": {}, "py": {}},
    )

    # Then: valid multi-target loop expands, invalid syntax leaves the template unchanged
    assert html.count("<li") == 2
    assert "i-for" in unchanged
