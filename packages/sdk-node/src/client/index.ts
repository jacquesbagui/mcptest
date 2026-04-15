import type { ServerConfig } from "../contract/schema.js";
import type { McpClient } from "./base.js";
import { StdioMcpClient } from "./stdio.js";

export { StdioMcpClient } from "./stdio.js";
export type { McpClient, CallToolOptions } from "./base.js";

export function buildClient(config: ServerConfig): McpClient {
  if (config.transport === "stdio") {
    if (!config.command) throw new Error("stdio transport requires server.command");
    return new StdioMcpClient({
      command: config.command,
      args: config.args,
      ...(Object.keys(config.env).length > 0 ? { env: config.env } : {}),
      ...(config.cwd !== undefined ? { cwd: config.cwd } : {}),
    });
  }
  throw new Error(`Transport '${config.transport}' is not implemented yet`);
}
