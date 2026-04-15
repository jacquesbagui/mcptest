import { describe, expect, it } from "vitest";
import type { McpClient } from "../src/index.js";
import { runContract, ContractSchema } from "../src/index.js";
import type { CallOutcome, ToolInfo } from "../src/index.js";

class FakeClient implements McpClient {
  private tools: ToolInfo[];
  private responses: Map<string, CallOutcome | ((args: Record<string, unknown>) => CallOutcome)>;

  constructor(
    tools: ToolInfo[],
    responses: Record<string, CallOutcome | ((args: Record<string, unknown>) => CallOutcome)> = {},
  ) {
    this.tools = tools;
    this.responses = new Map(Object.entries(responses));
  }

  async connect(): Promise<void> {}
  async close(): Promise<void> {}
  async listTools(): Promise<ToolInfo[]> {
    return this.tools;
  }
  async callTool(name: string, args: Record<string, unknown>): Promise<CallOutcome> {
    const r = this.responses.get(name);
    if (!r) return { isError: false, text: "", structured: null, latencyMs: 1 };
    return typeof r === "function" ? r(args) : r;
  }
}

function contract(yaml: object) {
  return ContractSchema.parse(yaml);
}

const baseTool: ToolInfo = {
  name: "echo",
  description: "Echo the message back",
  inputSchema: {
    type: "object",
    required: ["message"],
    properties: { message: { type: "string" } },
  },
};

describe("runContract", () => {
  it("passes when tool exists and call succeeds", async () => {
    const client = new FakeClient([baseTool], {
      echo: { isError: false, text: "hello", structured: null, latencyMs: 5 },
    });
    const c = contract({
      server: { transport: "stdio", command: "x" },
      tools: [
        {
          name: "echo",
          description_contains: "Echo",
          input_schema: {
            required: ["message"],
            properties: { message: { type: "string" } },
          },
          assertions: [
            {
              call: { args: { message: "hi" } },
              expect: { status: "success", response_contains: "hello", max_latency_ms: 1000 },
            },
          ],
        },
      ],
    });
    const report = await runContract(c, client);
    expect(report.ok).toBe(true);
    expect(report.failed).toBe(0);
    expect(report.passed).toBeGreaterThan(0);
  });

  it("fails when a must_exist tool is missing", async () => {
    const client = new FakeClient([]);
    const c = contract({
      server: { transport: "stdio", command: "x" },
      tools: [{ name: "ghost", must_exist: true }],
    });
    const report = await runContract(c, client);
    expect(report.failed).toBe(1);
    const [check] = report.checks;
    expect(check?.check).toBe("exists");
    expect(check?.status).toBe("fail");
  });

  it("skips optional absent tools", async () => {
    const client = new FakeClient([]);
    const c = contract({
      server: { transport: "stdio", command: "x" },
      tools: [{ name: "ghost", must_exist: false }],
    });
    const report = await runContract(c, client);
    expect(report.failed).toBe(0);
    expect(report.skipped).toBe(1);
  });

  it("detects input schema drift (required field missing)", async () => {
    const tool: ToolInfo = { ...baseTool, inputSchema: { required: [], properties: {} } };
    const client = new FakeClient([tool]);
    const c = contract({
      server: { transport: "stdio", command: "x" },
      tools: [
        { name: "echo", input_schema: { required: ["message"], properties: {} } },
      ],
    });
    const report = await runContract(c, client);
    const fail = report.checks.find((c) => c.status === "fail");
    expect(fail?.check).toBe("input_schema.required");
  });

  it("fails status when error expected but call succeeded", async () => {
    const client = new FakeClient([baseTool], {
      echo: { isError: false, text: "ok", structured: null, latencyMs: 1 },
    });
    const c = contract({
      server: { transport: "stdio", command: "x" },
      tools: [
        {
          name: "echo",
          assertions: [{ call: { args: {} }, expect: { status: "error" } }],
        },
      ],
    });
    const report = await runContract(c, client);
    const fail = report.checks.find((c) => c.status === "fail");
    expect(fail?.check).toBe("call#1.status");
  });

  it("enforces max_latency_ms", async () => {
    const client = new FakeClient([baseTool], {
      echo: { isError: false, text: "", structured: null, latencyMs: 500 },
    });
    const c = contract({
      server: { transport: "stdio", command: "x" },
      tools: [
        {
          name: "echo",
          assertions: [
            { call: { args: {} }, expect: { max_latency_ms: 100 } },
          ],
        },
      ],
    });
    const report = await runContract(c, client);
    const fail = report.checks.find((c) => c.check === "call#1.max_latency_ms");
    expect(fail?.status).toBe("fail");
  });

  it("validates response against a JSON Schema", async () => {
    const client = new FakeClient([baseTool], {
      echo: { isError: false, text: "", structured: { n: "not-a-number" }, latencyMs: 1 },
    });
    const c = contract({
      server: { transport: "stdio", command: "x" },
      tools: [
        {
          name: "echo",
          assertions: [
            {
              call: { args: {} },
              expect: {
                schema: { type: "object", properties: { n: { type: "number" } }, required: ["n"] },
              },
            },
          ],
        },
      ],
    });
    const report = await runContract(c, client);
    const fail = report.checks.find((c) => c.check === "call#1.schema");
    expect(fail?.status).toBe("fail");
  });
});
