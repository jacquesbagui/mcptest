import Ajv from "ajv";
import type { McpClient } from "../client/base.js";
import type { CallOutcome, ResourceInfo, ToolInfo } from "../types.js";
import { Report } from "../types.js";
import type {
  Assertion,
  Contract,
  Expectation,
  PromptAssertion,
  PromptSpec,
  ResourceSpec,
  ToolSpec,
} from "./schema.js";
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
          subject: spec.name,
          check: "exists",
          status: "fail",
          message: "tool not exposed by server",
        });
      } else {
        report.add({
          subject: spec.name,
          check: "exists",
          status: "skip",
          message: "optional tool absent",
        });
      }
      continue;
    }
    report.add({ subject: spec.name, check: "exists", status: "pass" });

    checkDescription(spec, tool, report);
    checkInputSchema(spec, tool, report);

    const stepContext: Record<string, unknown> = {};
    let i = 0;
    for (const assertion of spec.assertions) {
      i += 1;
      await runAssertion(spec.name, i, assertion, client, report, stepContext);
    }
  }

  if (contract.resources.length > 0) {
    await runResources(contract.resources, client, report);
  }
  if (contract.prompts.length > 0) {
    await runPrompts(contract.prompts, client, report);
  }

  return report;
}

// ---------- resources ----------

async function runResources(
  specs: ResourceSpec[],
  client: McpClient,
  report: Report,
): Promise<void> {
  const resources = await client.listResources();
  for (const spec of specs) {
    if (spec.uri !== undefined) {
      await checkResourceByUri(spec, resources, client, report);
    } else if (spec.uri_pattern !== undefined) {
      checkResourceByPattern(spec, resources, report);
    }
  }
}

async function checkResourceByUri(
  spec: ResourceSpec,
  resources: ResourceInfo[],
  client: McpClient,
  report: Report,
): Promise<void> {
  const uri = spec.uri!;
  const subject = `resource:${uri}`;
  const found = resources.some((r) => r.uri === uri);
  if (!found) {
    if (spec.must_exist) {
      report.add({ subject: subject, check: "exists", status: "fail", message: "resource not listed" });
    } else {
      report.add({ subject: subject, check: "exists", status: "skip", message: "optional resource absent" });
    }
    return;
  }
  report.add({ subject: subject, check: "exists", status: "pass" });

  if (spec.content_contains !== undefined || spec.content_schema !== undefined) {
    let text: string;
    try {
      const content = await client.readResource(uri);
      text = content.text;
    } catch (e) {
      report.add({ subject: subject, check: "read", status: "fail", message: `read failed: ${e instanceof Error ? e.message : String(e)}` });
      return;
    }
    checkResourceContent(subject, spec, text, report);
  }
}

function checkResourceByPattern(
  spec: ResourceSpec,
  resources: ResourceInfo[],
  report: Report,
): void {
  const pat = spec.uri_pattern!;
  const subject = `resource:~${pat}`;
  let re: RegExp;
  try {
    re = new RegExp(pat);
  } catch (e) {
    report.add({ subject: subject, check: "pattern", status: "fail", message: `invalid regex: ${e instanceof Error ? e.message : String(e)}` });
    return;
  }
  const matched = resources.filter((r) => re.test(r.uri));
  if (spec.min_count !== undefined) {
    if (matched.length < spec.min_count) {
      report.add({ subject: subject, check: "min_count", status: "fail", message: `matched ${matched.length}, expected >= ${spec.min_count}` });
    } else {
      report.add({ subject: subject, check: "min_count", status: "pass" });
    }
  }
  if (matched.length === 0 && spec.must_exist) {
    report.add({ subject: subject, check: "exists", status: "fail", message: "no resources match pattern" });
  }
}

function checkResourceContent(subject: string, spec: ResourceSpec, text: string, report: Report): void {
  if (spec.content_contains !== undefined) {
    const needles = typeof spec.content_contains === "string" ? [spec.content_contains] : spec.content_contains;
    const missing = needles.filter((n) => !text.includes(n));
    if (missing.length > 0) {
      report.add({ subject: subject, check: "content_contains", status: "fail", message: `missing: ${JSON.stringify(missing)}` });
    } else {
      report.add({ subject: subject, check: "content_contains", status: "pass" });
    }
  }
  if (spec.content_schema !== undefined) {
    let payload: unknown;
    try {
      payload = JSON.parse(text);
    } catch {
      report.add({ subject: subject, check: "content_schema", status: "fail", message: "content is not valid JSON" });
      return;
    }
    const validate = ajv.compile(spec.content_schema);
    if (validate(payload)) {
      report.add({ subject: subject, check: "content_schema", status: "pass" });
    } else {
      const first = (validate.errors ?? [])[0];
      report.add({ subject: subject, check: "content_schema", status: "fail", message: `schema mismatch: ${first?.message ?? "unknown"}` });
    }
  }
}

// ---------- prompts ----------

async function runPrompts(
  specs: PromptSpec[],
  client: McpClient,
  report: Report,
): Promise<void> {
  const prompts = await client.listPrompts();
  const byName = new Map(prompts.map((p) => [p.name, p]));

  for (const spec of specs) {
    const subject = `prompt:${spec.name}`;
    const prompt = byName.get(spec.name);
    if (!prompt) {
      if (spec.must_exist) {
        report.add({ subject: subject, check: "exists", status: "fail", message: "prompt not listed" });
      } else {
        report.add({ subject: subject, check: "exists", status: "skip" });
      }
      continue;
    }
    report.add({ subject: subject, check: "exists", status: "pass" });

    if (spec.description_contains !== undefined) {
      const needles = typeof spec.description_contains === "string" ? [spec.description_contains] : spec.description_contains;
      const desc = prompt.description ?? "";
      const missing = needles.filter((n) => !desc.includes(n));
      if (missing.length > 0) {
        report.add({ subject: subject, check: "description_contains", status: "fail", message: `description missing: ${JSON.stringify(missing)}` });
      } else {
        report.add({ subject: subject, check: "description_contains", status: "pass" });
      }
    }

    if (spec.arguments.length > 0) {
      const names = new Set(prompt.arguments.map((a) => a.name));
      for (const as of spec.arguments) {
        const check = `arg:${as.name}`;
        if (!names.has(as.name)) {
          report.add({ subject: subject, check, status: "fail", message: "argument not declared" });
        } else {
          report.add({ subject: subject, check, status: "pass" });
          if (as.required) {
            const actual = prompt.arguments.find((a) => a.name === as.name);
            if (!actual?.required) {
              report.add({ subject: subject, check: `${check}.required`, status: "fail", message: "expected required" });
            } else {
              report.add({ subject: subject, check: `${check}.required`, status: "pass" });
            }
          }
        }
      }
    }

    let pi = 0;
    for (const pa of spec.assertions) {
      pi += 1;
      await runPromptAssertion(subject, pi, spec.name, pa, client, report);
    }
  }
}

async function runPromptAssertion(
  subject: string,
  idx: number,
  promptName: string,
  pa: PromptAssertion,
  client: McpClient,
  report: Report,
): Promise<void> {
  const label = `get#${idx}`;
  let result: Awaited<ReturnType<McpClient["getPrompt"]>>;
  try {
    result = await client.getPrompt(promptName, pa.get_prompt.args);
  } catch (e) {
    report.add({ subject: subject, check: label, status: "fail", message: `get_prompt error: ${e instanceof Error ? e.message : String(e)}` });
    return;
  }

  const expect = pa.expect;
  if (expect.message_count !== undefined) {
    if (result.messages.length !== expect.message_count) {
      report.add({ subject: subject, check: `${label}.message_count`, status: "fail", message: `expected ${expect.message_count}, got ${result.messages.length}` });
    } else {
      report.add({ subject: subject, check: `${label}.message_count`, status: "pass" });
    }
  }

  if (expect.messages_contain !== undefined) {
    const needles = typeof expect.messages_contain === "string" ? [expect.messages_contain] : expect.messages_contain;
    const allText = result.messages.map((m) => m.text).join(" ");
    const missing = needles.filter((n) => !allText.includes(n));
    if (missing.length > 0) {
      report.add({ subject: subject, check: `${label}.messages_contain`, status: "fail", message: `missing: ${JSON.stringify(missing)}` });
    } else {
      report.add({ subject: subject, check: `${label}.messages_contain`, status: "pass" });
    }
  }

  if (expect.messages_schema !== undefined) {
    const payload = result.messages.map((m) => ({ role: m.role, text: m.text }));
    const validate = ajv.compile(expect.messages_schema);
    if (validate(payload)) {
      report.add({ subject: subject, check: `${label}.messages_schema`, status: "pass" });
    } else {
      const first = (validate.errors ?? [])[0];
      report.add({ subject: subject, check: `${label}.messages_schema`, status: "fail", message: `schema mismatch: ${first?.message ?? "unknown"}` });
    }
  }
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
      subject: spec.name,
      check: "description_contains",
      status: "fail",
      message: `description missing: ${JSON.stringify(missing)}`,
    });
  } else {
    report.add({ subject: spec.name, check: "description_contains", status: "pass" });
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
      subject: spec.name,
      check: "input_schema.required",
      status: "fail",
      message: `missing required fields: ${JSON.stringify(missingRequired)}`,
    });
  } else if (want.required.length > 0) {
    report.add({ subject: spec.name, check: "input_schema.required", status: "pass" });
  }

  for (const [propName, expected] of Object.entries(want.properties)) {
    const actual = properties[propName];
    const check = `input_schema.properties.${propName}`;
    if (!actual) {
      report.add({
        subject: spec.name,
        check,
        status: "fail",
        message: "property not declared by tool",
      });
      continue;
    }
    const expectedType = (expected as { type?: string }).type;
    if (expectedType && actual.type !== expectedType) {
      report.add({
        subject: spec.name,
        check,
        status: "fail",
        message: `expected type '${expectedType}', got '${actual.type ?? "undefined"}'`,
      });
    } else {
      report.add({ subject: spec.name, check, status: "pass" });
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
      report.add({ subject: toolName, check: label, status: "fail", message: `variable error: ${e.message}` });
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
      subject: toolName,
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
  subject: string,
  label: string,
  expect: Expectation,
  outcome: CallOutcome,
  report: Report,
): void {
  const expectedError = expect.status === "error";
  const check = `${label}.status`;
  if (expectedError === outcome.isError) {
    report.add({ subject, check, status: "pass", latencyMs: outcome.latencyMs });
    return;
  }
  let message = `expected status='${expect.status}', got '${outcome.isError ? "error" : "success"}'`;
  if (outcome.text) message += ` — ${outcome.text.slice(0, 200)}`;
  report.add({ subject, check, status: "fail", message, latencyMs: outcome.latencyMs });
}

function checkLatency(
  subject: string,
  label: string,
  expect: Expectation,
  outcome: CallOutcome,
  report: Report,
): void {
  if (expect.max_latency_ms === undefined) return;
  const check = `${label}.max_latency_ms`;
  if (outcome.latencyMs <= expect.max_latency_ms) {
    report.add({ subject, check, status: "pass", latencyMs: outcome.latencyMs });
  } else {
    report.add({
      subject,
      check,
      status: "fail",
      message: `${Math.round(outcome.latencyMs)}ms > ${expect.max_latency_ms}ms`,
      latencyMs: outcome.latencyMs,
    });
  }
}

function checkResponseContains(
  subject: string,
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
      subject,
      check,
      status: "fail",
      message: `missing substrings: ${JSON.stringify(missing)}`,
    });
  } else {
    report.add({ subject, check, status: "pass" });
  }
}

function checkResponseSchema(
  subject: string,
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
    report.add({ subject, check, status: "pass" });
    return;
  }
  const first = (validate.errors ?? [])[0];
  const at = first?.instancePath || "/";
  const msg = first?.message ?? "schema mismatch";
  report.add({ subject, check, status: "fail", message: `schema mismatch at ${at}: ${msg}` });
}
