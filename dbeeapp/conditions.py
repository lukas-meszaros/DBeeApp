"""Small declarative condition evaluator."""

from dbeeapp.errors import ValidationError
from dbeeapp.resolver import resolve_value


def evaluate_condition(condition, context):
    """Evaluate a validated condition without evaluating arbitrary code."""
    if not isinstance(condition, dict) or len(condition) != 1:
        raise ValidationError("condition must contain exactly one operator")
    operator, operands = next(iter(condition.items()))
    if operator in {"equals", "not_equals", "greater_than", "greater_than_or_equal", "less_than", "less_than_or_equal", "contains"}:
        left = resolve_value(operands["left"], context)
        right = resolve_value(operands["right"], context)
        try:
            if operator == "equals":
                return left == right
            if operator == "not_equals":
                return left != right
            if operator == "greater_than":
                return left > right
            if operator == "greater_than_or_equal":
                return left >= right
            if operator == "less_than":
                return left < right
            if operator == "less_than_or_equal":
                return left <= right
            return right in left
        except (TypeError, ValueError):
            raise ValidationError("condition operands have incompatible values") from None
    if operator in {"empty", "not_empty"}:
        value = resolve_value(operands, context)
        empty = value is None or value == "" or value == [] or value == {}
        return empty if operator == "empty" else not empty
    if operator in {"success", "failure"}:
        status = resolve_value(operands, context)
        expected_status = "success" if operator == "success" else "failure"
        return status == expected_status
    if operator == "row_count":
        actual = context["steps"][operands["step"]].get("row_count")
        expected = operands["value"]
        comparisons = {
            "eq": lambda: actual == expected,
            "ne": lambda: actual != expected,
            "gt": lambda: actual > expected,
            "gte": lambda: actual >= expected,
            "lt": lambda: actual < expected,
            "lte": lambda: actual <= expected,
        }
        if actual is None:
            raise ValidationError("row_count is unavailable for referenced step")
        return comparisons[operands["operator"]]()
    raise ValidationError("unsupported condition operator")