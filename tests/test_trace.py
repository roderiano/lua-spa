from __future__ import annotations

from lua_spa.trace import (
    _CastReference,
    _PropReference,
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
