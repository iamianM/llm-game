import type { EvalAccounting, EvalCost, EvalScenario, EvalShowcase, EvalUsage } from "./eval-showcase";

type UsageLike = { [K in keyof EvalUsage]?: EvalUsage[K] | null };

export type CostBreakdown = {
  agentTokens: number;
  judgeTokens: number;
  totalTokens: number;
  inputTokens: number;
  cachedInputTokens: number;
  outputTokens: number;
  exactCost: number | null;
  minimumCost: number | null;
  maximumCost: number | null;
  agentCost: EvalCost;
  judgeCost: EvalCost;
  pricingSource: string;
  pricingAsOf: string;
};

export function runCostBreakdown(showcase: EvalShowcase): CostBreakdown {
  return fromAccounting(showcase.accounting.game_agents, showcase.accounting.judges, showcase.accounting.total);
}

export function scenarioCostBreakdown(scenario: EvalScenario, pricing: EvalCost): CostBreakdown {
  const agent = mergeAccounting(scenario.turns.flatMap((turn) => turn.traces.map((trace) => ({ usage: trace, cost: trace.cost }))));
  const judge = mergeAccounting(scenario.judge ? [{ usage: scenario.judge, cost: scenario.judge.cost }] : []);
  return fromAccounting(agent, judge, withFallbackRange(mergeAccounting([agent, judge]), pricing));
}

function fromAccounting(agent: EvalAccounting, judge: EvalAccounting, total: EvalAccounting): CostBreakdown {
  return {
    agentTokens: agent.usage.total_tokens,
    judgeTokens: judge.usage.total_tokens,
    totalTokens: total.usage.total_tokens,
    inputTokens: total.usage.input_tokens ?? 0,
    cachedInputTokens: total.usage.cached_input_tokens ?? 0,
    outputTokens: total.usage.output_tokens ?? 0,
    exactCost: total.cost.kind === "exact" ? total.cost.total_usd ?? null : null,
    minimumCost: total.cost.minimum_usd ?? null,
    maximumCost: total.cost.maximum_usd ?? null,
    agentCost: agent.cost,
    judgeCost: judge.cost,
    pricingSource: total.cost.pricing_source,
    pricingAsOf: total.cost.pricing_as_of,
  };
}

function mergeAccounting(entries: { usage: UsageLike; cost?: EvalCost | null }[]): EvalAccounting {
  const usage = entries.reduce<EvalUsage>((sum, entry) => ({
    input_tokens: (sum.input_tokens ?? 0) + (entry.usage.input_tokens ?? 0),
    cached_input_tokens: (sum.cached_input_tokens ?? 0) + (entry.usage.cached_input_tokens ?? 0),
    cache_write_tokens: (sum.cache_write_tokens ?? 0) + (entry.usage.cache_write_tokens ?? 0),
    output_tokens: (sum.output_tokens ?? 0) + (entry.usage.output_tokens ?? 0),
    reasoning_tokens: (sum.reasoning_tokens ?? 0) + (entry.usage.reasoning_tokens ?? 0),
    total_tokens: sum.total_tokens + (entry.usage.total_tokens ?? 0),
  }), { total_tokens: 0 });
  const costs = entries.map((entry) => entry.cost).filter((cost): cost is EvalCost => Boolean(cost));
  const source = costs[0]?.pricing_source ?? "https://developers.openai.com/api/docs/models/gpt-5.6-luna";
  const asOf = costs[0]?.pricing_as_of ?? "2026-08-21";
  if (costs.length === entries.length && costs.every((cost) => cost.kind === "exact")) {
    return { usage, cost: { kind: "exact", total_usd: costs.reduce((sum, cost) => sum + (cost.total_usd ?? 0), 0), pricing_source: source, pricing_as_of: asOf } };
  }
  return { usage, cost: { kind: "unavailable", pricing_source: source, pricing_as_of: asOf } };
}

function withFallbackRange(accounting: EvalAccounting, pricing: EvalCost): EvalAccounting {
  if (accounting.cost.kind !== "unavailable") return accounting;
  const inputRate = pricing.input_rate_per_million;
  const outputRate = pricing.output_rate_per_million;
  if (inputRate == null || outputRate == null) return accounting;
  return {
    usage: accounting.usage,
    cost: {
      ...pricing,
      kind: "range",
      total_usd: null,
      minimum_usd: accounting.usage.total_tokens / 1_000_000 * inputRate,
      maximum_usd: accounting.usage.total_tokens / 1_000_000 * outputRate,
    },
  };
}
