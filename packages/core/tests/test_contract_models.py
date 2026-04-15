import pytest

from mcpcheck.contract import ContractError, load_contract
from mcpcheck.contract.models import Contract, ServerConfig


def test_server_config_requires_command_for_stdio() -> None:
    with pytest.raises(ValueError, match="command is required"):
        ServerConfig(transport="stdio")


def test_server_config_requires_url_for_http() -> None:
    with pytest.raises(ValueError, match="url is required"):
        ServerConfig(transport="http")


def test_load_contract_missing_file(tmp_path) -> None:
    with pytest.raises(ContractError, match="not found"):
        load_contract(tmp_path / "nope.yaml")


def test_load_contract_happy_path(tmp_path) -> None:
    p = tmp_path / "c.yaml"
    p.write_text(
        """
server:
  transport: stdio
  command: python -c 'pass'
tools:
  - name: echo
    assertions:
      - call:
          args:
            message: hi
        expect:
          status: success
""".strip()
    )
    contract = load_contract(p)
    assert isinstance(contract, Contract)
    assert contract.tools[0].name == "echo"
    assert contract.tools[0].assertions[0].call.args == {"message": "hi"}


def test_load_contract_rejects_unknown_keys(tmp_path) -> None:
    p = tmp_path / "c.yaml"
    p.write_text(
        """
server:
  transport: stdio
  command: x
  unknown_field: 1
""".strip()
    )
    with pytest.raises(ContractError):
        load_contract(p)
