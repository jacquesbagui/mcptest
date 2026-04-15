import { existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { McpTest, loadContract, runContract, buildClient } from "../src/index.js";

const REPO = resolve(__dirname, "../../..");
const TOY = join(REPO, "packages/core/examples/toy_server.py");
const VENV_PY = join(REPO, "packages/core/.venv/bin/python");

function canRunToy(): boolean {
  return existsSync(VENV_PY) && existsSync(TOY);
}

describe("e2e against toy MCP server", () => {
  it("runs the example contract with all checks passing", async () => {
    if (!canRunToy()) return;
    const contract = loadContract(join(REPO, "contracts/example.yaml"));
    const patched = {
      ...contract,
      server: { ...contract.server, command: VENV_PY, args: [TOY] },
    };
    const client = buildClient(patched.server);
    await client.connect();
    try {
      const report = await runContract(patched, client);
      expect(
        report.checks.filter((c) => c.status === "fail"),
      ).toEqual([]);
      expect(report.passed).toBeGreaterThan(0);
    } finally {
      await client.close();
    }
  });

  it("exposes a fluent McpTest API", async () => {
    if (!canRunToy()) return;
    const t = new McpTest({ transport: "stdio", command: VENV_PY, args: [TOY] });
    await t.connect();
    try {
      await t.assertToolExists("echo");
      const out = await t.call("echo", { message: "hello" });
      t.expect(out).toSucceed().toContain("hello").withinMs(5000);

      const boom = await t.call("boom", {});
      t.expect(boom).toError();
    } finally {
      await t.disconnect();
    }
  });
});
