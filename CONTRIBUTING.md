# Contributing to mymcp

Thanks for your interest in making MCP servers more testable. This project is
small and we'd like to keep it focused — please open an issue before starting
any non-trivial work so we can agree on scope.

## Repository layout

```
mymcp/
├── packages/
│   ├── core/         # Python engine + CLI (the current shipped package)
│   └── sdk-node/     # TypeScript SDK (planned)
├── contracts/        # Example contracts
└── .github/workflows # CI
```

## Local setup (Python core)

```bash
cd packages/core
uv venv .venv
uv pip install -e ".[dev]"
```

## Before opening a PR

From `packages/core`:

```bash
.venv/bin/ruff check src tests
.venv/bin/mypy src
.venv/bin/pytest -q
```

**If you edited the root `README.md`**, mirror it so the Python package ships
the same text on PyPI:

```bash
cp README.md packages/core/README.md
```

CI fails the PR if these two files differ.

All three must pass. New features must come with tests.

## Commit style

- One logical change per commit; keep messages in the imperative mood
  (`add snapshot diff`, not `added snapshot diff`).
- Reference the related issue when relevant (`fix #42: ...`).

## Code style

- Python 3.10+, strict typing. `mypy --strict` must pass.
- Pydantic v2 models are frozen and reject unknown keys (`extra="forbid"`).
- Public API lives in `mymcp/__init__.py` — keep it small and curated.
- Prefer explicit imports over re-export chains.

## Releasing

Releases are tag-triggered (`vX.Y.Z`) and run from CI. Never publish from a
developer machine.

## License

By contributing you agree that your contributions are licensed under the MIT
license, the same as the rest of the project.
