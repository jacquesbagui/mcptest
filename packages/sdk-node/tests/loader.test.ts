import { writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { ContractError, loadContract } from "../src/index.js";

function tmpFile(content: string): string {
  const dir = mkdtempSync(join(tmpdir(), "mcptest-"));
  const path = join(dir, "c.yaml");
  writeFileSync(path, content, "utf-8");
  return path;
}

describe("loadContract", () => {
  it("loads a valid contract", () => {
    const path = tmpFile(`
server:
  transport: stdio
  command: python -c pass
tools:
  - name: echo
    assertions:
      - call:
          args: { message: hi }
        expect:
          status: success
`);
    const c = loadContract(path);
    expect(c.tools[0]?.name).toBe("echo");
    expect(c.tools[0]?.assertions[0]?.call.args).toEqual({ message: "hi" });
  });

  it("rejects missing file", () => {
    expect(() => loadContract("/no/such/file.yaml")).toThrow(ContractError);
  });

  it("rejects unknown keys", () => {
    const path = tmpFile(`
server:
  transport: stdio
  command: x
  unknown: 1
`);
    expect(() => loadContract(path)).toThrow(ContractError);
  });

  it("requires command for stdio", () => {
    const path = tmpFile(`
server:
  transport: stdio
`);
    expect(() => loadContract(path)).toThrow(/command is required/);
  });

  it("requires url for http", () => {
    const path = tmpFile(`
server:
  transport: http
`);
    expect(() => loadContract(path)).toThrow(/url is required/);
  });
});
