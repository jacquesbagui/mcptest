import Ajv from "ajv";
import type { McpClient } from "../client/base.js";
import type { CallOutcome, ToolInfo } from "../types.js";
import { Report } from "../types.js";
import type { Assertion, Contract, Expectation, ToolSpec } from "./schema.js";
import { VariableError, resolveValue } from "./variables.js";

const ajv = new Ajv({ strict: false, allErrors: true });

export async function runContract(contract: Contract, client: McpClient): Promise<Report> {
  const report = new Report();
  const tools = await client.listTools();
  const byName = new Map(tools.map((t) => [t.name, t]));

  for (const spec of contract.tools) {
    const tool = byName.get(spec.name);
    if (!tool) {
      if (spec.must_exist) {
        report.add({
          tool: spec.name,
          check: "exists",
          status: "fail",
          message: "tool not exposed by server",
        });
      } else {
        report.add({
          tool: spec.name,
          check: "exists",
          status: "skip",
          message: "optional tool absent",
        });
      }
      continue;
    }
    report.add({ tool: spec.name, check: "exists", status: "pass" });

    checkDescription(spec, tool, report);
    checkInputSchema(spec, tool, report);

    const stepContext: Record<string, unknown> = {};
    let i = 0;
    for (const assertion of spec.assertions) {
      i += 1;
      await runAssertion(spec.name, i, assertion, client, report, stepContext);
    }
  }

  return report;
}

function asList(v: string | string[] | undefined): string[] {
  if (v === undefined) return [];
  return typeof v === "string" ? [v] : v;
}

function checkDescription(spec: ToolSpec, tool: ToolInfo, report: Report): void {
  const needles = asList(spec.description_contains);
  if (needles.length === 0) return;
  const desc = tool.description ?? "";
  const missing = needles.filter((n) => !desc.includes(n));
  if (missing.length > 0) {
    report.add({
      tool: spec.name,
      check: "description_contains",
      status: "fail",
      message: `description missing: ${JSON.stringify(missing)}`,
    });
  } else {
    report.add({ tool: spec.name, check: "description_contains", status: "pass" });
  }
}

function checkInputSchema(spec: ToolSpec, tool: ToolInfo, report: Report): void {
  const want = spec.input_schema;
  if (!want) return;
  const schema = tool.inputSchema ?? {};
  const required = new Set(Array.isArray(schema["required"]) ? (schema["required"] as string[]) : []);
  const properties = (schema["properties"] as Record<string, { type?: string }> | undefined) ?? {};

  const missingRequired = want.required.filter((r) => !required.has(r));
  if (missingRequired.length > 0) {
    report.add({
      tool: spec.name,
      check: "input_schema.required",
      status: "fail",
      message: `missing required fields: ${JSON.stringify(missingRequired)}`,
    });
  } else if (want.required.length > 0) {
    report.add({ tool: spec.name, check: "input_schema.required", status: "pass" });
  }

  for (const [propName, expected] of Object.entries(want.properties)) {
    const actual = properties[propName];
    const check = `input_schema.properties.${propName}`;
    if (!actual) {
      report.add({
        tool: spec.name,
        check,
        status: "fail",
        message: "property not declared by tool",
      });
      continue;
    }
    const expectedType = (expected as { type?: string }).type;
    if (expectedType && actual.type !== expectedType) {
      report.add({
        tool: spec.name,
        check,
        status: "fail",
        message: `expected type '${expectedType}', got '${actual.type ?? "undefined"}'`,
      });
    } else {
      report.add({ tool: spec.name, check, status: "pass" });
    }
  }
}

async function runAssertion(
  toolName: string,
  idx: number,
  assertion: Assertion,
  client: McpClient,
  report: Report,
  stepContext: Record<string, unknown> = {},
): Promise<void> {
  const label = assertion.name ?? `call#${idx}`;

  let resolvedArgs: Record<string, unknown>;
  try {
    resolvedArgs = resolveValue(assertion.call.args, stepContext) as Record<string, unknown>;
  } catch (e) {
    if (e instanceof VariableError) {
      report.add({ tool: toolName, check: label, status: "fail", message: `variable error: ${e.message}` });
      return;
    }
    throw e;
  }

  let outcome: CallOutcome;
  try {
    outcome = await client.callTool(
      toolName,
      resolvedArgs,
      assertion.call.timeout_ms !== undefined ? { timeoutMs: assertion.call.timeout_ms } : {},
    );
  } catch (e) {
    report.add({
      tool: toolName,
      check: label,
      status: "fail",
      message: `transport error: ${e instanceof Error ? e.message : String(e)}`,
    });
    return;
  }

  if (assertion.name !== undefined) {
    stepContext[assertion.name] = {
      text: outcome.text,
      structured: outcome.structured,
      is_error: outcome.isError,
    };
  }

  checkStatus(toolName, label, assertion.expect, outcome, report);
  checkLatency(toolName, label, assertion.expect, outcome, report);
  checkResponseContains(toolName, label, assertion.expect, outcome, report);
  checkResponseSchema(toolName, label, assertion.expect, outcome, report);
}

function checkStatus(
  tool: string,
  label: string,
  expect: Expectation,
  outcome: CallOutcome,
  report: Report,
): void {
  const expectedError = expect.status === "error";
  const check = `${label}.status`;
  if (expectedError === outcome.isError) {
    report.add({ tool, check, status: "pass", latencyMs: outcome.latencyMs });
    return;
  }
  let message = `expected status='${expect.status}', got '${outcome.isError ? "error" : "success"}'`;
  if (outcome.text) message += ` — ${outcome.text.slice(0, 200)}`;
  report.add({ tool, check, status: "fail", message, latencyMs: outcome.latencyMs });
}

function checkLatency(
  tool: string,
  label: string,
  expect: Expectation,
  outcome: CallOutcome,
  report: Report,
): void {
  if (expect.max_latency_ms === undefined) return;
  const check = `${label}.max_latency_ms`;
  if (outcome.latencyMs <= expect.max_latency_ms) {
    report.add({ tool, check, status: "pass", latencyMs: outcome.latencyMs });
  } else {
    report.add({
      tool,
      check,
      status: "fail",
      message: `${Math.round(outcome.latencyMs)}ms > ${expect.max_latency_ms}ms`,
      latencyMs: outcome.latencyMs,
    });
  }
}

function checkResponseContains(
  tool: string,
  label: string,
  expect: Expectation,
  outcome: CallOutcome,
  report: Report,
): void {
  const needles = asList(expect.response_contains);
  if (needles.length === 0) return;
  const check = `${label}.response_contains`;
  const missing = needles.filter((n) => !outcome.text.includes(n));
  if (missing.length > 0) {
    report.add({
      tool,
      check,
      status: "fail",
      message: `missing substrings: ${JSON.stringify(missing)}`,
    });
  } else {
    report.add({ tool, check, status: "pass" });
  }
}

function checkResponseSchema(
  tool: string,
  label: string,
  expect: Expectation,
  outcome: CallOutcome,
  report: Report,
): void {
  if (!expect.schema) return;
  const check = `${label}.schema`;
  const payload: unknown = outcome.structured ?? outcome.text;
  const validate = ajv.compile(expect.schema);
  if (validate(payload)) {
    report.add({ tool, check, status: "pass" });
    return;
  }
  const first = (validate.errors ?? [])[0];
  const at = first?.instancePath || "/";
  const msg = first?.message ?? "schema mismatch";
  report.add({ tool, check, status: "fail", message: `schema mismatch at ${at}: ${msg}` });
}
