"""Capture a snapshot of an MCP server's tool surface."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..client.base import McpClient

SNAPSHOT_VERSION = 1


@dataclass(frozen=True)
class Snapshot:
    """Stable, comparable record of a server's exposed tools.

    Schemas are stored as-is (already JSON-compatible dicts), so diffs can
    surface additions, removals, and precise structural changes.
    """

    version: int
    captured_at: str
    server: str | None
    tools: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "captured_at": self.captured_at,
            "server": self.server,
            "tools": self.tools,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Snapshot:
        return cls(
            version=int(data.get("version", SNAPSHOT_VERSION)),
            captured_at=str(data.get("captured_at", "")),
            server=data.get("server"),
            tools=dict(data.get("tools", {})),
        )


async def capture_snapshot(client: McpClient, server_name: str | None = None) -> Snapshot:
    tools = await client.list_tools()
    payload = {
        t.name: {
            "description": t.description,
            "input_schema": t.input_schema,
        }
        for t in sorted(tools, key=lambda x: x.name)
    }
    return Snapshot(
        version=SNAPSHOT_VERSION,
        captured_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        server=server_name,
        tools=payload,
    )


def save_snapshot(snapshot: Snapshot, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(snapshot.to_dict(), indent=2, sort_keys=True), encoding="utf-8")


def load_snapshot(path: str | Path) -> Snapshot:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid snapshot file: {p}")
    return Snapshot.from_dict(data)
