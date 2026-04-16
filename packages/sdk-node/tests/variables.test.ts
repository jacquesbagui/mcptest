import { describe, expect, it } from "vitest";
import { resolveValue, VariableError } from "../src/contract/variables.js";

function ctx(): Record<string, unknown> {
  return {
    create: {
      text: '{"id": "abc123", "title": "hello"}',
      structured: { id: "abc123", title: "hello" },
      is_error: false,
    },
    list: {
      text: "[]",
      structured: { result: [{ id: "abc123" }] },
      is_error: false,
    },
  };
}

describe("resolveValue", () => {
  it("passes through non-variable strings", () => {
    expect(resolveValue("hello", {})).toBe("hello");
  });

  it("passes through non-string types", () => {
    expect(resolveValue(42, {})).toBe(42);
    expect(resolveValue(null, {})).toBe(null);
  });

  it("preserves type for full replacement", () => {
    const r = resolveValue("${{ steps.create.result }}", ctx());
    expect(r).toEqual({ id: "abc123", title: "hello" });
  });

  it("resolves nested paths", () => {
    expect(resolveValue("${{ steps.create.result.id }}", ctx())).toBe("abc123");
  });

  it("resolves array indices", () => {
    expect(resolveValue("${{ steps.list.result.result.0.id }}", ctx())).toBe("abc123");
  });

  it("string-interpolates when embedded", () => {
    expect(resolveValue("id=${{ steps.create.result.id }}", ctx())).toBe("id=abc123");
  });

  it("resolves in dicts", () => {
    expect(resolveValue({ uid: "${{ steps.create.result.id }}" }, ctx())).toEqual({
      uid: "abc123",
    });
  });

  it("resolves in arrays", () => {
    expect(resolveValue(["${{ steps.create.result.id }}"], ctx())).toEqual(["abc123"]);
  });

  it("throws on missing step", () => {
    expect(() => resolveValue("${{ steps.nope.result }}", {})).toThrow(VariableError);
  });

  it("throws on missing path segment", () => {
    expect(() => resolveValue("${{ steps.create.result.nope }}", ctx())).toThrow(VariableError);
  });

  it("falls back to parsed text when structured is null", () => {
    const c = { txt: { text: '{"x": 42}', structured: null, is_error: false } };
    expect(resolveValue("${{ steps.txt.result.x }}", c)).toBe(42);
  });

  it("falls back to raw text when JSON parse fails", () => {
    const c = { txt: { text: "plain string", structured: null, is_error: false } };
    expect(resolveValue("${{ steps.txt.result }}", c)).toBe("plain string");
  });
});
