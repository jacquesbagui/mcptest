import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import type { McpClient } from "../client/base.js";

export const SNAPSHOT_VERSION = 1;

export interface Snapshot {
  version: number;
  captured_at: string;
  server: string | null;
  tools: Record<string, SnapshotTool>;
}

export interface SnapshotTool {
  description: string | null;
  input_schema: Record<string, unknown>;
}

export type DiffKind = "added" | "removed" | "changed";

export interface DiffEntry {
  tool: string;
  kind: DiffKind;
  details: string[];
}

export interface SnapshotDiff {
  entries: DiffEntry[];
  hasChanges: boolean;
  hasBreaking: boolean;
}

export async function captureSnapshot(
  client: McpClient,
  serverName: string | null = null,
): Promise<Snapshot> {
  const tools = await client.listTools();
  const sorted = [...tools].sort((a, b) => a.name.localeCompare(b.name));
  const payload: Record<string, SnapshotTool> = {};
  for (const t of sorted) {
    payload[t.name] = {
      description: t.description ?? null,
      input_schema: t.inputSchema,
    };
  }
  return {
    version: SNAPSHOT_VERSION,
    captured_at: new Date().toISOString().replace(/\.\d{3}Z$/, "+00:00"),
    server: serverName,
    tools: payload,
  };
}

export function saveSnapshot(snapshot: Snapshot, path: string): void {
  const abs = resolve(path);
  mkdirSync(dirname(abs), { recursive: true });
  writeFileSync(abs, JSON.stringify(snapshot, null, 2), "utf-8");
}

export function loadSnapshot(path: string): Snapshot {
  const abs = resolve(path);
  const raw = readFileSync(abs, "utf-8");
  const parsed = JSON.parse(raw) as Partial<Snapshot>;
  return {
    version: parsed.version ?? SNAPSHOT_VERSION,
    captured_at: parsed.captured_at ?? "",
    server: parsed.server ?? null,
    tools: parsed.tools ?? {},
  };
}

const BREAKING_PREFIXES = ["required ", "type ", "property removed"];

function isBreaking(entry: DiffEntry): boolean {
  if (entry.kind === "removed") return true;
  if (entry.kind === "changed") {
    return entry.details.some((d) => BREAKING_PREFIXES.some((p) => d.startsWith(p)));
  }
  return false;
}

export function diffSnapshots(baseline: Snapshot, current: Snapshot): SnapshotDiff {
  const base = baseline.tools;
  const cur = current.tools;
  const entries: DiffEntry[] = [];

  for (const name of Object.keys(base).sort()) {
    if (!(name in cur)) entries.push({ tool: name, kind: "removed", details: [] });
  }
  for (const name of Object.keys(cur).sort()) {
    if (!(name in base)) entries.push({ tool: name, kind: "added", details: [] });
  }
  for (const name of Object.keys(base).sort()) {
    if (!(name in cur)) continue;
    const details = diffTool(base[name]!, cur[name]!);
    if (details.length > 0) entries.push({ tool: name, kind: "changed", details });
  }

  let hasBreaking = false;
  for (const e of entries) if (isBreaking(e)) hasBreaking = true;
  return { entries, hasChanges: entries.length > 0, hasBreaking };
}

function diffTool(base: SnapshotTool, current: SnapshotTool): string[] {
  const details: string[] = [];
  if (base.description !== current.description) details.push("description changed");

  const bSchema = base.input_schema ?? {};
  const cSchema = current.input_schema ?? {};
  const bReq = new Set(asStringArray(bSchema["required"]));
  const cReq = new Set(asStringArray(cSchema["required"]));
  for (const r of [...bReq].filter((x) => !cReq.has(x)).sort()) {
    details.push(`required removed: ${r}`);
  }
  for (const r of [...cReq].filter((x) => !bReq.has(x)).sort()) {
    details.push(`required added: ${r}`);
  }
  const bProps = asPropMap(bSchema["properties"]);
  const cProps = asPropMap(cSchema["properties"]);
  for (const p of Object.keys(bProps).filter((x) => !(x in cProps)).sort()) {
    details.push(`property removed: ${p}`);
  }
  for (const p of Object.keys(cProps).filter((x) => !(x in bProps)).sort()) {
    details.push(`property added: ${p}`);
  }
  for (const p of Object.keys(bProps).filter((x) => x in cProps).sort()) {
    const bType = bProps[p]?.type;
    const cType = cProps[p]?.type;
    if (bType !== cType) details.push(`type changed on ${p}: '${bType}' → '${cType}'`);
  }
  return details;
}

function asStringArray(v: unknown): string[] {
  return Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : [];
}

function asPropMap(v: unknown): Record<string, { type?: string }> {
  if (!v || typeof v !== "object") return {};
  return v as Record<string, { type?: string }>;
}
