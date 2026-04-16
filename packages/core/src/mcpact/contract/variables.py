"""Resolve ${{ steps.<name>.result.<path> }} references in contract values."""

from __future__ import annotations

import json
import re
from typing import Any

_VAR_RE = re.compile(r"\$\{\{\s*steps\.(\w+)\.result((?:\.\w+)*)\s*\}\}")


class VariableError(Exception):
    pass


def _walk_path(obj: Any, path: list[str]) -> Any:
    current = obj
    for segment in path:
        if isinstance(current, dict):
            if segment not in current:
                raise VariableError(f"path segment '{segment}' not found in {list(current.keys())}")
            current = current[segment]
        elif isinstance(current, list):
            try:
                current = current[int(segment)]
            except (ValueError, IndexError) as e:
                raise VariableError(f"invalid list index '{segment}'") from e
        else:
            raise VariableError(f"cannot traverse into {type(current).__name__} with '{segment}'")
    return current


def _extract_result(outcome_data: Any) -> Any:
    """Get a traversable result from a step's stored data.

    Prefers structured content (already a dict/list). Falls back to parsing
    text as JSON. Returns raw text if that also fails.
    """
    if isinstance(outcome_data, dict):
        structured = outcome_data.get("structured")
        if structured is not None:
            return structured
        text = outcome_data.get("text", "")
        if text:
            try:
                return json.loads(text)
            except (json.JSONDecodeError, TypeError):
                pass
        return text
    return outcome_data


def resolve_value(template: Any, context: dict[str, Any]) -> Any:
    """Resolve variable references in a single value.

    If the entire value is a single variable reference, preserves the resolved
    type (dict, list, int, etc.). Otherwise string-interpolates.
    """
    if not isinstance(template, str):
        if isinstance(template, dict):
            return {k: resolve_value(v, context) for k, v in template.items()}
        if isinstance(template, list):
            return [resolve_value(v, context) for v in template]
        return template

    match = _VAR_RE.fullmatch(template)
    if match:
        return _resolve_single(match, context)

    def _replacer(m: re.Match[str]) -> str:
        return str(_resolve_single(m, context))

    return _VAR_RE.sub(_replacer, template)


def _resolve_single(match: re.Match[str], context: dict[str, Any]) -> Any:
    step_name = match.group(1)
    path_str = match.group(2)

    if step_name not in context:
        raise VariableError(f"step '{step_name}' not found; available: {list(context.keys())}")

    result = _extract_result(context[step_name])
    if not path_str:
        return result

    path = [s for s in path_str.split(".") if s]
    return _walk_path(result, path)
