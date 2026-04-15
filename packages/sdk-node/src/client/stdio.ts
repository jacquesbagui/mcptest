import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import type { Transport } from "@modelcontextprotocol/sdk/shared/transport.js";
import { SessionClient } from "./session.js";

export interface StdioClientOptions {
  command: string;
  args?: string[];
  env?: Record<string, string>;
  cwd?: string;
  /** Forward child stderr to this process's stderr. Defaults to inheriting. */
  inheritStderr?: boolean;
}

function splitCommand(cmd: string): { command: string; args: string[] } {
  const parts = cmd.trim().match(/(?:[^\s"']+|"[^"]*"|'[^']*')+/g) ?? [];
  if (parts.length === 0) throw new Error("command must not be empty");
  const stripped = parts.map((p) =>
    (p.startsWith('"') && p.endsWith('"')) || (p.startsWith("'") && p.endsWith("'"))
      ? p.slice(1, -1)
      : p,
  );
  const [command, ...args] = stripped as [string, ...string[]];
  return { command, args };
}

export class StdioMcpClient extends SessionClient {
  private readonly command: string;
  private readonly args: string[];
  private readonly env: Record<string, string> | undefined;
  private readonly cwd: string | undefined;
  private readonly inheritStderr: boolean;

  constructor(options: StdioClientOptions) {
    super();
    if (options.args === undefined) {
      const split = splitCommand(options.command);
      this.command = split.command;
      this.args = split.args;
    } else {
      this.command = options.command;
      this.args = options.args;
    }
    this.env = options.env;
    this.cwd = options.cwd;
    this.inheritStderr = options.inheritStderr ?? false;
  }

  protected override createTransport(): Transport {
    return new StdioClientTransport({
      command: this.command,
      args: this.args,
      stderr: this.inheritStderr ? "inherit" : "ignore",
      ...(this.env ? { env: this.env } : {}),
      ...(this.cwd ? { cwd: this.cwd } : {}),
    });
  }
}
