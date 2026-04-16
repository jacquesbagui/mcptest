"""Minimal MCP server used by tests and the quickstart example."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("toy")

# ---------- resources ----------

@mcp.resource("config://version")
def config_version() -> str:
    """The server's version string."""
    return '{"version": "0.1.0", "name": "toy"}'


# ---------- prompts ----------

@mcp.prompt()
def greet(name: str) -> str:
    """Generate a greeting for the given name."""
    return f"Hello, {name}! Welcome to the toy MCP server."


# ---------- tools ----------

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
    import os
    import sys

    # Usage:
    #   python toy_server.py                 # stdio (default)
    #   python toy_server.py http [port]     # streamable HTTP
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    if transport == "http":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else int(os.environ.get("PORT", "0"))
        mcp.settings.host = "127.0.0.1"
        mcp.settings.port = port or 3000
        mcp.run(transport="streamable-http")
    else:
        mcp.run()
