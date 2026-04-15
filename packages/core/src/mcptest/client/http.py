"""HTTP (streamable) and SSE transport clients."""

from __future__ import annotations

import asyncio
import time
from contextlib import AsyncExitStack
from typing import Any, Literal

import httpx
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamable_http_client

from .base import CallOutcome, ToolInfo

Kind = Literal["http", "sse"]


class HttpClient:
    """Shared implementation for streamable-HTTP and SSE transports.

    The two SDK helpers have nearly identical shapes (yield read/write streams
    consumed by ClientSession); we parameterise on `kind` rather than duplicate.
    """

    def __init__(
        self,
        url: str,
        *,
        kind: Kind = "http",
        headers: dict[str, str] | None = None,
    ) -> None:
        self._url = url
        self._kind: Kind = kind
        self._headers = headers or {}
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None

    async def connect(self) -> None:
        if self._session is not None:
            return
        stack = AsyncExitStack()
        try:
            if self._kind == "http":
                http_client = (
                    httpx.AsyncClient(headers=self._headers) if self._headers else None
                )
                if http_client is not None:
                    await stack.enter_async_context(http_client)
                streams = await stack.enter_async_context(
                    streamable_http_client(self._url, http_client=http_client)
                )
                # streamable_http_client yields (read, write, get_session_id)
                read, write = streams[0], streams[1]
            else:
                read, write = await stack.enter_async_context(
                    sse_client(self._url, headers=self._headers or None)
                )
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
        except Exception:
            await stack.aclose()
            raise
        self._stack = stack
        self._session = session

    async def close(self) -> None:
        if self._stack is None:
            return
        stack, self._stack = self._stack, None
        self._session = None
        await stack.aclose()

    def _require_session(self) -> ClientSession:
        if self._session is None:
            raise RuntimeError("Client is not connected; call connect() first")
        return self._session

    async def list_tools(self) -> list[ToolInfo]:
        session = self._require_session()
        result = await session.list_tools()
        return [
            ToolInfo(
                name=t.name,
                description=t.description,
                input_schema=dict(t.inputSchema or {}),
            )
            for t in result.tools
        ]

    async def call_tool(
        self, name: str, args: dict[str, Any], *, timeout_ms: int | None = None
    ) -> CallOutcome:
        session = self._require_session()
        coro = session.call_tool(name, args)
        start = time.perf_counter()
        try:
            if timeout_ms is not None:
                raw = await asyncio.wait_for(coro, timeout=timeout_ms / 1000)
            else:
                raw = await coro
        except asyncio.TimeoutError:
            elapsed = (time.perf_counter() - start) * 1000
            return CallOutcome(
                is_error=True,
                text=f"Timeout after {timeout_ms}ms",
                structured=None,
                latency_ms=elapsed,
            )
        elapsed = (time.perf_counter() - start) * 1000
        text_parts: list[str] = []
        for block in raw.content or []:
            text = getattr(block, "text", None)
            if text is not None:
                text_parts.append(text)
        structured = getattr(raw, "structuredContent", None)
        return CallOutcome(
            is_error=bool(getattr(raw, "isError", False)),
            text="\n".join(text_parts),
            structured=structured,
            latency_ms=elapsed,
            raw=raw,
        )
