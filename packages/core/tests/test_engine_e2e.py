"""End-to-end test: spawn the toy MCP server and run the example contract."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

from mcptest.client import build_client
from mcptest.contract import load_contract
from mcptest.contract.engine import run_contract

REPO = Path(__file__).resolve().parents[3]
TOY_SERVER = REPO / "packages/core/examples/toy_server.py"


@pytest.mark.asyncio
async def test_example_contract_passes() -> None:
    if shutil.which("python") is None:
        pytest.skip("python not on PATH")
    contract = load_contract(REPO / "contracts/example.yaml")
    # Pin to the current interpreter so the toy server uses the same env.
    contract = contract.model_copy(
        update={
            "server": contract.server.model_copy(
                update={"command": sys.executable, "args": [str(TOY_SERVER)]}
            )
        }
    )
    client = build_client(contract.server)
    try:
        await client.connect()
        report = await run_contract(contract, client)
    finally:
        await client.close()

    assert report.failed == 0, [
        (c.tool, c.check, c.message) for c in report.checks if c.status.value == "fail"
    ]
    assert report.passed > 0
