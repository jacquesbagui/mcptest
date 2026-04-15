# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Releases for each package are tagged with a prefix:

- `core-vX.Y.Z` — Python package (`mymcp` on PyPI)
- `sdk-vX.Y.Z`  — Node.js package (`mymcp` on npm)

## [Unreleased]

### Added

- Python core (`packages/core`):
  - YAML contract schema (Pydantic v2, strict).
  - MCP clients for stdio, streamable HTTP, and SSE transports.
  - Assertion engine: tool existence, description, input schema, status,
    latency, response substrings, JSON Schema validation.
  - Snapshot capture and diff with breaking-change detection.
  - Reporters: console, JSON, JUnit XML, standalone HTML.
  - CLI (`mymcp run|snapshot|diff|validate`).
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
- `mymcp watch` — re-run the contract on contract/extra-path changes.
- Realistic example: notes MCP server (`packages/core/examples/notes_server.py`)
  and matching `contracts/notes.yaml`.
