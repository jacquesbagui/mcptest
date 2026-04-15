import type { CallOutcome, ToolInfo } from "../types.js";

export interface CallToolOptions {
  timeoutMs?: number;
}

export interface McpClient {
  connect(): Promise<void>;
  close(): Promise<void>;
  listTools(): Promise<ToolInfo[]>;
  callTool(
    name: string,
    args: Record<string, unknown>,
    options?: CallToolOptions,
  ): Promise<CallOutcome>;
}
