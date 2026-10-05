"""Restricted workflow value and output-text placeholder resolution."""

import re
import json

from dbeeapp.errors import ValidationError

_PLACEHOLDER = re.compile(r"\{\{\s*([A-Za-z][A-Za-z0-9_.-]*)\s*\}\}")


def _lookup(path, context):
    parts = path.split(".")
    if parts[0] not in {"vars", "steps"}:
        raise ValidationError("unsupported template reference namespace")
    current = context
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, (list, tuple)) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            raise ValidationError("template reference is not available: {}".format(path))
    return current


def resolve_value(value, context):
    """Resolve a full scalar placeholder while preserving its Python type."""
    if not isinstance(value, str):
        if isinstance(value, list):
            return [resolve_value(item, context) for item in value]
        if isinstance(value, dict):
            return {key: resolve_value(item, context) for key, item in value.items()}
        return value
    match = _PLACEHOLDER.fullmatch(value)
    if match:
        return _lookup(match.group(1), context)
    if "{{" in value or "}}" in value:
        raise ValidationError("only complete placeholders are supported here")
    return value


def render_text(text, context, result=None):
    """Render literal output text with simple placeholders only."""
    output_context = dict(context)
    output_context["result"] = result
    if not isinstance(text, str):
        raise ValidationError("output text must be a string")

    def replace(match):
        path = match.group(1)
        if path == "result":
            value = result
        elif path.startswith(("vars.", "steps.")):
            value = _lookup(path, context)
        else:
            raise ValidationError("unsupported output placeholder")
        if value is None:
            return ""
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(value, default=str, ensure_ascii=False, separators=(",", ":"))
        return str(value)

    rendered = _PLACEHOLDER.sub(replace, text)
    if "{{" in rendered or "}}" in rendered:
        raise ValidationError("invalid output placeholder")
    return rendered