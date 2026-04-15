"""End-to-end test over streamable HTTP transport."""

from __future__ import annotations

import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from mcptest.client.http import HttpClient
from mcptest.contract.engine import run_contract
from mcptest.contract.models import (
    Assertion,
    CallSpec,
    Contract,
    Expectation,
    ServerConfig,
    ToolSpec,
)

REPO = Path(__file__).resolve().parents[3]
TOY_SERVER = REPO / "packages/core/examples/toy_server.py"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _wait_for_port(port: int, timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.1)
    raise TimeoutError(f"server on :{port} did not open in {timeout}s")


def _wait_for_mcp(port: int, timeout: float = 10.0) -> None:
    """FastMCP may open the port before the MCP endpoint is ready; poll /mcp."""
    url = f"http://127.0.0.1:{port}/mcp"
    deadline = time.time() + timeout
    last: Exception | None = None
    while time.time() < deadline:
        try:
            # GET /mcp without accepting SSE returns 4xx quickly but confirms liveness.
            urllib.request.urlopen(url, timeout=0.5)
            return
        except urllib.error.HTTPError:
            return  # endpoint exists
        except Exception as e:
            last = e
            time.sleep(0.1)
    raise TimeoutError(f"MCP endpoint :{port}/mcp not reachable: {last}")


@pytest.mark.asyncio
async def test_http_transport_lists_tools_and_calls() -> None:
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, str(TOY_SERVER), "http", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_port(port)
        _wait_for_mcp(port)

        contract = Contract(
            server=ServerConfig(transport="http", url=f"http://127.0.0.1:{port}/mcp"),
            tools=[
                ToolSpec(
                    name="echo",
                    must_exist=True,
                    assertions=[
                        Assertion(
                            call=CallSpec(args={"message": "hi-http"}),
                            expect=Expectation(status="success", response_contains="hi-http"),
                        )
                    ],
                ),
            ],
        )

        client = HttpClient(contract.server.url or "", kind="http")
        try:
            await client.connect()
            report = await run_contract(contract, client)
        finally:
            await client.close()

        assert report.failed == 0, [
            (c.tool, c.check, c.message) for c in report.checks if c.status.value == "fail"
        ]
        assert report.passed > 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
