import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import type { Transport } from "@modelcontextprotocol/sdk/shared/transport.js";
import type { CallOutcome, ToolInfo } from "../types.js";
import type { CallToolOptions, McpClient } from "./base.js";

/**
 * Shared MCP session logic. Concrete clients only construct the transport.
 */
export abstract class SessionClient implements McpClient {
  private client: Client | null = null;
  private transport: Transport | null = null;

  protected abstract createTransport(): Transport;

  async connect(): Promise<void> {
    if (this.client) return;
    const transport = this.createTransport();
    const client = new Client(
      { name: "mcpact", version: "0.1.0" },
      { capabilities: {} },
    );
    await client.connect(transport);
    this.client = client;
    this.transport = transport;
  }

  async close(): Promise<void> {
    const { client, transport } = this;
    this.client = null;
    this.transport = null;
    if (client) await client.close();
    if (transport) await transport.close();
  }

  private require(): Client {
    if (!this.client) throw new Error("Client is not connected; call connect() first");
    return this.client;
  }

  async listTools(): Promise<ToolInfo[]> {
    const res = await this.require().listTools();
    return res.tools.map((t) => ({
      name: t.name,
      description: t.description,
      inputSchema: (t.inputSchema ?? {}) as Record<string, unknown>,
    }));
  }

  async callTool(
    name: string,
    args: Record<string, unknown>,
    options: CallToolOptions = {},
  ): Promise<CallOutcome> {
    const client = this.require();
    const start = performance.now();
    const callPromise = client.callTool({ name, arguments: args });

    let raw: Awaited<ReturnType<Client["callTool"]>>;
    try {
      if (options.timeoutMs !== undefined) {
        raw = await withTimeout(callPromise, options.timeoutMs);
      } else {
        raw = await callPromise;
      }
    } catch (e) {
      const elapsed = performance.now() - start;
      return {
        isError: true,
        text: e instanceof Error ? e.message : String(e),
        structured: null,
        latencyMs: elapsed,
      };
    }

    const elapsed = performance.now() - start;
    const contentBlocks = Array.isArray(raw.content) ? raw.content : [];
    const text = contentBlocks
      .filter(
        (b): b is { type: "text"; text: string } =>
          typeof (b as { type?: unknown }).type === "string" &&
          (b as { type: string }).type === "text",
      )
      .map((b) => b.text)
      .join("\n");
    return {
      isError: Boolean(raw.isError),
      text,
      structured: (raw as { structuredContent?: unknown }).structuredContent ?? null,
      latencyMs: elapsed,
      raw,
    };
  }
}

async function withTimeout<T>(p: Promise<T>, ms: number): Promise<T> {
  let timer: NodeJS.Timeout | undefined;
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(new Error(`Timeout after ${ms}ms`)), ms);
  });
  try {
    return await Promise.race([p, timeout]);
  } finally {
    if (timer) clearTimeout(timer);
  }
}
