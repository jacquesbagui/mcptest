import { describe, expect, it } from "vitest";
import { diffSnapshots, type Snapshot, SNAPSHOT_VERSION } from "../src/index.js";

function snap(tools: Snapshot["tools"]): Snapshot {
  return { version: SNAPSHOT_VERSION, captured_at: "t", server: null, tools };
}

describe("diffSnapshots", () => {
  it("detects added and removed tools", () => {
    const base = snap({ a: { description: "A", input_schema: {} } });
    const cur = snap({ b: { description: "B", input_schema: {} } });
    const diff = diffSnapshots(base, cur);
    expect(diff.entries.map((e) => [e.tool, e.kind]).sort()).toEqual([
      ["a", "removed"],
      ["b", "added"],
    ]);
    expect(diff.hasBreaking).toBe(true);
  });

  it("detects schema changes and classifies them", () => {
    const base = snap({
      t: {
        description: "d",
        input_schema: {
          required: ["x"],
          properties: { x: { type: "string" }, y: { type: "integer" } },
        },
      },
    });
    const cur = snap({
      t: {
        description: "d",
        input_schema: { required: [], properties: { x: { type: "integer" } } },
      },
    });
    const diff = diffSnapshots(base, cur);
    expect(diff.entries).toHaveLength(1);
    const [e] = diff.entries;
    expect(e?.kind).toBe("changed");
    expect(e?.details.some((d) => d.startsWith("required removed: x"))).toBe(true);
    expect(e?.details.some((d) => d.startsWith("property removed: y"))).toBe(true);
    expect(e?.details.some((d) => d.startsWith("type changed on x"))).toBe(true);
    expect(diff.hasBreaking).toBe(true);
  });

  it("additions only are not breaking", () => {
    const base = snap({ a: { description: "A", input_schema: {} } });
    const cur = snap({
      a: { description: "A", input_schema: {} },
      b: { description: "B", input_schema: {} },
    });
    const diff = diffSnapshots(base, cur);
    expect(diff.hasChanges).toBe(true);
    expect(diff.hasBreaking).toBe(false);
  });
});
