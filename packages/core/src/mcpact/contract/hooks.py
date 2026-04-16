"""Execute before/after hooks defined in contracts."""

from __future__ import annotations

import asyncio
from typing import Any

from ..client.base import McpClient
from .models import HookAction, HookShell, HookToolCall
from .variables import resolve_value


async def run_hooks(
    hooks: list[HookAction],
    client: McpClient,
    step_context: dict[str, Any] | None = None,
) -> None:
    ctx = step_context or {}
    for hook in hooks:
        if isinstance(hook, HookShell):
            await _run_shell(hook.shell)
        elif isinstance(hook, HookToolCall):
            resolved_args = resolve_value(dict(hook.args), ctx)
            await client.call_tool(hook.tool, resolved_args)


async def _run_shell(cmd: str) -> None:
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        msg = stderr.decode(errors="replace").strip() if stderr else ""
        raise RuntimeError(f"hook shell command failed (exit {proc.returncode}): {cmd}\n{msg}")
