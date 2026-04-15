"""stdio transport client built on the official `mcp` SDK."""

from __future__ import annotations

import asyncio
import io
import os
import shlex
import sys
import time
from contextlib import AsyncExitStack
from typing import Any, TextIO

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .base import CallOutcome, ToolInfo


class StdioClient:
    """Thin async wrapper around `mcp.ClientSession` over stdio.

    Manages the lifecycle of the subprocess and session with a single
    AsyncExitStack so `close()` unwinds everything deterministically.
    """

    def __init__(
        self,
        command: str,
        args: list[str] | None = None,
        *,
        env: dict[str, str] | None = None,
        cwd: str | None = None,
        errlog: TextIO | None = None,
    ) -> None:
        """If `errlog` is None, the child's stderr is forwarded to ours."""
        if args is None:
            parts = shlex.split(command)
            if not parts:
                raise ValueError("command must not be empty")
            command, args = parts[0], parts[1:]
        self._command = command
        self._args = args
        self._env = {**os.environ, **(env or {})} if env else None
        self._cwd = cwd
        self._errlog: TextIO = errlog if errlog is not None else sys.stderr
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None

    @property
    def captured_stderr(self) -> str:
        """Return stderr collected so far if a seekable sink was provided, else ''."""
        buf = self._errlog
        if buf is sys.stderr:
            return ""
        try:
            buf.flush()
            buf.seek(0)
            return buf.read()
        except (OSError, io.UnsupportedOperation, ValueError):
            return ""

    async def connect(self) -> None:
        if self._session is not None:
            return
        stack = AsyncExitStack()
        try:
            params = StdioServerParameters(
                command=self._command, args=self._args, env=self._env, cwd=self._cwd
            )
            read, write = await stack.enter_async_context(stdio_client(params, errlog=self._errlog))
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

    async def __aenter__(self) -> StdioClient:
        await self.connect()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

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
