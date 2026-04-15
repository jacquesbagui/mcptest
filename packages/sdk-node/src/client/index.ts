import type { ServerConfig } from "../contract/schema.js";
import type { McpClient } from "./base.js";
import { HttpMcpClient, SseMcpClient } from "./http.js";
import { StdioMcpClient } from "./stdio.js";

export { StdioMcpClient } from "./stdio.js";
export { HttpMcpClient, SseMcpClient } from "./http.js";
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
  if (config.transport === "http") {
    if (!config.url) throw new Error("http transport requires server.url");
    return new HttpMcpClient({ url: config.url });
  }
  if (config.transport === "sse") {
    if (!config.url) throw new Error("sse transport requires server.url");
    return new SseMcpClient({ url: config.url });
  }
  throw new Error(`Transport '${config.transport as string}' is not implemented yet`);
}
