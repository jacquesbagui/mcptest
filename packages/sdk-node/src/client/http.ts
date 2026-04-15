import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";
import type { Transport } from "@modelcontextprotocol/sdk/shared/transport.js";
import { SessionClient } from "./session.js";

export interface HttpClientOptions {
  url: string;
  headers?: Record<string, string>;
}

export class HttpMcpClient extends SessionClient {
  private readonly url: URL;
  private readonly headers: Record<string, string> | undefined;

  constructor(options: HttpClientOptions) {
    super();
    this.url = new URL(options.url);
    this.headers = options.headers;
  }

  protected override createTransport(): Transport {
    return new StreamableHTTPClientTransport(this.url, {
      ...(this.headers ? { requestInit: { headers: this.headers } } : {}),
    }) as unknown as Transport;
  }
}

export class SseMcpClient extends SessionClient {
  private readonly url: URL;
  private readonly headers: Record<string, string> | undefined;

  constructor(options: HttpClientOptions) {
    super();
    this.url = new URL(options.url);
    this.headers = options.headers;
  }

  protected override createTransport(): Transport {
    return new SSEClientTransport(this.url, {
      ...(this.headers ? { requestInit: { headers: this.headers } } : {}),
    }) as unknown as Transport;
  }
}
