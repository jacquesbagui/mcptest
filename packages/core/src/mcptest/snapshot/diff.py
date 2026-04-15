"""Compare two snapshots and classify the differences."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .capture import Snapshot


class DiffKind(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    CHANGED = "changed"


@dataclass(frozen=True)
class DiffEntry:
    tool: str
    kind: DiffKind
    details: list[str] = field(default_factory=list)

    @property
    def breaking(self) -> bool:
        """Removals and required/type changes break consumers; additions don't."""
        if self.kind is DiffKind.REMOVED:
            return True
        if self.kind is DiffKind.CHANGED:
            return any(
                d.startswith(("required ", "type ", "property removed"))
                for d in self.details
            )
        return False


@dataclass(frozen=True)
class SnapshotDiff:
    entries: list[DiffEntry]

    @property
    def has_changes(self) -> bool:
        return bool(self.entries)

    @property
    def has_breaking(self) -> bool:
        return any(e.breaking for e in self.entries)


def diff_snapshots(baseline: Snapshot, current: Snapshot) -> SnapshotDiff:
    base = baseline.tools
    cur = current.tools
    entries: list[DiffEntry] = []

    for name in sorted(set(base) - set(cur)):
        entries.append(DiffEntry(name, DiffKind.REMOVED))
    for name in sorted(set(cur) - set(base)):
        entries.append(DiffEntry(name, DiffKind.ADDED))

    for name in sorted(set(base) & set(cur)):
        details = _diff_tool(base[name], cur[name])
        if details:
            entries.append(DiffEntry(name, DiffKind.CHANGED, details))

    return SnapshotDiff(entries)


def _diff_tool(base: dict[str, Any], current: dict[str, Any]) -> list[str]:
    details: list[str] = []
    if base.get("description") != current.get("description"):
        details.append("description changed")

    b_schema = base.get("input_schema") or {}
    c_schema = current.get("input_schema") or {}

    b_req = set(b_schema.get("required", []) or [])
    c_req = set(c_schema.get("required", []) or [])
    for r in sorted(b_req - c_req):
        details.append(f"required removed: {r}")
    for r in sorted(c_req - b_req):
        details.append(f"required added: {r}")

    b_props = b_schema.get("properties", {}) or {}
    c_props = c_schema.get("properties", {}) or {}
    for p in sorted(set(b_props) - set(c_props)):
        details.append(f"property removed: {p}")
    for p in sorted(set(c_props) - set(b_props)):
        details.append(f"property added: {p}")
    for p in sorted(set(b_props) & set(c_props)):
        b_type = b_props[p].get("type")
        c_type = c_props[p].get("type")
        if b_type != c_type:
            details.append(f"type changed on {p}: {b_type!r} → {c_type!r}")

    return details
