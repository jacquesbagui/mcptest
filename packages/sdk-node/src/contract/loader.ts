import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { parse } from "yaml";
import { ContractSchema, type Contract } from "./schema.js";

export class ContractError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ContractError";
  }
}

export function loadContract(path: string): Contract {
  const abs = resolve(path);
  let raw: string;
  try {
    raw = readFileSync(abs, "utf-8");
  } catch {
    throw new ContractError(`Contract file not found: ${abs}`);
  }

  let data: unknown;
  try {
    data = parse(raw);
  } catch (e) {
    throw new ContractError(
      `Invalid YAML in ${abs}: ${e instanceof Error ? e.message : String(e)}`,
    );
  }

  if (typeof data !== "object" || data === null || Array.isArray(data)) {
    throw new ContractError(`Contract root must be a mapping, got ${typeof data}`);
  }

  const parsed = ContractSchema.safeParse(data);
  if (!parsed.success) {
    throw new ContractError(
      `Contract schema validation failed for ${abs}:\n${parsed.error.message}`,
    );
  }
  return parsed.data;
}
