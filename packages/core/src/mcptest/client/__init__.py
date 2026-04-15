import sys
import tempfile
from typing import TextIO

from ..contract.models import ServerConfig
from .base import CallOutcome, McpClient, ToolInfo
from .http import HttpClient
from .stdio import StdioClient


def build_client(config: ServerConfig, *, verbose: bool = False) -> McpClient:
    """Construct the right client for a given server config.

    For stdio transports, `verbose=True` streams the child's stderr to the
    parent's terminal; `verbose=False` (default) captures it into a temp
    file (the subprocess layer requires a real file descriptor) so the
    caller can surface it on connection failure without polluting output.
    """
    if config.transport == "stdio":
        assert config.command is not None
        # TemporaryFile lifetime is tied to the client — ruff SIM115 is a false positive here.
        errlog: TextIO = (
            sys.stderr
            if verbose
            else tempfile.TemporaryFile(mode="w+", encoding="utf-8")  # noqa: SIM115
        )
        return StdioClient(
            command=config.command,
            args=list(config.args) or None,
            env=dict(config.env) or None,
            cwd=config.cwd,
            errlog=errlog,
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
