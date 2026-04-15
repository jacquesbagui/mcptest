from mcpcheck.snapshot import Snapshot, diff_snapshots
from mcpcheck.snapshot.capture import SNAPSHOT_VERSION


def _snap(tools: dict) -> Snapshot:
    return Snapshot(version=SNAPSHOT_VERSION, captured_at="t", server=None, tools=tools)


def test_diff_detects_added_and_removed() -> None:
    base = _snap({"a": {"description": "A", "input_schema": {}}})
    cur = _snap({"b": {"description": "B", "input_schema": {}}})
    diff = diff_snapshots(base, cur)
    kinds = {(e.tool, e.kind.value) for e in diff.entries}
    assert kinds == {("a", "removed"), ("b", "added")}
    assert diff.has_breaking  # removal is breaking


def test_diff_detects_schema_changes() -> None:
    base = _snap(
        {
            "t": {
                "description": "d",
                "input_schema": {
                    "required": ["x"],
                    "properties": {"x": {"type": "string"}, "y": {"type": "integer"}},
                },
            }
        }
    )
    cur = _snap(
        {
            "t": {
                "description": "d",
                "input_schema": {
                    "required": [],
                    "properties": {"x": {"type": "integer"}},
                },
            }
        }
    )
    diff = diff_snapshots(base, cur)
    [entry] = diff.entries
    assert entry.kind.value == "changed"
    assert any("required removed: x" in d for d in entry.details)
    assert any("property removed: y" in d for d in entry.details)
    assert any("type changed on x" in d for d in entry.details)
    assert entry.breaking


def test_diff_addition_only_not_breaking() -> None:
    base = _snap({"a": {"description": "A", "input_schema": {}}})
    cur = _snap(
        {
            "a": {"description": "A", "input_schema": {}},
            "b": {"description": "B", "input_schema": {}},
        }
    )
    diff = diff_snapshots(base, cur)
    assert diff.has_changes
    assert not diff.has_breaking
