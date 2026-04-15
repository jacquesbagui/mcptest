"""Load and validate contract YAML files."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from .models import Contract


class ContractError(Exception):
    """Raised when a contract file is invalid or cannot be loaded."""


def load_contract(path: str | Path) -> Contract:
    p = Path(path)
    if not p.is_file():
        raise ContractError(f"Contract file not found: {p}")
    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise ContractError(f"Invalid YAML in {p}: {e}") from e
    if not isinstance(raw, dict):
        raise ContractError(f"Contract root must be a mapping, got {type(raw).__name__}")
    try:
        return Contract.model_validate(raw)
    except ValidationError as e:
        raise ContractError(f"Contract schema validation failed for {p}:\n{e}") from e
