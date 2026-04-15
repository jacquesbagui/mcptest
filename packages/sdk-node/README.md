# @mcptest/sdk (Node.js)

> TypeScript SDK for [mcptest](https://github.com/jacquesbagui/mcptest) —
> contract testing for MCP servers, usable from any Node test runner.

**Status:** not yet released. See the [repository README](../../README.md) and
the Python `mcptest` package in [`../core`](../core) for the current shipped
functionality.

## Planned API

```ts
import { McpTest } from "mcptest";

const tester = new McpTest({
  transport: "stdio",
  command: "python server.py",
});

await tester.connect();
await tester.assertToolExists("search_files");

const result = await tester.call("search_files", { query: "hello" });
tester.expect(result).toSucceed().withinMs(1000);

const report = await tester.runContract("./contracts/my-server.yaml");
console.log(report.summary());

await tester.disconnect();
```

Contract YAML files are **the same schema** as the Python core — a single
contract runs identically from either language.

## License

MIT — see [LICENSE](../../LICENSE).
