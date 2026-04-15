import { buildClient } from "./client/index.js";
import type { McpClient } from "./client/base.js";
import { runContract } from "./contract/engine.js";
import { loadContract } from "./contract/loader.js";
import type { CallOutcome } from "./types.js";
import { Report } from "./types.js";

export type StdioOptions = {
  transport: "stdio";
  command: string;
  args?: string[];
  env?: Record<string, string>;
  cwd?: string;
};

export type McpTestOptions = StdioOptions;

/**
 * High-level, test-runner-friendly API for exercising MCP servers.
 *
 * Wraps a single `McpClient` and offers fluent assertions. Designed to be
 * used from Jest/Vitest/any Node test runner.
 */
export class McpTest {
  private readonly client: McpClient;

  constructor(options: McpTestOptions) {
    this.client = buildClient({
      transport: options.transport,
      command: options.command,
      args: options.args ?? [],
      env: options.env ?? {},
      ...(options.cwd !== undefined ? { cwd: options.cwd } : {}),
    });
  }

  async connect(): Promise<void> {
    await this.client.connect();
  }

  async disconnect(): Promise<void> {
    await this.client.close();
  }

  async listTools(): Promise<string[]> {
    const tools = await this.client.listTools();
    return tools.map((t) => t.name);
  }

  async assertToolExists(name: string): Promise<void> {
    const names = await this.listTools();
    if (!names.includes(name)) {
      throw new AssertionError(
        `expected tool '${name}' to exist; got [${names.join(", ")}]`,
      );
    }
  }

  async call(
    name: string,
    args: Record<string, unknown> = {},
    options: { timeoutMs?: number } = {},
  ): Promise<CallOutcome> {
    return this.client.callTool(
      name,
      args,
      options.timeoutMs !== undefined ? { timeoutMs: options.timeoutMs } : {},
    );
  }

  expect(outcome: CallOutcome): Expectation {
    return new Expectation(outcome);
  }

  async runContract(path: string): Promise<Report> {
    const contract = loadContract(path);
    return runContract(contract, this.client);
  }
}

export class AssertionError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AssertionError";
  }
}

export class Expectation {
  constructor(private readonly outcome: CallOutcome) {}

  toSucceed(): this {
    if (this.outcome.isError) {
      throw new AssertionError(
        `expected call to succeed; got error: ${this.outcome.text.slice(0, 200)}`,
      );
    }
    return this;
  }

  toError(): this {
    if (!this.outcome.isError) {
      throw new AssertionError("expected call to error; got success");
    }
    return this;
  }

  withinMs(max: number): this {
    if (this.outcome.latencyMs > max) {
      throw new AssertionError(
        `expected latency ≤ ${max}ms; got ${Math.round(this.outcome.latencyMs)}ms`,
      );
    }
    return this;
  }

  toContain(needle: string): this {
    if (!this.outcome.text.includes(needle)) {
      throw new AssertionError(
        `expected response to contain '${needle}'; got '${this.outcome.text.slice(0, 200)}'`,
      );
    }
    return this;
  }
}
