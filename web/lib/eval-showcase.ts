import rawShowcase from "../data/evals/latest.json";

export type EvalStatus = "pass" | "fail" | "cannot_determine";
export type EvalCategory =
  | "conversation"
  | "social_dynamics"
  | "pairing_and_endings"
  | "special_events"
  | "challenges";

export type EvalCheck = {
  id: string;
  kind: "deterministic" | "judge";
  result: EvalStatus;
  reason: string;
  evidence: string | null;
};

export type EvalTrace = {
  agent: string;
  model: string;
  reasoning_effort: string;
  output_type: string | null;
  latency_ms: number | null;
  input_tokens?: number | null;
  cached_input_tokens?: number | null;
  cache_write_tokens?: number | null;
  output_tokens?: number | null;
  reasoning_tokens?: number | null;
  total_tokens: number | null;
  cost?: EvalCost | null;
  output?: unknown;
  reasoning_summaries?: string[];
  attempt: number;
};

export type EvalGoldenCall = {
  agent: string;
  output_type: string;
  output: Record<string, unknown> | null;
  criteria: string[];
};

export type EvalGolden = {
  calls: EvalGoldenCall[];
};

export type EvalUsage = {
  input_tokens?: number;
  cached_input_tokens?: number;
  cache_write_tokens?: number;
  output_tokens?: number;
  reasoning_tokens?: number;
  total_tokens: number;
};

export type EvalCost = {
  currency?: "USD";
  kind: "exact" | "range" | "unavailable";
  total_usd?: number | null;
  minimum_usd?: number | null;
  maximum_usd?: number | null;
  input_usd?: number | null;
  cached_input_usd?: number | null;
  cache_write_usd?: number | null;
  output_usd?: number | null;
  input_rate_per_million?: number | null;
  cached_input_rate_per_million?: number | null;
  cache_write_rate_per_million?: number | null;
  output_rate_per_million?: number | null;
  pricing_source: string;
  pricing_as_of: string;
};

export type EvalAccounting = {
  usage: EvalUsage;
  cost: EvalCost;
};

export type EvalStory = {
  engine_result: string | null;
  engine_details?: { label: string; value: string }[];
  relationship_changes: string[];
  dialogue: { player: string; npc: string; tone: string | null; mood_after: string | null } | null;
  narration: string | null;
  choices: { label: string; category: string; risk: string }[];
  events: string[];
  memories: string[];
  resort_changes: string | null;
};

export type EvalTurn = {
  id: string;
  action: string;
  status: EvalStatus;
  golden: EvalGolden;
  story: EvalStory;
  checks: EvalCheck[];
  traces: EvalTrace[];
};

export type EvalScenario = {
  id: string;
  title: string;
  question: string;
  category: EvalCategory;
  goal: string;
  status: EvalStatus;
  judge: {
    result: EvalStatus;
    reason: string;
    evidence: string | null;
    model: string | null;
    reasoning_effort: string | null;
    latency_ms: number | null;
    input_tokens?: number | null;
    cached_input_tokens?: number | null;
    cache_write_tokens?: number | null;
    output_tokens?: number | null;
    reasoning_tokens?: number | null;
    total_tokens: number | null;
    cost?: EvalCost | null;
    reasoning_summaries?: string[];
    criteria: string[];
    criterion_findings: EvalCheck[];
  } | null;
  turns: EvalTurn[];
};

export type EvalShowcase = {
  schema_version: 6;
  llm_mode: "mock" | "real";
  judge_enabled: boolean;
  passed: number;
  failed: number;
  cannot_determine: number;
  turn_count: number;
  agent_call_count: number;
  total_tokens: number;
  accounting: {
    game_agents: EvalAccounting;
    judges: EvalAccounting;
    total: EvalAccounting;
  };
  provenance: {
    published_at: string | null;
    source_revision: string | null;
    note: string | null;
  };
  scenarios: EvalScenario[];
};

export const CATEGORY_ORDER: EvalCategory[] = [
  "conversation",
  "social_dynamics",
  "pairing_and_endings",
  "special_events",
  "challenges",
];

export const CATEGORY_LABELS: Record<EvalCategory, string> = {
  conversation: "Conversation",
  social_dynamics: "Social dynamics",
  pairing_and_endings: "Pairing & endings",
  special_events: "Special events",
  challenges: "Challenges",
};

export const DEFAULT_SCENARIO = "conversation-continuity-exit";

export const evalShowcase = parseShowcase(rawShowcase);

export function getScenario(id: string) {
  return evalShowcase?.scenarios.find((scenario) => scenario.id === id) ?? null;
}

function parseShowcase(value: unknown): EvalShowcase | null {
  if (!value || typeof value !== "object") return null;
  const candidate = value as Partial<EvalShowcase>;
  if (
    candidate.schema_version !== 6 ||
    !Array.isArray(candidate.scenarios) ||
    typeof candidate.passed !== "number" ||
    typeof candidate.turn_count !== "number" ||
    !candidate.accounting
  ) {
    return null;
  }
  return candidate as EvalShowcase;
}
