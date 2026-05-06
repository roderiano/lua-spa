from __future__ import annotations

from moon_spa.trace import (
    _CastReference,
    _PropReference,
    _TraceCondition,
    _TraceProps,
    _TraceState,
    _py_bool,
    _py_float,
    _py_int,
    _py_str,
)


def test_trace_prop_and_cast_binary_overloads() -> None:
    # Given: property and cast references used in traced expressions
    prop = _PropReference("p", 1)
    cast = _CastReference("int", prop)

    # When: arithmetic operators are applied in both directions
    exprs = [
        prop + 1,
        1 + prop,
        prop - 1,
        1 - prop,
        prop * 2,
        2 * prop,
        prop / 2,
        2 / prop,
        prop // 2,
        2 // prop,
        prop % 2,
        2 % prop,
        prop**2,
        2**prop,
        cast + 1,
        1 + cast,
        cast - 1,
        1 - cast,
        cast * 2,
        2 * cast,
        cast / 2,
        2 / cast,
        cast // 2,
        2 // cast,
        cast % 2,
        2 % cast,
        cast**2,
        2**cast,
    ]

    # Then: all generated expressions are trace operation objects
    assert all(hasattr(expr, "op") for expr in exprs)


def test_trace_state_operations_and_cast_helpers() -> None:
    # Given: trace props and trace state objects
    props = _TraceProps()

    # When: values are retrieved, compared, and cast
    ref = props.get("value", 1)
    assert ref.name == "value"

    state = _TraceState()
    value = state.counter
    value += 1
    value -= 1
    _ = value < 1
    _ = value <= 1
    _ = value > 1
    _ = value >= 1
    _ = value == 1
    _ = value != 1
    assert int(value) == 0
    assert float(value) == 0.0
    assert str(value) == ""
    assert "_TraceStateValue" in repr(value)

    # Then: cast helper wrappers return cast references
    assert isinstance(_py_int(ref), _CastReference)
    assert isinstance(_py_float(ref), _CastReference)
    assert isinstance(_py_str(ref), _CastReference)
    assert isinstance(_py_bool(ref), _CastReference)


def test_trace_additional_paths_for_conditions_and_plain_casts() -> None:
    # Given: trace props/state and plain values for cast wrappers
    props = _TraceProps()
    _ = props.foo
    state = _TraceState()

    # When: a pending condition is attached to the next operation
    state.set_condition(_TraceCondition("count", ">", 1))
    state.add_operation({"op": "add", "state": "count", "value": 2})

    # Then: conditional metadata is injected and pending condition is consumed
    assert state.operations[0]["cond"]["left"] == "count"

    # When / Then: plain Python values still use built-in casts
    assert _py_int("2") == 2
    assert _py_float("2.5") == 2.5
    assert _py_str(123) == "123"
    assert _py_bool(1) is True

    # When / Then: __setattr__ handles private attrs and explicit set operations
    state._private = 1  # type: ignore[attr-defined]
    state.total = 10  # type: ignore[attr-defined]
    assert state.operations[-1]["op"] == "set"
