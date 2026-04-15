"""Minimal MCP server used by tests and the quickstart example."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("toy")


@mcp.tool()
def echo(message: str) -> str:
    """Echo back the provided message."""
    return message


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two integers and return the sum."""
    return a + b


@mcp.tool()
def boom() -> str:
    """Always raises — used to exercise error-path assertions."""
    raise RuntimeError("kaboom")


if __name__ == "__main__":
    mcp.run()
