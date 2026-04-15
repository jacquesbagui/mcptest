# mcptest

> Contract testing and regression detection for MCP servers.

[![PyPI version](https://img.shields.io/pypi/v/mcptest.svg)](https://pypi.org/project/mcptest/)
[![npm version](https://img.shields.io/npm/v/mcptest.svg)](https://www.npmjs.com/package/mcptest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/your-username/mcptest/actions/workflows/ci.yml/badge.svg)](https://github.com/your-username/mcptest/actions)

---

## The problem

You build an MCP server. You expose tools. You modify something. **How do you know you didn't break anything?**

Today your only options are:
- Open Claude Desktop and manually test each tool
- Click through MCP Inspector one tool at a time
- Hope your agent doesn't fail in production

There is no automated way to define what your MCP server *should* do and verify it on every commit.

**mcptest fixes that.**

---

## What it does

mcptest lets you define a **contract** — a YAML file describing the tools your server must expose, their expected behavior, and performance requirements. Then it runs those assertions against your live server and tells you exactly what passes and what fails.

```bash
mcptest run --contract contracts/my-server.yaml
```

```
✓ search_files        called with {query: "test"} → 200ms   PASS
✓ read_file           exists, schema valid                   PASS  
✗ write_file          expected status: success, got: error   FAIL
  └─ error: permission denied on /tmp/output.txt

3 tools tested · 2 passed · 1 failed
```

Think of it as **pytest for your MCP server**.

---

## Install

**CLI (Python)**

```bash
pip install mcptest
```

**SDK (Node.js / TypeScript)**

```bash
npm install mcptest
```

---

## Quick start

### 1. Write a contract

```yaml
# contracts/my-server.yaml
server:
  name: "my-mcp-server"
  transport: stdio
  command: "python server.py"

tools:
  - name: search_files
    must_exist: true
    description_contains: "search"
    input_schema:
      required:
        - query
      properties:
        query:
          type: string
    assertions:
      - call:
          args:
            query: "hello world"
        expect:
          status: success
          max_latency_ms: 1000

  - name: read_file
    must_exist: true
    assertions:
      - call:
          args:
            path: "/tmp/test.txt"
        expect:
          status: success

snapshots:
  enabled: true
  baseline: ".mcptest/baseline.json"
  fail_on_regression: true
```

### 2. Run the tests

```bash
mcptest run --contract contracts/my-server.yaml
```

### 3. Capture a baseline snapshot

```bash
mcptest snapshot --server "python server.py" --out .mcptest/baseline.json
```

### 4. Detect regressions

```bash
mcptest diff --baseline .mcptest/baseline.json --server "python server.py"
```

```
Snapshot diff:
  + get_file_info    (new tool added)
  ✗ search_files     input_schema changed: removed required field "limit"
  - delete_file      (tool removed — breaking change)
```

---

## CLI reference

| Command | Description |
|---|---|
| `mcptest run` | Run contract assertions against a server |
| `mcptest snapshot` | Capture the current state of a server's tools |
| `mcptest diff` | Compare current server state against a baseline |
| `mcptest validate` | Check MCP spec conformance without running tests |

**Options**

```bash
mcptest run --contract <path>       # Contract file to run
            --server <cmd>          # Override server command
            --transport <type>      # stdio | http | sse (default: stdio)
            --reporter <format>     # json | html | junit (default: console)
            --out <path>            # Output file for report
            --fail-fast             # Stop on first failure
```

---

## Transports

mcptest supports all three MCP transports:

```yaml
# stdio (default)
server:
  transport: stdio
  command: "python server.py"

# HTTP
server:
  transport: http
  url: "http://localhost:3000/mcp"

# SSE
server:
  transport: sse
  url: "http://localhost:3000/sse"
```

---

## SDK (Node.js / TypeScript)

Use mcptest programmatically in your existing test suite:

```typescript
import { McpTest } from 'mcptest';

const tester = new McpTest({
  transport: 'stdio',
  command: 'python server.py',
});

await tester.connect();

// Assert a tool exists
await tester.assertToolExists('search_files');

// Call a tool and assert the response
const result = await tester.call('search_files', { query: 'hello' });
tester.expect(result).toSucceed().withinMs(1000);

// Load and run a full contract
const report = await tester.runContract('./contracts/my-server.yaml');
console.log(report.summary());

await tester.disconnect();
```

Works with **Jest**, **Vitest**, or any Node.js test runner.

---

## CI/CD integration

### GitHub Actions

```yaml
# .github/workflows/mcp-server.yml
name: Test MCP server

on: [push, pull_request]

jobs:
  mcptest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install mcptest
          pip install -r requirements.txt

      - name: Run contract tests
        run: mcptest run --contract contracts/my-server.yaml --reporter junit --out results.xml

      - name: Publish test results
        uses: mikepenz/action-junit-report@v4
        if: always()
        with:
          report_paths: results.xml
```

mcptest exits with code `0` on success and `1` on failure — standard CI/CD behavior.

---

## Contract reference

### Tool assertion

```yaml
tools:
  - name: my_tool           # Tool name (required)
    must_exist: true        # Fail if tool is not exposed
    description_contains:   # Assert description includes this string
      - "keyword"
    input_schema:           # Assert input schema shape
      required:
        - param1
      properties:
        param1:
          type: string
    assertions:
      - call:
          args:             # Arguments to pass
            param1: "value"
          timeout_ms: 5000  # Override default timeout
        expect:
          status: success   # success | error
          response_contains: "expected text"
          max_latency_ms: 2000
          schema:           # Assert response shape
            type: object
            properties:
              result:
                type: array
```

### Snapshots

```yaml
snapshots:
  enabled: true
  baseline: ".mcptest/baseline.json"
  fail_on_regression: true    # Fail CI if tools are removed or schemas change
  warn_on_addition: false     # Warn (not fail) when new tools are added
```

---

## Project structure

```
mcptest/
├── packages/
│   ├── core/                    # Python — core engine
│   │   ├── mcptest/
│   │   │   ├── client/          # MCP protocol client (stdio, HTTP, SSE)
│   │   │   ├── contract/        # YAML parser + assertion engine
│   │   │   ├── snapshot/        # Capture + diff
│   │   │   ├── reporter/        # Console, JSON, HTML, JUnit
│   │   │   └── validator/       # MCP spec conformance
│   │   └── pyproject.toml
│   │
│   └── sdk-node/                # TypeScript SDK
│       ├── src/
│       │   ├── McpTest.ts
│       │   ├── Contract.ts
│       │   └── types.ts
│       └── package.json
│
├── cli/
│   └── main.py                  # CLI entry point (Typer)
│
├── contracts/
│   └── example.yaml             # Example contract
│
├── .github/
│   └── workflows/
│       └── ci.yml               # Ready-to-use GitHub Actions workflow
│
└── README.md
```

---

## Comparison

| | MCP Inspector | Claude Desktop | mcptest |
|---|---|---|---|
| Automated | ✗ | ✗ | ✓ |
| CI/CD ready | ✗ | ✗ | ✓ |
| Contract file | ✗ | ✗ | ✓ |
| Regression detection | ✗ | ✗ | ✓ |
| All transports | ✓ | ✓ | ✓ |
| No LLM required | ✓ | ✗ | ✓ |

---

## Roadmap

- [ ] Core Python engine + CLI
- [ ] Node.js SDK
- [ ] stdio transport
- [ ] HTTP + SSE transport
- [ ] Snapshot + diff
- [ ] JUnit / HTML reporter
- [ ] GitHub Actions example
- [ ] VS Code extension (test runner integration)
- [ ] Watch mode (`mcptest watch`)

---

## Contributing

Contributions are welcome. Please open an issue before submitting a large PR.

```bash
git clone https://github.com/your-username/mcptest
cd mcptest
pip install -e "packages/core[dev]"
cd packages/sdk-node && npm install
```

---

## License

MIT © [Your Name](https://github.com/your-username)

---

*Built for the MCP community. If mcptest saves you time, a ⭐ on GitHub is appreciated.*
