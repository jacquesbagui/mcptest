export interface ToolInfo {
  readonly name: string;
  readonly description: string | undefined;
  readonly inputSchema: Record<string, unknown>;
}

export interface CallOutcome {
  readonly isError: boolean;
  readonly text: string;
  readonly structured: unknown;
  readonly latencyMs: number;
  readonly raw?: unknown;
}

export interface ResourceInfo {
  readonly uri: string;
  readonly name: string | undefined;
  readonly description: string | undefined;
  readonly mimeType: string | undefined;
}

export interface ResourceContent {
  readonly uri: string;
  readonly text: string;
  readonly mimeType: string | undefined;
}

export interface PromptArgInfo {
  readonly name: string;
  readonly description: string | undefined;
  readonly required: boolean;
}

export interface PromptInfo {
  readonly name: string;
  readonly description: string | undefined;
  readonly arguments: PromptArgInfo[];
}

export interface PromptMessage {
  readonly role: string;
  readonly text: string;
}

export interface PromptResult {
  readonly description: string | undefined;
  readonly messages: PromptMessage[];
}

export type CheckStatus = "pass" | "fail" | "skip";

export interface CheckResult {
  readonly subject: string;
  readonly check: string;
  readonly status: CheckStatus;
  readonly message?: string;
  readonly latencyMs?: number;
}

export class Report {
  readonly checks: CheckResult[] = [];

  add(result: CheckResult): void {
    this.checks.push(result);
  }

  get passed(): number {
    return this.checks.filter((c) => c.status === "pass").length;
  }
  get failed(): number {
    return this.checks.filter((c) => c.status === "fail").length;
  }
  get skipped(): number {
    return this.checks.filter((c) => c.status === "skip").length;
  }
  get total(): number {
    return this.checks.length;
  }
  get ok(): boolean {
    return this.failed === 0;
  }

  summary(): string {
    return `${this.total} checks · ${this.passed} passed · ${this.failed} failed${
      this.skipped > 0 ? ` · ${this.skipped} skipped` : ""
    }`;
  }
}
