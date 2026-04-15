# mcpact

Contract testing for MCP servers.

[![CI](https://github.com/jacquesbagui/mcpact/actions/workflows/ci.yml/badge.svg)](https://github.com/jacquesbagui/mcpact/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/mcpact.svg)](https://pypi.org/project/mcpact/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

You build an MCP server. You change something. How do you know the tools still
work and the schemas haven't drifted? mcpact gives you a YAML contract, runs
it against your running server, and fails CI when something breaks.

## Install

```bash
pip install mcpact
```

Requires Python 3.10+.

## A minimal contract

```yaml
# contracts/my-server.yaml
server:
  transport: stdio
  command: python server.py

tools:
  - name: search_files
    description_contains: search
    input_schema:
      required: [query]
      properties:
        query: { type: string }
    assertions:
      - call:
          args: { query: "hello" }
        expect:
          status: success
          max_latency_ms: 1000
```

Run it:

```bash
mcpact run --contract contracts/my-server.yaml
```

```
search_files
  ✓ exists
  ✓ description_contains
  ✓ input_schema.required
  ✓ call#1.status [42ms]
  ✓ call#1.max_latency_ms [42ms]

5 checks · 5 passed · 0 failed
```

Exit code is `0` on success, `1` on any failure, `2` on contract errors.

## Detect regressions

Capture the current surface, then compare future runs against it:

```bash
mcpact snapshot --contract contracts/my-server.yaml --out .mcpact/baseline.json
mcpact diff     --contract contracts/my-server.yaml --baseline .mcpact/baseline.json
```

```
Snapshot diff:
  + get_file_info          (new tool)
  - delete_file            (removed — breaking)
  ✗ search_files
    └─ required removed: limit
    └─ type changed on query: 'string' → 'integer'
```

`diff` exits non-zero on breaking changes (removed tools, removed required
fields, changed property types) so you can wire it into CI.

## Transports

```yaml
server:
  transport: stdio     # command: python server.py
  transport: http      # url: http://localhost:3000/mcp
  transport: sse       # url: http://localhost:3000/sse
```

## Commands

| Command | Purpose |
|---|---|
| `mcpact run`      | Run a contract against a server |
| `mcpact watch`    | Re-run the contract on file changes |
| `mcpact snapshot` | Write the server's tool surface to a JSON file |
| `mcpact diff`     | Compare a live server against a snapshot |
| `mcpact validate` | Validate a contract file without running it |

Reporters for `run`: `console` (default), `json`, `junit`, `html`. Output goes
to `--out` when provided, otherwise to stdout.

For a realistic example, see
[`packages/core/examples/notes_server.py`](packages/core/examples/notes_server.py)
and the matching contract [`contracts/notes.yaml`](contracts/notes.yaml) — a
tiny notes MCP server exercising `list`, `read`, `search`, and `create` tools.

## GitHub Actions

```yaml
- run: pip install mcpact
- run: mcpact run --contract contracts/my-server.yaml --reporter junit --out results.xml
- uses: mikepenz/action-junit-report@v4
  if: always()
  with:
    report_paths: results.xml
```

## Python API

```python
import asyncio
from mcpact import build_client, load_contract, run_contract

async def main() -> None:
    contract = load_contract("contracts/my-server.yaml")
    client = build_client(contract.server)
    await client.connect()
    try:
        report = await run_contract(contract, client)
    finally:
        await client.close()
    print(f"{report.passed}/{report.total} passed")

asyncio.run(main())
```

## Contract reference

```yaml
server:
  transport: stdio | http | sse
  command: <cmd>           # stdio only
  args: [<arg>, ...]       # stdio only
  env: { KEY: value }      # stdio only
  url: <url>               # http/sse only

tools:
  - name: <tool>
    must_exist: true       # default
    description_contains: <str> | [<str>, ...]
    input_schema:
      required: [<field>, ...]
      properties:
        <field>: { type: string|integer|... }
    assertions:
      - call:
          args: { ... }
          timeout_ms: <int>
        expect:
          status: success | error    # default: success
          response_contains: <str> | [<str>, ...]
          max_latency_ms: <int>
          schema: { ... }            # JSON Schema for the response
```

## Status

Pre-1.0. Both packages are functional and tested against a real MCP server.
API may still change before 1.0.

## Repository layout

```
packages/core/        Python engine + CLI
packages/sdk-node/    TypeScript SDK
contracts/            Example contracts
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Issues and PRs welcome — please open an
issue before starting non-trivial work. Security issues: see [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE)
