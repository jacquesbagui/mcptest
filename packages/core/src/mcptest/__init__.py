"""mcptest — contract testing for MCP servers."""

from .client import McpClient, StdioClient, build_client
from .contract import Contract, ContractError, load_contract
from .contract.engine import run_contract
from .report import CheckResult, CheckStatus, Report

__version__ = "0.1.0"

__all__ = [
    "CheckResult",
    "CheckStatus",
    "Contract",
    "ContractError",
    "McpClient",
    "Report",
    "StdioClient",
    "__version__",
    "build_client",
    "load_contract",
    "run_contract",
]
