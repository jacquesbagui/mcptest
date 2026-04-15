"""Pydantic models for the mcpact contract YAML schema."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Transport = Literal["stdio", "http", "sse"]
AssertStatus = Literal["success", "error"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ServerConfig(StrictModel):
    name: str | None = None
    transport: Transport = "stdio"
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    url: str | None = None
    cwd: str | None = None

    @model_validator(mode="after")
    def _validate_transport(self) -> ServerConfig:
        if self.transport == "stdio" and not self.command:
            raise ValueError("server.command is required for stdio transport")
        if self.transport in ("http", "sse") and not self.url:
            raise ValueError(f"server.url is required for {self.transport} transport")
        return self


class InputSchemaAssertion(StrictModel):
    required: list[str] = Field(default_factory=list)
    properties: dict[str, dict[str, Any]] = Field(default_factory=dict)


class CallSpec(StrictModel):
    args: dict[str, Any] = Field(default_factory=dict)
    timeout_ms: int | None = None


class Expectation(StrictModel):
    status: AssertStatus = "success"
    response_contains: str | list[str] | None = None
    max_latency_ms: int | None = None
    schema_: dict[str, Any] | None = Field(default=None, alias="schema")

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class Assertion(StrictModel):
    call: CallSpec
    expect: Expectation = Expectation()


class ToolSpec(StrictModel):
    name: str
    must_exist: bool = True
    description_contains: str | list[str] | None = None
    input_schema: InputSchemaAssertion | None = None
    assertions: list[Assertion] = Field(default_factory=list)


class SnapshotConfig(StrictModel):
    enabled: bool = False
    baseline: str = ".mcpact/baseline.json"
    fail_on_regression: bool = True
    warn_on_addition: bool = False


class Contract(StrictModel):
    server: ServerConfig
    tools: list[ToolSpec] = Field(default_factory=list)
    snapshots: SnapshotConfig = SnapshotConfig()
