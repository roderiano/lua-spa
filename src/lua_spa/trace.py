"""Runtime tracing primitives for capturing state mutations and property access in components.

These classes enable the framework to record method side-effects (state operations)
and property references without modifying the component class itself, by swapping
attributes with proxy objects during method invocation.
"""

from __future__ import annotations

import builtins
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class _TraceCondition:
    """Represents a condition captured during comparison (e.g., count > 10).

    Used to associate conditionals with state operations for JavaScript generation.
    """

    left: str
    op: str
    right: Any


@dataclass(frozen=True)
class _PropReference:
    """Represents a reference to a component prop, captured during method execution.

    Used to track which props are accessed so they can be evaluated at runtime
    on the client side rather than baked into the compiled code.
    """

    name: str
    default: Any = None

    def _binary(self, op: str, other: Any, reverse: bool = False) -> "_BinaryExpression":
        left = other if reverse else self
        right = self if reverse else other
        return _BinaryExpression(op=op, left=left, right=right)

    def __add__(self, other: Any) -> "_BinaryExpression":
        return self._binary("+", other)

    def __radd__(self, other: Any) -> "_BinaryExpression":
        return self._binary("+", other, reverse=True)

    def __sub__(self, other: Any) -> "_BinaryExpression":
        return self._binary("-", other)

    def __rsub__(self, other: Any) -> "_BinaryExpression":
        return self._binary("-", other, reverse=True)

    def __mul__(self, other: Any) -> "_BinaryExpression":
        return self._binary("*", other)

    def __rmul__(self, other: Any) -> "_BinaryExpression":
        return self._binary("*", other, reverse=True)

    def __truediv__(self, other: Any) -> "_BinaryExpression":
        return self._binary("/", other)

    def __rtruediv__(self, other: Any) -> "_BinaryExpression":
        return self._binary("/", other, reverse=True)

    def __floordiv__(self, other: Any) -> "_BinaryExpression":
        return self._binary("//", other)

    def __rfloordiv__(self, other: Any) -> "_BinaryExpression":
        return self._binary("//", other, reverse=True)

    def __mod__(self, other: Any) -> "_BinaryExpression":
        return self._binary("%", other)

    def __rmod__(self, other: Any) -> "_BinaryExpression":
        return self._binary("%", other, reverse=True)

    def __pow__(self, other: Any) -> "_BinaryExpression":
        return self._binary("**", other)

    def __rpow__(self, other: Any) -> "_BinaryExpression":
        return self._binary("**", other, reverse=True)


@dataclass(frozen=True)
class _CastReference:
    """Represents a type-cast operation on a value or prop reference.

    Records the cast type ("int", "float", "str", "bool") so the framework
    can generate appropriate JavaScript coercions at runtime.
    """

    cast: str
    value: Any

    def _binary(self, op: str, other: Any, reverse: bool = False) -> "_BinaryExpression":
        left = other if reverse else self
        right = self if reverse else other
        return _BinaryExpression(op=op, left=left, right=right)

    def __add__(self, other: Any) -> "_BinaryExpression":
        return self._binary("+", other)

    def __radd__(self, other: Any) -> "_BinaryExpression":
        return self._binary("+", other, reverse=True)

    def __sub__(self, other: Any) -> "_BinaryExpression":
        return self._binary("-", other)

    def __rsub__(self, other: Any) -> "_BinaryExpression":
        return self._binary("-", other, reverse=True)

    def __mul__(self, other: Any) -> "_BinaryExpression":
        return self._binary("*", other)

    def __rmul__(self, other: Any) -> "_BinaryExpression":
        return self._binary("*", other, reverse=True)

    def __truediv__(self, other: Any) -> "_BinaryExpression":
        return self._binary("/", other)

    def __rtruediv__(self, other: Any) -> "_BinaryExpression":
        return self._binary("/", other, reverse=True)

    def __floordiv__(self, other: Any) -> "_BinaryExpression":
        return self._binary("//", other)

    def __rfloordiv__(self, other: Any) -> "_BinaryExpression":
        return self._binary("//", other, reverse=True)

    def __mod__(self, other: Any) -> "_BinaryExpression":
        return self._binary("%", other)

    def __rmod__(self, other: Any) -> "_BinaryExpression":
        return self._binary("%", other, reverse=True)

    def __pow__(self, other: Any) -> "_BinaryExpression":
        return self._binary("**", other)

    def __rpow__(self, other: Any) -> "_BinaryExpression":
        return self._binary("**", other, reverse=True)


@dataclass(frozen=True)
class _BinaryExpression:
    """Represents a binary expression captured during tracing."""

    op: str
    left: Any
    right: Any


class _TraceProps:
    """Proxy object for component props during method tracing.

    Returns _PropReference instead of actual values, allowing the framework
    to infer which props are used by a method without executing full logic.
    """

    def __getattr__(self, name: str) -> _PropReference:
        """Return a prop reference when accessed."""
        return _PropReference(name=name)

    def get(self, name: str, default: Any = None) -> _PropReference:
        """Return a prop reference with a default fallback value."""
        return _PropReference(name=name, default=default)


class _TraceStateValue:
    """Represents a state variable during tracing, supporting compound assignments and comparisons.

    When augmented assignment operators (+=, -=) are used on this object,
    it records the operation on its owner _TraceState instead of executing it.
    Comparison operators return True to allow conditional branches in traced methods to execute.
    """

    def __init__(self, name: str, owner: _TraceState) -> None:
        """Initialize a traced state value."""
        self.name = name
        self.owner = owner

    def __iadd__(self, other: Any) -> _TraceStateValue:
        """Record an add operation when state += is used."""
        self.owner.add_operation({"op": "add", "state": self.name, "value": other})
        return self

    def __isub__(self, other: Any) -> _TraceStateValue:
        """Record a sub operation when state -= is used."""
        self.owner.add_operation({"op": "sub", "state": self.name, "value": other})
        return self

    def __lt__(self, other: Any) -> bool:
        """Support < comparison (returns True to execute conditional branches)."""
        self.owner.set_condition(_TraceCondition(self.name, "<", other))
        return True

    def __le__(self, other: Any) -> bool:
        """Support <= comparison (returns True to execute conditional branches)."""
        self.owner.set_condition(_TraceCondition(self.name, "<=", other))
        return True

    def __gt__(self, other: Any) -> bool:
        """Support > comparison (returns True to execute conditional branches)."""
        self.owner.set_condition(_TraceCondition(self.name, ">", other))
        return True

    def __ge__(self, other: Any) -> bool:
        """Support >= comparison (returns True to execute conditional branches)."""
        self.owner.set_condition(_TraceCondition(self.name, ">=", other))
        return True

    def __eq__(self, other: Any) -> bool:
        """Support == comparison (returns True to execute conditional branches)."""
        self.owner.set_condition(_TraceCondition(self.name, "==", other))
        return True

    def __ne__(self, other: Any) -> bool:
        """Support != comparison (returns True to execute conditional branches)."""
        self.owner.set_condition(_TraceCondition(self.name, "!=", other))
        return True

    def __int__(self) -> int:
        """Support int() conversion (returns 0 for tracing)."""
        return 0

    def __float__(self) -> float:
        """Support float() conversion (returns 0.0 for tracing)."""
        return 0.0

    def __str__(self) -> str:
        """Support str() conversion (returns empty string for tracing)."""
        return ""

    def __repr__(self) -> str:
        """Return representation of the traced value."""
        return f"_TraceStateValue({self.name})"


class _TraceState:
    """Proxy object for component state during method tracing.

    Captures state mutations (assignments, compound ops) as operation dicts
    instead of modifying actual state, allowing inference of method behavior
    without executing the logic.
    """

    _operations: list[dict[str, Any]]
    _pending_condition: _TraceCondition | None

    def __init__(self) -> None:
        super().__setattr__("_operations", [])
        super().__setattr__("_pending_condition", None)

    @property
    def operations(self) -> list[dict[str, Any]]:
        """Get the list of recorded state operations."""
        return self._operations

    def set_condition(self, condition: _TraceCondition) -> None:
        """Register a condition from a comparison operation."""
        super().__setattr__("_pending_condition", condition)

    def add_operation(self, operation: dict[str, Any]) -> None:
        """Append an operation dict to the trace, attaching any pending condition."""
        condition = super().__getattribute__("_pending_condition")
        if condition is not None:
            operation["cond"] = {
                "left": condition.left,
                "op": condition.op,
                "right": condition.right,
            }
            super().__setattr__("_pending_condition", None)
        self._operations.append(operation)

    def add_log(self, message: Any) -> None:
        """Append a log operation without consuming pending conditions."""
        self._operations.append({"op": "log", "value": message})

    def __getattr__(self, name: str) -> _TraceStateValue:
        """Return a trace state value when accessed."""
        return _TraceStateValue(name=name, owner=self)

    def __setattr__(self, name: str, value: Any) -> None:
        """Record a set operation when state.x = value is used."""
        if name.startswith("_"):
            super().__setattr__(name, value)
            return

        if isinstance(value, _TraceStateValue) and value.name == name:
            return

        self.add_operation({"op": "set", "state": name, "value": value})


def _py_int(value: Any = 0) -> Any:
    """Builtin int() wrapper that captures casts on prop/cast references.

    If value is a _PropReference or _CastReference, return a _CastReference("int", value).
    Otherwise, return the normal int() cast.
    """
    if isinstance(value, (_PropReference, _CastReference)):
        return _CastReference(cast="int", value=value)
    return builtins.int(value)


def _py_float(value: Any = 0) -> Any:
    """Builtin float() wrapper that captures casts on prop/cast references."""
    if isinstance(value, (_PropReference, _CastReference)):
        return _CastReference(cast="float", value=value)
    return builtins.float(value)


def _py_str(value: Any = "") -> Any:
    """Builtin str() wrapper that captures casts on prop/cast references."""
    if isinstance(value, (_PropReference, _CastReference)):
        return _CastReference(cast="str", value=value)
    return builtins.str(value)


def _py_bool(value: Any = False) -> Any:
    """Builtin bool() wrapper that captures casts on prop/cast references."""
    if isinstance(value, (_PropReference, _CastReference)):
        return _CastReference(cast="bool", value=value)
    return builtins.bool(value)
