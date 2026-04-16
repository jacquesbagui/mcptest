import { z } from "zod";

export const TransportSchema = z.enum(["stdio", "http", "sse"]);
export type Transport = z.infer<typeof TransportSchema>;

export const ServerConfigSchema = z
  .object({
    name: z.string().optional(),
    transport: TransportSchema.default("stdio"),
    command: z.string().optional(),
    args: z.array(z.string()).default([]),
    env: z.record(z.string()).default({}),
    url: z.string().optional(),
    cwd: z.string().optional(),
  })
  .strict()
  .superRefine((cfg, ctx) => {
    if (cfg.transport === "stdio" && !cfg.command) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "server.command is required for stdio transport",
      });
    }
    if ((cfg.transport === "http" || cfg.transport === "sse") && !cfg.url) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: `server.url is required for ${cfg.transport} transport`,
      });
    }
  });
export type ServerConfig = z.infer<typeof ServerConfigSchema>;

const StringOrStringArray = z.union([z.string(), z.array(z.string())]);

export const InputSchemaAssertionSchema = z
  .object({
    required: z.array(z.string()).default([]),
    properties: z.record(z.record(z.unknown())).default({}),
  })
  .strict();
export type InputSchemaAssertion = z.infer<typeof InputSchemaAssertionSchema>;

export const CallSpecSchema = z
  .object({
    args: z.record(z.unknown()).default({}),
    timeout_ms: z.number().int().positive().optional(),
  })
  .strict();
export type CallSpec = z.infer<typeof CallSpecSchema>;

export const ExpectationSchema = z
  .object({
    status: z.enum(["success", "error"]).default("success"),
    response_contains: StringOrStringArray.optional(),
    max_latency_ms: z.number().int().positive().optional(),
    schema: z.record(z.unknown()).optional(),
  })
  .strict();
export type Expectation = z.infer<typeof ExpectationSchema>;

export const AssertionSchema = z
  .object({
    name: z.string().optional(),
    call: CallSpecSchema,
    expect: ExpectationSchema.default({}),
  })
  .strict();
export type Assertion = z.infer<typeof AssertionSchema>;

export const ToolSpecSchema = z
  .object({
    name: z.string(),
    must_exist: z.boolean().default(true),
    description_contains: StringOrStringArray.optional(),
    input_schema: InputSchemaAssertionSchema.optional(),
    assertions: z.array(AssertionSchema).default([]),
  })
  .strict();
export type ToolSpec = z.infer<typeof ToolSpecSchema>;

export const ResourceSpecSchema = z
  .object({
    uri: z.string().optional(),
    uri_pattern: z.string().optional(),
    must_exist: z.boolean().default(true),
    min_count: z.number().int().nonnegative().optional(),
    content_contains: z.union([z.string(), z.array(z.string())]).optional(),
    content_schema: z.record(z.string(), z.unknown()).optional(),
  })
  .strict()
  .superRefine((s, ctx) => {
    if (!s.uri && !s.uri_pattern)
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: "resource spec requires 'uri' or 'uri_pattern'" });
    if (s.uri && s.uri_pattern)
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: "resource spec cannot have both 'uri' and 'uri_pattern'" });
  });
export type ResourceSpec = z.infer<typeof ResourceSpecSchema>;

export const PromptArgSpecSchema = z
  .object({
    name: z.string(),
    required: z.boolean().default(true),
  })
  .strict();
export type PromptArgSpec = z.infer<typeof PromptArgSpecSchema>;

export const PromptGetSpecSchema = z
  .object({
    args: z.record(z.string(), z.unknown()).default({}),
  })
  .strict();

export const PromptExpectationSchema = z
  .object({
    messages_contain: z.union([z.string(), z.array(z.string())]).optional(),
    message_count: z.number().int().nonnegative().optional(),
    messages_schema: z.record(z.string(), z.unknown()).optional(),
  })
  .strict();
export type PromptExpectation = z.infer<typeof PromptExpectationSchema>;

export const PromptAssertionSchema = z
  .object({
    get_prompt: PromptGetSpecSchema,
    expect: PromptExpectationSchema.default({}),
  })
  .strict();
export type PromptAssertion = z.infer<typeof PromptAssertionSchema>;

export const PromptSpecSchema = z
  .object({
    name: z.string(),
    must_exist: z.boolean().default(true),
    description_contains: z.union([z.string(), z.array(z.string())]).optional(),
    arguments: z.array(PromptArgSpecSchema).default([]),
    assertions: z.array(PromptAssertionSchema).default([]),
  })
  .strict();
export type PromptSpec = z.infer<typeof PromptSpecSchema>;

export const SnapshotConfigSchema = z
  .object({
    enabled: z.boolean().default(false),
    baseline: z.string().default(".mcpact/baseline.json"),
    fail_on_regression: z.boolean().default(true),
    warn_on_addition: z.boolean().default(false),
  })
  .strict();
export type SnapshotConfig = z.infer<typeof SnapshotConfigSchema>;

export const ContractSchema = z
  .object({
    server: ServerConfigSchema,
    tools: z.array(ToolSpecSchema).default([]),
    resources: z.array(ResourceSpecSchema).default([]),
    prompts: z.array(PromptSpecSchema).default([]),
    snapshots: SnapshotConfigSchema.default({}),
  })
  .strict();
export type Contract = z.infer<typeof ContractSchema>;
