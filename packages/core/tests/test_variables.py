import pytest

from mcpact.contract.variables import VariableError, resolve_value


def _ctx() -> dict:
    return {
        "create": {
            "text": '{"id": "abc123", "title": "hello"}',
            "structured": {"id": "abc123", "title": "hello"},
            "is_error": False,
        },
        "list": {
            "text": "[]",
            "structured": {"result": [{"id": "abc123"}]},
            "is_error": False,
        },
    }


def test_no_variable() -> None:
    assert resolve_value("hello", {}) == "hello"
    assert resolve_value(42, {}) == 42
    assert resolve_value({"a": 1}, {}) == {"a": 1}


def test_full_replacement_preserves_type() -> None:
    ctx = _ctx()
    result = resolve_value("${{ steps.create.result }}", ctx)
    assert isinstance(result, dict)
    assert result["id"] == "abc123"


def test_nested_path() -> None:
    ctx = _ctx()
    assert resolve_value("${{ steps.create.result.id }}", ctx) == "abc123"


def test_list_index() -> None:
    ctx = _ctx()
    assert resolve_value("${{ steps.list.result.result.0.id }}", ctx) == "abc123"


def test_string_interpolation() -> None:
    ctx = _ctx()
    result = resolve_value("User ID is ${{ steps.create.result.id }}", ctx)
    assert result == "User ID is abc123"


def test_multiple_refs_in_string() -> None:
    ctx = _ctx()
    result = resolve_value(
        "${{ steps.create.result.id }} - ${{ steps.create.result.title }}", ctx
    )
    assert result == "abc123 - hello"


def test_resolve_in_dict() -> None:
    ctx = _ctx()
    result = resolve_value({"user_id": "${{ steps.create.result.id }}"}, ctx)
    assert result == {"user_id": "abc123"}


def test_resolve_in_list() -> None:
    ctx = _ctx()
    result = resolve_value(["${{ steps.create.result.id }}"], ctx)
    assert result == ["abc123"]


def test_missing_step_raises() -> None:
    with pytest.raises(VariableError, match="step 'nope' not found"):
        resolve_value("${{ steps.nope.result }}", {})


def test_missing_path_segment_raises() -> None:
    ctx = _ctx()
    with pytest.raises(VariableError, match="path segment"):
        resolve_value("${{ steps.create.result.nonexistent }}", ctx)


def test_fallback_to_text_json() -> None:
    ctx = {"txt": {"text": '{"x": 42}', "structured": None, "is_error": False}}
    assert resolve_value("${{ steps.txt.result.x }}", ctx) == 42


def test_fallback_to_raw_text() -> None:
    ctx = {"txt": {"text": "plain string", "structured": None, "is_error": False}}
    assert resolve_value("${{ steps.txt.result }}", ctx) == "plain string"
