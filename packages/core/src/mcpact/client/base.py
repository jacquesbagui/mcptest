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


@dataclass(frozen=True)
class ResourceInfo:
    uri: str
    name: str | None
    description: str | None
    mime_type: str | None


@dataclass(frozen=True)
class ResourceContent:
    uri: str
    text: str
    mime_type: str | None


@dataclass(frozen=True)
class PromptArgInfo:
    name: str
    description: str | None
    required: bool


@dataclass(frozen=True)
class PromptInfo:
    name: str
    description: str | None
    arguments: list[PromptArgInfo] = field(default_factory=list)


@dataclass(frozen=True)
class PromptMessage:
    role: str
    text: str


@dataclass(frozen=True)
class PromptResult:
    description: str | None
    messages: list[PromptMessage] = field(default_factory=list)


class McpClient(Protocol):
    async def connect(self) -> None: ...
    async def close(self) -> None: ...
    async def list_tools(self) -> list[ToolInfo]: ...
    async def call_tool(
        self, name: str, args: dict[str, Any], *, timeout_ms: int | None = None
    ) -> CallOutcome: ...
    async def list_resources(self) -> list[ResourceInfo]: ...
    async def read_resource(self, uri: str) -> ResourceContent: ...
    async def list_prompts(self) -> list[PromptInfo]: ...
    async def get_prompt(self, name: str, args: dict[str, Any]) -> PromptResult: ...
