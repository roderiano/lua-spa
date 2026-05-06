from __future__ import annotations

from typing import Any

from lua_spa.codegen import (
    _evaluate_state_init_callable,
    _js_action_statement,
    _js_initial_state_expression,
    _js_literal,
    _js_runtime_value_expression,
    _normalize_action_operation,
    build_client_script,
)
from lua_spa.trace import _BinaryExpression, _CastReference, _PropReference


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
    def inc(self):
        self.state.count += 1

    def client(self):
        class Props:
            start = 0

        class State:
            count = StateField(name="count", from_prop="start", default=0, cast="int")

        class ClientSpec:
            def inc(self):
                self.state.count += 1

            pass

        ClientSpec.Props = Props
        ClientSpec.State = State
        ClientSpec.Methods = ["inc"]
        return ClientSpec()
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


def test_codegen_additional_runtime_and_action_branches() -> None:
    # Given / When: runtime expressions for floor, pow and plain binary operators
    floor_expr = _js_runtime_value_expression(_BinaryExpression("//", 7, 2), "props")
    pow_expr = _js_runtime_value_expression(_BinaryExpression("**", 2, 3), "props")
    add_expr = _js_runtime_value_expression(_BinaryExpression("+", 2, 3), "props")

    # Then: special operators are compiled to expected JS helpers
    assert "Math.floor" in floor_expr
    assert "Math.pow" in pow_expr
    assert add_expr == "(2 + 3)"

    # Given / When: toggle action and unknown state action
    toggle_stmt = _js_action_statement(
        {"op": "toggle", "state": "enabled", "value": None},
        {"enabled": "setEnabled"},
    )
    assert "!value" in toggle_stmt

    try:
        _js_action_statement({"op": "set", "state": "missing", "value": 1}, {"x": "setX"})
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

    # Given / When: invalid action config and missing state field
    for invalid in ["bad", {"op": "set", "value": 1}, {"op": "multi", "steps": "x"}]:
        try:
            _normalize_action_operation(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError")


def test_codegen_init_and_lifecycle_call_action_branch() -> None:
    # Given: init callable that only supports zero args
    def init_no_args() -> int:
        return 7

    # When: initial state expression is built from init
    expr = _js_initial_state_expression({"init": init_no_args}, "resolvedProps")

    # Then: expression resolves to a JS literal
    assert expr == _js_literal(7)

    # Given: lifecycle with action-name string triggers __callAction branch
    python_block = """
class App(Component):
    def inc(self):
        self.state.count += 1

    def client(self):
        class Props:
            enabled = False
            start = 1

        class State:
            count = StateField(name="count", from_prop="start", default=0, cast="bool")

        class ClientSpec:
            def inc(self):
                self.state.count += 1

            pass

        ClientSpec.Props = Props
        ClientSpec.State = State
        ClientSpec.Methods = ["inc"]
        ClientSpec.Lifecycle = {"onMount": ["inc"]}
        return ClientSpec()
"""

    # When: script is generated
    script = build_client_script(python_block)

    # Then: lifecycle string action invokes __callAction and bool cast is generated
    assert "__callAction(\"inc\")" in script
    assert "Boolean(" in script


def test_codegen_remaining_branches_for_initializers_and_actions() -> None:
    # Given / When: lifecycle mapping operation branch is generated via lifecycle method tracing
    python_block = """
class ClientSpec:
    class State:
        count = 1

    Methods = ["inc"]

    def inc(self):
        self.state.count += 1

    def created(self):
        return {"op": "set", "state": "count", "value": 2}


class App(Component):
    def client(self):
        return ClientSpec()
"""
    script = build_client_script(python_block)
    assert "onCreate" in script
    assert "return 2" in script

    # Given / When: initial state expression branches
    assert _js_initial_state_expression({"default": 4}, "props") == "4"
    assert "Number(" in _js_initial_state_expression(
        {"from_prop": "v", "default": 0, "cast": "float"}, "props"
    )
    assert "String(" in _js_initial_state_expression(
        {"from_prop": "v", "default": "x", "cast": "str"}, "props"
    )
    assert "props" in _js_initial_state_expression(
        {"from_prop": "v", "default": 0, "cast": "raw"}, "props"
    )
    assert _js_initial_state_expression(5, "props") == "5"

    # Given / When: cond passthrough and non-list multi error
    normalized = _normalize_action_operation(
        {"op": "set", "state": "count", "value": 1, "cond": {"left": "count"}}
    )
    assert "cond" in normalized

    try:
        _js_action_statement({"op": "multi", "steps": "bad"}, {"count": "setCount"})
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

    set_stmt = _js_action_statement(
        {"op": "set", "state": "count", "value": 3},
        {"count": "setCount"},
    )
    assert "function ()" in set_stmt

    # Given / When: cast runtime expression branches for int/unknown cast
    assert "Number(" in _js_runtime_value_expression(_CastReference("int", 2), "props")
    assert _js_runtime_value_expression(_CastReference("custom", 2), "props") == "2"
