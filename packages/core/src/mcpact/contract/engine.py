"""Run a contract's assertions against a connected MCP client."""

from __future__ import annotations

import re
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaError

from ..client.base import CallOutcome, McpClient, ResourceInfo, ToolInfo
from ..report import CheckResult, CheckStatus, Report
from .hooks import run_hooks
from .models import (
    Assertion,
    Contract,
    Expectation,
    InputSchemaAssertion,
    PromptSpec,
    ResourceSpec,
    ToolSpec,
)
from .variables import VariableError, resolve_value


async def run_contract(
    contract: Contract,
    client: McpClient,
    *,
    fail_fast: bool = False,
    no_hooks: bool = False,
) -> Report:
    """Execute every check the contract declares and return a Report.

    When `fail_fast` is True, stop as soon as any check fails.
    When `no_hooks` is True, before/after hooks are skipped.
    """
    report = Report()

    if not no_hooks and contract.before:
        try:
            await run_hooks(contract.before, client)
        except Exception as e:
            report.add(CheckResult("contract", "before", CheckStatus.FAIL, f"hook error: {e}"))
            return report

    try:
        tools = await client.list_tools()
        by_name = {t.name: t for t in tools}

        for spec in contract.tools:
            tool = by_name.get(spec.name)
            if tool is None:
                if spec.must_exist:
                    report.add(
                        CheckResult(spec.name, "exists", CheckStatus.FAIL, "tool not exposed by server")
                    )
                    if fail_fast:
                        return report
                else:
                    report.add(CheckResult(spec.name, "exists", CheckStatus.SKIP, "optional tool absent"))
                continue
            report.add(CheckResult(spec.name, "exists", CheckStatus.PASS))

            _check_description(spec, tool, report)
            _check_input_schema(spec, tool, report)
            if fail_fast and report.failed:
                return report

            if not no_hooks and spec.before:
                try:
                    await run_hooks(spec.before, client)
                except Exception as e:
                    report.add(CheckResult(spec.name, "before", CheckStatus.FAIL, f"hook error: {e}"))
                    continue

            step_context: dict[str, Any] = {}
            try:
                for idx, assertion in enumerate(spec.assertions, start=1):
                    await _run_assertion(spec.name, idx, assertion, client, report, step_context)
                    if fail_fast and report.failed:
                        return report
            finally:
                if not no_hooks and spec.after:
                    try:
                        await run_hooks(spec.after, client, step_context)
                    except Exception as e:
                        report.add(CheckResult(spec.name, "after", CheckStatus.FAIL, f"hook error: {e}"))

        if contract.resources:
            await _run_resources(contract.resources, client, report, fail_fast)
            if fail_fast and report.failed:
                return report

        if contract.prompts:
            await _run_prompts(contract.prompts, client, report, fail_fast)
    finally:
        if not no_hooks and contract.after:
            try:
                await run_hooks(contract.after, client)
            except Exception as e:
                report.add(CheckResult("contract", "after", CheckStatus.FAIL, f"hook error: {e}"))

    return report


# ---------- resources ----------

async def _run_resources(
    specs: list[ResourceSpec],
    client: McpClient,
    report: Report,
    fail_fast: bool,
) -> None:
    resources = await client.list_resources()
    for spec in specs:
        if spec.uri:
            await _check_resource_by_uri(spec, resources, client, report)
        else:
            _check_resource_by_pattern(spec, resources, report)
        if fail_fast and report.failed:
            return


async def _check_resource_by_uri(
    spec: ResourceSpec,
    resources: list[ResourceInfo],
    client: McpClient,
    report: Report,
) -> None:
    assert spec.uri is not None
    subject = f"resource:{spec.uri}"
    found = any(r.uri == spec.uri for r in resources)
    if not found:
        if spec.must_exist:
            report.add(CheckResult(subject, "exists", CheckStatus.FAIL, "resource not listed"))
        else:
            report.add(CheckResult(subject, "exists", CheckStatus.SKIP, "optional resource absent"))
        return
    report.add(CheckResult(subject, "exists", CheckStatus.PASS))

    if spec.content_contains is not None or spec.content_schema is not None:
        try:
            content = await client.read_resource(spec.uri)
        except Exception as e:
            report.add(
                CheckResult(subject, "read", CheckStatus.FAIL, f"read failed: {e}")
            )
            return
        _check_resource_content(subject, spec, content.text, report)


def _check_resource_by_pattern(
    spec: ResourceSpec,
    resources: list[ResourceInfo],
    report: Report,
) -> None:
    assert spec.uri_pattern is not None
    subject = f"resource:~{spec.uri_pattern}"
    try:
        pattern = re.compile(spec.uri_pattern)
    except re.error as e:
        report.add(CheckResult(subject, "pattern", CheckStatus.FAIL, f"invalid regex: {e}"))
        return
    matched = [r for r in resources if pattern.search(r.uri)]
    if spec.min_count is not None and len(matched) < spec.min_count:
        report.add(
            CheckResult(
                subject,
                "min_count",
                CheckStatus.FAIL,
                f"matched {len(matched)}, expected >= {spec.min_count}",
            )
        )
    elif spec.min_count is not None:
        report.add(CheckResult(subject, "min_count", CheckStatus.PASS))
    if not matched and spec.must_exist:
        report.add(CheckResult(subject, "exists", CheckStatus.FAIL, "no resources match pattern"))


def _check_resource_content(
    subject: str, spec: ResourceSpec, text: str, report: Report
) -> None:
    if spec.content_contains is not None:
        needles = (
            [spec.content_contains]
            if isinstance(spec.content_contains, str)
            else list(spec.content_contains)
        )
        missing = [n for n in needles if n not in text]
        if missing:
            report.add(
                CheckResult(subject, "content_contains", CheckStatus.FAIL, f"missing: {missing!r}")
            )
        else:
            report.add(CheckResult(subject, "content_contains", CheckStatus.PASS))

    if spec.content_schema is not None:
        import json

        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            report.add(
                CheckResult(subject, "content_schema", CheckStatus.FAIL, "content is not valid JSON")
            )
            return
        try:
            Draft202012Validator(spec.content_schema).validate(payload)
        except JsonSchemaError as e:
            report.add(
                CheckResult(
                    subject,
                    "content_schema",
                    CheckStatus.FAIL,
                    f"schema mismatch: {e.message}",
                )
            )
            return
        report.add(CheckResult(subject, "content_schema", CheckStatus.PASS))


# ---------- prompts ----------

async def _run_prompts(
    specs: list[PromptSpec],
    client: McpClient,
    report: Report,
    fail_fast: bool,
) -> None:
    prompts = await client.list_prompts()
    by_name = {p.name: p for p in prompts}
    for spec in specs:
        prompt = by_name.get(spec.name)
        subject = f"prompt:{spec.name}"
        if prompt is None:
            if spec.must_exist:
                report.add(CheckResult(subject, "exists", CheckStatus.FAIL, "prompt not listed"))
            else:
                report.add(CheckResult(subject, "exists", CheckStatus.SKIP))
            continue
        report.add(CheckResult(subject, "exists", CheckStatus.PASS))

        if spec.description_contains is not None:
            needles = (
                [spec.description_contains]
                if isinstance(spec.description_contains, str)
                else list(spec.description_contains)
            )
            desc = prompt.description or ""
            missing = [n for n in needles if n not in desc]
            if missing:
                report.add(
                    CheckResult(
                        subject, "description_contains", CheckStatus.FAIL,
                        f"description missing: {missing!r}",
                    )
                )
            else:
                report.add(CheckResult(subject, "description_contains", CheckStatus.PASS))

        if spec.arguments:
            prompt_arg_names = {a.name for a in prompt.arguments}
            for arg_spec in spec.arguments:
                check = f"arg:{arg_spec.name}"
                if arg_spec.name not in prompt_arg_names:
                    report.add(CheckResult(subject, check, CheckStatus.FAIL, "argument not declared"))
                else:
                    report.add(CheckResult(subject, check, CheckStatus.PASS))
                    if arg_spec.required:
                        actual = next(a for a in prompt.arguments if a.name == arg_spec.name)
                        if not actual.required:
                            report.add(
                                CheckResult(subject, f"{check}.required", CheckStatus.FAIL, "expected required")
                            )
                        else:
                            report.add(CheckResult(subject, f"{check}.required", CheckStatus.PASS))

        for pa_idx, pa in enumerate(spec.assertions, start=1):
            await _run_prompt_assertion(subject, pa_idx, spec.name, pa, client, report)

        if fail_fast and report.failed:
            return


async def _run_prompt_assertion(
    subject: str,
    idx: int,
    prompt_name: str,
    pa: Any,
    client: McpClient,
    report: Report,
) -> None:
    from .models import PromptAssertion

    assert isinstance(pa, PromptAssertion)
    label = f"get#{idx}"
    try:
        result = await client.get_prompt(prompt_name, dict(pa.get_prompt.args))
    except Exception as e:
        report.add(
            CheckResult(subject, label, CheckStatus.FAIL, f"get_prompt error: {e}")
        )
        return

    expect = pa.expect
    if expect.message_count is not None:
        actual = len(result.messages)
        if actual != expect.message_count:
            report.add(
                CheckResult(
                    subject, f"{label}.message_count", CheckStatus.FAIL,
                    f"expected {expect.message_count}, got {actual}",
                )
            )
        else:
            report.add(CheckResult(subject, f"{label}.message_count", CheckStatus.PASS))

    if expect.messages_contain is not None:
        needles = (
            [expect.messages_contain]
            if isinstance(expect.messages_contain, str)
            else list(expect.messages_contain)
        )
        all_text = " ".join(m.text for m in result.messages)
        missing = [n for n in needles if n not in all_text]
        if missing:
            report.add(
                CheckResult(
                    subject, f"{label}.messages_contain", CheckStatus.FAIL,
                    f"missing: {missing!r}",
                )
            )
        else:
            report.add(CheckResult(subject, f"{label}.messages_contain", CheckStatus.PASS))

    if expect.messages_schema is not None:
        payload = [{"role": m.role, "text": m.text} for m in result.messages]
        try:
            Draft202012Validator(expect.messages_schema).validate(payload)
        except JsonSchemaError as e:
            report.add(
                CheckResult(
                    subject, f"{label}.messages_schema", CheckStatus.FAIL,
                    f"schema mismatch: {e.message}",
                )
            )
        else:
            report.add(CheckResult(subject, f"{label}.messages_schema", CheckStatus.PASS))


# ---------- tools ----------

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
    step_context: dict[str, Any] | None = None,
) -> None:
    label = assertion.name or f"call#{idx}"
    ctx = step_context if step_context is not None else {}

    try:
        resolved_args = resolve_value(dict(assertion.call.args), ctx)
    except VariableError as e:
        report.add(
            CheckResult(tool_name, label, CheckStatus.FAIL, f"variable error: {e}")
        )
        return

    try:
        outcome = await client.call_tool(
            tool_name, resolved_args, timeout_ms=assertion.call.timeout_ms
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

    if assertion.name:
        ctx[assertion.name] = {
            "text": outcome.text,
            "structured": outcome.structured,
            "is_error": outcome.is_error,
        }

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
