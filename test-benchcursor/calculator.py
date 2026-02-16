"""
Object-oriented calculator module with robust error handling.

The design focuses on:
- Clear separation of concerns between operations and the calculator
- Extensibility via pluggable operations
- Safe error handling using custom exception types and try/except blocks
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Protocol


class CalculationError(Exception):
    """Domain-specific error raised when a calculation cannot be completed."""


class Operation(Protocol):
    """Protocol representing a binary numeric operation."""

    def __call__(self, left: float, right: float) -> float:
        ...


@dataclass(frozen=True)
class BinaryOperation:
    """Immutable wrapper around a binary operation function."""

    symbol: str
    func: Callable[[float, float], float]

    def __call__(self, left: float, right: float) -> float:
        """
        Execute the underlying operation while translating low-level
        runtime errors into domain-specific exceptions.
        """
        try:
            return self.func(left, right)
        except ZeroDivisionError as exc:  # Example of specific error mapping
            raise CalculationError("Division by zero is not allowed.") from exc
        except OverflowError as exc:
            raise CalculationError("Numeric overflow during calculation.") from exc
        except Exception as exc:  # Fallback guardrail
            raise CalculationError("Unexpected error while performing operation.") from exc


class Calculator:
    """
    A simple, extensible calculator.

    Operations are stored in a registry that can be extended at runtime.
    All public methods wrap internal errors into CalculationError so callers
    can handle failures in a uniform way.
    """

    def __init__(self) -> None:
        self._operations: Dict[str, BinaryOperation] = {}
        self._register_default_operations()

    # --- Registration API -------------------------------------------------

    def register_operation(self, symbol: str, operation: Operation) -> None:
        """
        Register or override an operation.

        Args:
            symbol: Textual symbol representing the operation (e.g. "+", "-", "*").
            operation: Callable implementing the operation.
        """
        wrapped = (
            operation
            if isinstance(operation, BinaryOperation)
            else BinaryOperation(symbol=symbol, func=operation)
        )
        self._operations[symbol] = wrapped

    def _register_default_operations(self) -> None:
        """Populate the calculator with a standard set of operations."""
        self.register_operation("+", lambda a, b: a + b)
        self.register_operation("-", lambda a, b: a - b)
        self.register_operation("*", lambda a, b: a * b)
        self.register_operation("/", lambda a, b: a / b)
        self.register_operation("^", lambda a, b: a**b)

    # --- Calculation API --------------------------------------------------

    def calculate(self, left: float, right: float, symbol: str) -> float:
        """
        Perform a calculation using the specified operation symbol.

        Raises:
            CalculationError: If the operation is unknown or if any computation
            error occurs.
        """
        try:
            operation = self._operations[symbol]
        except KeyError as exc:
            raise CalculationError(f"Unknown operation symbol: {symbol!r}") from exc

        # Delegate to the BinaryOperation which performs its own error mapping.
        try:
            return operation(left, right)
        except CalculationError:
            # Already mapped to a domain error; just propagate.
            raise
        except Exception as exc:
            # Last-resort safety net in case an operation misbehaves.
            raise CalculationError("Unexpected error during calculation.") from exc

    # --- Convenience helpers ----------------------------------------------

    def add(self, left: float, right: float) -> float:
        return self.calculate(left, right, "+")

    def subtract(self, left: float, right: float) -> float:
        return self.calculate(left, right, "-")

    def multiply(self, left: float, right: float) -> float:
        return self.calculate(left, right, "*")

    def divide(self, left: float, right: float) -> float:
        return self.calculate(left, right, "/")

    def power(self, left: float, right: float) -> float:
        return self.calculate(left, right, "^")


def _parse_operand(raw: str) -> float:
    """
    Safely parse a string into a float, raising CalculationError on failure.
    """
    try:
        return float(raw)
    except ValueError as exc:
        raise CalculationError(f"Invalid numeric value: {raw!r}") from exc


def evaluate_expression(expression: str) -> float:
    """
    Evaluate a very small expression language of the form:

        "<number> <op> <number>"

    Example:
        "3 + 4"
        "10 / 2"

    This is intentionally minimal and meant as a usage example.
    """
    calculator = Calculator()

    try:
        left_str, symbol, right_str = expression.strip().split(maxsplit=2)
    except ValueError as exc:
        raise CalculationError(
            "Expression must be in the form: '<number> <op> <number>'."
        ) from exc

    left = _parse_operand(left_str)
    right = _parse_operand(right_str)
    return calculator.calculate(left, right, symbol)


if __name__ == "__main__":
    # Very small interactive demo for manual runs.
    print("Simple OOP Calculator. Type 'quit' to exit.")
    calc = Calculator()

    while True:
        try:
            raw = input("Enter expression (e.g. 3 + 4): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if raw.lower() in {"quit", "exit"}:
            print("Goodbye.")
            break

        if not raw:
            continue

        try:
            result = evaluate_expression(raw)
        except CalculationError as exc:
            print(f"Error: {exc}")
        except Exception as exc:
            # Final guardrail to avoid crashing the demo loop.
            print(f"Unexpected failure: {exc}")
        else:
            print(f"Result: {result}")

