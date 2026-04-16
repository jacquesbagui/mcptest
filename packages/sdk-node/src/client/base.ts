import type {
  CallOutcome,
  PromptInfo,
  PromptResult,
  ResourceContent,
  ResourceInfo,
  ToolInfo,
} from "../types.js";

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
  listResources(): Promise<ResourceInfo[]>;
  readResource(uri: string): Promise<ResourceContent>;
  listPrompts(): Promise<PromptInfo[]>;
  getPrompt(name: string, args: Record<string, unknown>): Promise<PromptResult>;
}
