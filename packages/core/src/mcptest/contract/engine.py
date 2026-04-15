"""Run a contract's assertions against a connected MCP client."""

from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaError

from ..client.base import CallOutcome, McpClient, ToolInfo
from ..report import CheckResult, CheckStatus, Report
from .models import Assertion, Contract, Expectation, InputSchemaAssertion, ToolSpec


async def run_contract(contract: Contract, client: McpClient) -> Report:
    """Execute every check the contract declares and return a Report."""
    report = Report()
    tools = await client.list_tools()
    by_name = {t.name: t for t in tools}

    for spec in contract.tools:
        tool = by_name.get(spec.name)
        if tool is None:
            if spec.must_exist:
                report.add(
                    CheckResult(spec.name, "exists", CheckStatus.FAIL, "tool not exposed by server")
                )
            else:
                report.add(CheckResult(spec.name, "exists", CheckStatus.SKIP, "optional tool absent"))
            continue
        report.add(CheckResult(spec.name, "exists", CheckStatus.PASS))

        _check_description(spec, tool, report)
        _check_input_schema(spec, tool, report)

        for idx, assertion in enumerate(spec.assertions, start=1):
            await _run_assertion(spec.name, idx, assertion, client, report)

    return report


def _check_description(spec: ToolSpec, tool: ToolInfo, report: Report) -> None:
    if spec.description_contains is None:
        return
    needles = (
        [spec.description_contains]
        if isinstance(spec.description_contains, str)
        else list(spec.description_contains)
    )
    desc = tool.description or ""
    missing = [n for n in needles if n not in desc]
    if missing:
        report.add(
            CheckResult(
                spec.name,
                "description_contains",
                CheckStatus.FAIL,
                f"description missing: {missing!r}",
            )
        )
    else:
        report.add(CheckResult(spec.name, "description_contains", CheckStatus.PASS))


def _check_input_schema(spec: ToolSpec, tool: ToolInfo, report: Report) -> None:
    if spec.input_schema is None:
        return
    assertion: InputSchemaAssertion = spec.input_schema
    schema = tool.input_schema or {}
    required = set(schema.get("required", []) or [])
    properties = schema.get("properties", {}) or {}

    missing_required = [r for r in assertion.required if r not in required]
    if missing_required:
        report.add(
            CheckResult(
                spec.name,
                "input_schema.required",
                CheckStatus.FAIL,
                f"missing required fields: {missing_required}",
            )
        )
    elif assertion.required:
        report.add(CheckResult(spec.name, "input_schema.required", CheckStatus.PASS))

    for prop_name, expected in assertion.properties.items():
        actual = properties.get(prop_name)
        if actual is None:
            report.add(
                CheckResult(
                    spec.name,
                    f"input_schema.properties.{prop_name}",
                    CheckStatus.FAIL,
                    "property not declared by tool",
                )
            )
            continue
        expected_type = expected.get("type")
        if expected_type and actual.get("type") != expected_type:
            report.add(
                CheckResult(
                    spec.name,
                    f"input_schema.properties.{prop_name}",
                    CheckStatus.FAIL,
                    f"expected type {expected_type!r}, got {actual.get('type')!r}",
                )
            )
        else:
            report.add(
                CheckResult(
                    spec.name, f"input_schema.properties.{prop_name}", CheckStatus.PASS
                )
            )


async def _run_assertion(
    tool_name: str,
    idx: int,
    assertion: Assertion,
    client: McpClient,
    report: Report,
) -> None:
    label = f"call#{idx}"
    try:
        outcome = await client.call_tool(
            tool_name, dict(assertion.call.args), timeout_ms=assertion.call.timeout_ms
        )
    except Exception as e:
        report.add(
            CheckResult(
                tool_name,
                label,
                CheckStatus.FAIL,
                f"transport error: {type(e).__name__}: {e}",
            )
        )
        return

    _check_status(tool_name, label, assertion.expect, outcome, report)
    _check_latency(tool_name, label, assertion.expect, outcome, report)
    _check_response_contains(tool_name, label, assertion.expect, outcome, report)
    _check_response_schema(tool_name, label, assertion.expect, outcome, report)


def _check_status(
    tool: str, label: str, expect: Expectation, outcome: CallOutcome, report: Report
) -> None:
    expected_error = expect.status == "error"
    actual_error = outcome.is_error
    if expected_error == actual_error:
        report.add(
            CheckResult(
                tool,
                f"{label}.status",
                CheckStatus.PASS,
                latency_ms=outcome.latency_ms,
            )
        )
    else:
        msg = f"expected status={expect.status!r}, got {'error' if actual_error else 'success'}"
        if outcome.text:
            msg += f" — {outcome.text[:200]}"
        report.add(
            CheckResult(
                tool,
                f"{label}.status",
                CheckStatus.FAIL,
                msg,
                latency_ms=outcome.latency_ms,
            )
        )


def _check_latency(
    tool: str, label: str, expect: Expectation, outcome: CallOutcome, report: Report
) -> None:
    if expect.max_latency_ms is None:
        return
    if outcome.latency_ms <= expect.max_latency_ms:
        report.add(
            CheckResult(
                tool,
                f"{label}.max_latency_ms",
                CheckStatus.PASS,
                latency_ms=outcome.latency_ms,
            )
        )
    else:
        report.add(
            CheckResult(
                tool,
                f"{label}.max_latency_ms",
                CheckStatus.FAIL,
                f"{outcome.latency_ms:.0f}ms > {expect.max_latency_ms}ms",
                latency_ms=outcome.latency_ms,
            )
        )


def _check_response_contains(
    tool: str, label: str, expect: Expectation, outcome: CallOutcome, report: Report
) -> None:
    if expect.response_contains is None:
        return
    needles = (
        [expect.response_contains]
        if isinstance(expect.response_contains, str)
        else list(expect.response_contains)
    )
    missing = [n for n in needles if n not in outcome.text]
    if missing:
        report.add(
            CheckResult(
                tool,
                f"{label}.response_contains",
                CheckStatus.FAIL,
                f"missing substrings: {missing!r}",
            )
        )
    else:
        report.add(CheckResult(tool, f"{label}.response_contains", CheckStatus.PASS))


def _check_response_schema(
    tool: str, label: str, expect: Expectation, outcome: CallOutcome, report: Report
) -> None:
    if expect.schema_ is None:
        return
    payload: Any = outcome.structured if outcome.structured is not None else outcome.text
    try:
        Draft202012Validator(expect.schema_).validate(payload)
    except JsonSchemaError as e:
        report.add(
            CheckResult(
                tool,
                f"{label}.schema",
                CheckStatus.FAIL,
                f"schema mismatch at {'/'.join(map(str, e.absolute_path))}: {e.message}",
            )
        )
        return
    report.add(CheckResult(tool, f"{label}.schema", CheckStatus.PASS))
