from ..contract.models import ServerConfig
from .base import CallOutcome, McpClient, ToolInfo
from .http import HttpClient
from .stdio import StdioClient


def build_client(config: ServerConfig) -> McpClient:
    """Construct the right client for a given server config."""
    if config.transport == "stdio":
        assert config.command is not None
        return StdioClient(
            command=config.command,
            args=list(config.args) or None,
            env=dict(config.env) or None,
            cwd=config.cwd,
        )
    if config.transport in ("http", "sse"):
        assert config.url is not None
        return HttpClient(config.url, kind=config.transport)
    raise NotImplementedError(f"Transport '{config.transport}' is not implemented yet")


__all__ = [
    "CallOutcome",
    "HttpClient",
    "McpClient",
    "StdioClient",
    "ToolInfo",
    "build_client",
]
