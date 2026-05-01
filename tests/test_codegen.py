from __future__ import annotations

from typing import Any

from lua_spa.codegen import (
    _evaluate_state_init_callable,
    _js_action_statement,
    _js_initial_state_expression,
    _js_runtime_value_expression,
    _normalize_action_operation,
    build_client_script,
)
from lua_spa.trace import _CastReference, _PropReference


def test_codegen_action_and_value_helpers() -> None:
    # Given: action operation definitions and prop/cast references
    operation = _normalize_action_operation({"op": "add", "state": "count", "value": 2})

    # When: JS helpers convert them to JavaScript expressions
    statement = _js_action_statement(operation, {"count": "setCount"}, {"count": "countValue"})
    expr = _js_initial_state_expression(
        {"from_prop": "start", "default": 1, "cast": "int"}, "props"
    )
    runtime_expr = _js_runtime_value_expression(
        _CastReference("str", _PropReference("name", "x")), "props"
    )

    # Then: generated JS contains expected setter and cast wrappers
    assert "setCount" in statement
    assert "Number(" in expr
    assert "String(" in runtime_expr


def test_codegen_branches_for_multi_log_js_and_conditions() -> None:
    # Given: various operation types (multi, log, js, conditional)
    multi = _normalize_action_operation(
        {
            "op": "multi",
            "steps": [
                {"op": "add", "state": "count", "value": 1},
                {"op": "sub", "state": "count", "value": 1},
            ],
        }
    )

    # When: each operation is compiled to a JS statement
    statement = _js_action_statement(multi, {"count": "setCount"}, {"count": "value"})
    log_stmt = _js_action_statement({"op": "log", "value": "x"}, {"count": "setCount"})
    js_stmt = _js_action_statement({"op": "js", "value": "return;"}, {"count": "setCount"})
    conditional_stmt = _js_action_statement(
        {
            "op": "add",
            "state": "count",
            "value": 1,
            "cond": {"left": "count", "op": ">", "right": 0},
        },
        {"count": "setCount"},
        {"count": "countVal"},
    )

    # Then: each compiled statement has the expected JS structure
    assert "setCount" in statement
    assert "console.log" in log_stmt
    assert js_stmt == "return;"
    assert conditional_stmt.startswith("if (")


def test_codegen_build_client_script() -> None:
    # Given: a Python component class with client spec
    python_block = """
class Counter(Component):
    def client(self):
        return {
            "props": {"start": 0},
            "state": {"count": {"from_prop": "start", "default": 0, "cast": "int"}},
            "actions": {"inc": {"op": "add", "state": "count", "value": 1}},
            "lifecycle": {"onMount": []},
        }
"""

    # When: build_client_script compiles the component
    script = build_client_script(python_block)

    # Then: the resulting JS defines a setup function with actions
    assert "function setup" in script
    assert "actions" in script


def test_codegen_fallback_and_error_paths() -> None:
    # Given: an init callable wrapper, invalid operation inputs
    class InitWrap:
        def __call__(self, value: Any) -> Any:
            raise TypeError("wrapped")

        def __func__(self, value: Any) -> Any:
            return value.props.get("x", 1)

    # When: error paths and fallback branches are exercised

    # Then: each edge case behaves as expected
    assert _evaluate_state_init_callable(InitWrap()) is not None

    assert _normalize_action_operation({"op": "log", "value": "x"})["op"] == "log"
    try:
        _normalize_action_operation("bad")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

    try:
        _js_action_statement({"op": "multi", "steps": [1]}, {"count": "setCount"})
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

    try:
        _js_action_statement({"op": "js", "value": 1}, {"count": "setCount"})
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

    bool_expr = _js_runtime_value_expression(
        _CastReference("bool", _PropReference("v", 0)), "props"
    )
    assert "Boolean(" in bool_expr
