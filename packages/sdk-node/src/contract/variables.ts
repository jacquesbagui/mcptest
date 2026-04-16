const VAR_RE = /\$\{\{\s*steps\.(\w+)\.result((?:\.\w+)*)\s*\}\}/g;
const VAR_FULL_RE = /^\$\{\{\s*steps\.(\w+)\.result((?:\.\w+)*)\s*\}\}$/;

export class VariableError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "VariableError";
  }
}

function walkPath(obj: unknown, path: string[]): unknown {
  let current = obj;
  for (const segment of path) {
    if (current === null || current === undefined) {
      throw new VariableError(`cannot traverse into ${typeof current} with '${segment}'`);
    }
    if (typeof current === "object" && !Array.isArray(current)) {
      const rec = current as Record<string, unknown>;
      if (!(segment in rec)) {
        throw new VariableError(`path segment '${segment}' not found in [${Object.keys(rec).join(", ")}]`);
      }
      current = rec[segment];
    } else if (Array.isArray(current)) {
      const idx = Number(segment);
      if (Number.isNaN(idx) || idx < 0 || idx >= current.length) {
        throw new VariableError(`invalid list index '${segment}'`);
      }
      current = current[idx];
    } else {
      throw new VariableError(`cannot traverse into ${typeof current} with '${segment}'`);
    }
  }
  return current;
}

interface StepData {
  text?: string;
  structured?: unknown;
  is_error?: boolean;
}

function extractResult(data: unknown): unknown {
  if (typeof data === "object" && data !== null && !Array.isArray(data)) {
    const d = data as StepData;
    if (d.structured !== null && d.structured !== undefined) return d.structured;
    const text = d.text ?? "";
    if (text) {
      try {
        return JSON.parse(text);
      } catch {
        /* not JSON */
      }
    }
    return text;
  }
  return data;
}

function resolveSingle(stepName: string, pathStr: string, context: Record<string, unknown>): unknown {
  if (!(stepName in context)) {
    throw new VariableError(`step '${stepName}' not found; available: [${Object.keys(context).join(", ")}]`);
  }
  const result = extractResult(context[stepName]);
  if (!pathStr) return result;
  const path = pathStr.split(".").filter(Boolean);
  return walkPath(result, path);
}

export function resolveValue(template: unknown, context: Record<string, unknown>): unknown {
  if (typeof template === "string") {
    const full = VAR_FULL_RE.exec(template);
    if (full) {
      return resolveSingle(full[1]!, full[2]!, context);
    }
    return template.replace(VAR_RE, (_match, step: string, path: string) =>
      String(resolveSingle(step, path, context)),
    );
  }
  if (Array.isArray(template)) {
    return template.map((v) => resolveValue(v, context));
  }
  if (typeof template === "object" && template !== null) {
    const result: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(template)) {
      result[k] = resolveValue(v, context);
    }
    return result;
  }
  return template;
}
