# mcpcheck (Node.js SDK)

TypeScript SDK for [mcpcheck](https://github.com/jacquesbagui/mcpcheck) — contract
testing for MCP servers, usable from any Node test runner.

> Pre-release. Not yet published to npm. Build locally with `pnpm build` to try it.

## Install

```bash
npm install mcpcheck
```

Requires Node.js 20+.

## Fluent API

```ts
import { McpTest } from "mcpcheck";

const t = new McpTest({ transport: "stdio", command: "python server.py" });
await t.connect();

await t.assertToolExists("search_files");

const out = await t.call("search_files", { query: "hello" });
t.expect(out).toSucceed().toContain("hello").withinMs(1000);

await t.disconnect();
```

Works with Jest, Vitest, and any other Node test runner — no runtime
integration required.

## Run a YAML contract

The contract format is identical to the Python core. The same file runs in
either language.

```ts
import { McpTest } from "mcpcheck";

const t = new McpTest({ transport: "stdio", command: "python server.py" });
await t.connect();
const report = await t.runContract("./contracts/my-server.yaml");
console.log(report.summary());
await t.disconnect();

if (!report.ok) process.exit(1);
```

## Low-level API

If you don't want the fluent wrapper:

```ts
import { buildClient, loadContract, runContract } from "mcpcheck";

const contract = loadContract("./contracts/my-server.yaml");
const client = buildClient(contract.server);
await client.connect();
try {
  const report = await runContract(contract, client);
  console.log(report.summary());
} finally {
  await client.close();
}
```

## Development

```bash
pnpm install
pnpm typecheck
pnpm test
pnpm build
```

## License

MIT — see [LICENSE](../../LICENSE).
