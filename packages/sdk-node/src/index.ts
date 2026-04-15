export { McpTest, Expectation, AssertionError } from "./McpTest.js";
export type { McpTestOptions, StdioOptions } from "./McpTest.js";
export { buildClient, StdioMcpClient, HttpMcpClient, SseMcpClient } from "./client/index.js";
export type { McpClient, CallToolOptions } from "./client/base.js";
export { loadContract, ContractError } from "./contract/loader.js";
export { runContract } from "./contract/engine.js";
export {
  ContractSchema,
  ServerConfigSchema,
  ToolSpecSchema,
} from "./contract/schema.js";
export type {
  Assertion,
  CallSpec,
  Contract,
  Expectation as ContractExpectation,
  InputSchemaAssertion,
  ServerConfig,
  SnapshotConfig,
  ToolSpec,
  Transport,
} from "./contract/schema.js";
export { Report } from "./types.js";
export type { CallOutcome, CheckResult, CheckStatus, ToolInfo } from "./types.js";
export {
  captureSnapshot,
  diffSnapshots,
  loadSnapshot,
  saveSnapshot,
  SNAPSHOT_VERSION,
} from "./snapshot/index.js";
export type { DiffEntry, DiffKind, Snapshot, SnapshotDiff, SnapshotTool } from "./snapshot/index.js";
