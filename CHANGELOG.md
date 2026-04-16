# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Releases for each package are tagged with a prefix:

- `core-vX.Y.Z` — Python package (`mcpact` on PyPI)
- `sdk-vX.Y.Z`  — Node.js package (`mcpact` on npm)

## [Unreleased] (v0.2)

### Added
- **Resources testing** — `resources:` section in contracts. Test by exact URI
  (existence + content_contains + content_schema) or by `uri_pattern` regex
  (min_count). Reads resources via `read_resource`.
- **Prompts testing** — `prompts:` section. Assert existence, description,
  arguments (name + required), and `get_prompt` responses (message_count,
  messages_contain, messages_schema).
- **Named assertions + variables** — assertions can have a `name:` field.
  Later steps reference earlier results via `${{ steps.<name>.result.<path> }}`.
  Type-preserving for full-value refs, string interpolation when embedded.
- **Setup/teardown hooks** — `before:` / `after:` at contract and per-tool
  level. Supports shell commands and tool calls. Variable interpolation in
  hook tool args. `--no-hooks` CLI flag for safety.
- Client protocol extended: `list_resources`, `read_resource`, `list_prompts`,
  `get_prompt` in both Python and Node clients.

### Changed
- **`CheckResult.tool` renamed to `CheckResult.subject`** — the field now
  holds the entity under test (tool name, `resource:<uri>`, `prompt:<name>`,
  or `contract` for hooks). JSON reporter output key changed accordingly.
  **Breaking** for code parsing v0.1 JSON/JUnit reports.

## [0.1.0]

### Added

- Python core (`packages/core`):
  - YAML contract schema (Pydantic v2, strict).
  - MCP clients for stdio, streamable HTTP, and SSE transports.
  - Assertion engine: tool existence, description, input schema, status,
    latency, response substrings, JSON Schema validation.
  - Snapshot capture and diff with breaking-change detection.
  - Reporters: console, JSON, JUnit XML, standalone HTML.
  - CLI (`mcpact run|snapshot|diff|validate`).
- Node.js SDK (`packages/sdk-node`):
  - Zod contract schemas in parity with the Python models.
  - stdio client built on `@modelcontextprotocol/sdk`.
  - Assertion engine mirroring the Python core.
  - Fluent `McpTest` API (`connect`, `assertToolExists`, `call`,
    `expect(...).toSucceed().toContain().withinMs()`, `runContract()`).
- CI pipeline for both packages; publish workflows (PyPI trusted publishing,
  npm with provenance) triggered by prefixed tags.
- Coverage reporting (`pytest-cov` for Python, `@vitest/coverage-v8` for Node)
  uploaded as CI artefacts.
- Security policy (`SECURITY.md`) and Dependabot configuration.
- `mcpact watch` — re-run the contract on contract/extra-path changes.
- Realistic example: notes MCP server (`packages/core/examples/notes_server.py`)
  and matching `contracts/notes.yaml`.
