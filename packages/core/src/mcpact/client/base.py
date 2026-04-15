"""Transport-agnostic MCP client interface used by the engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ToolInfo:
    name: str
    description: str | None
    input_schema: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CallOutcome:
    """Normalised result of calling a tool, regardless of transport."""

    is_error: bool
    text: str
    structured: Any | None
    latency_ms: float
    raw: Any = None


class McpClient(Protocol):
    async def connect(self) -> None: ...
    async def close(self) -> None: ...
    async def list_tools(self) -> list[ToolInfo]: ...
    async def call_tool(
        self, name: str, args: dict[str, Any], *, timeout_ms: int | None = None
    ) -> CallOutcome: ...
