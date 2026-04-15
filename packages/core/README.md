# mcptest (Python core)

The Python engine and CLI that powers [mcptest](https://github.com/jacquesbagui/mcptest) —
contract testing and regression detection for MCP servers.

See the [repository README](../../README.md) for the overall project description
and user-facing documentation. This file covers contributor-level details for
the Python package only.

## Install

```bash
pip install mcptest
```

## Development

The package uses [`uv`](https://docs.astral.sh/uv/) for a fast local loop:

```bash
cd packages/core
uv venv .venv
uv pip install -e ".[dev]"
```

Then from the repo root:

```bash
packages/core/.venv/bin/ruff check src tests
packages/core/.venv/bin/mypy src
packages/core/.venv/bin/pytest -q
```

## CLI

```bash
mcptest run       --contract contracts/example.yaml
mcptest snapshot  --contract contracts/example.yaml --out .mcptest/baseline.json
mcptest diff      --contract contracts/example.yaml --baseline .mcptest/baseline.json
mcptest validate  --contract contracts/example.yaml
```

Supported reporters for `run`: `console` (default), `json`, `junit`, `html`.
Exit code is `0` when all checks pass, `1` on any failure, `2` on contract
errors.

## Python API

```python
import asyncio
from mcptest import load_contract, build_client, run_contract

async def main() -> None:
    contract = load_contract("contracts/example.yaml")
    client = build_client(contract.server)
    await client.connect()
    try:
        report = await run_contract(contract, client)
    finally:
        await client.close()
    print(f"{report.passed}/{report.total} passed")

asyncio.run(main())
```

## Package layout

```
src/mcptest/
├── cli.py                 # Typer CLI entry point
├── client/                # Transport clients (stdio, http, sse)
├── contract/              # YAML models (Pydantic) + loader + assertion engine
├── report.py              # CheckResult / Report data model
├── reporter/              # console, json, junit, html
└── snapshot/              # capture + diff
```

## License

MIT — see [LICENSE](../../LICENSE).
