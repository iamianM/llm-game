import type { Metadata } from "next";
import Link from "next/link";
import { EvalHeader } from "../../components/evals/EvalHeader";
import { runCostBreakdown } from "../../lib/eval-cost";
import { evalRollout } from "../../lib/eval-rollout";
import {
  CATEGORY_LABELS,
  CATEGORY_ORDER,
  evalShowcase,
} from "../../lib/eval-showcase";
import styles from "./evals.module.css";

export const metadata: Metadata = {
  title: "AI Evaluation | Paradise Hearts",
  description: "Paradise Hearts AI evaluation results.",
};

export default function EvalsPage() {
  const showcase = evalShowcase;
  if (!showcase) return <Unavailable />;
  const total = showcase.scenarios.length;
  const allPassed = showcase.failed === 0 && showcase.cannot_determine === 0;
  const reviewScenario = showcase.scenarios.find((scenario) => scenario.status !== "pass");
  const models = [...new Set(showcase.scenarios.flatMap((scenario) => scenario.turns).flatMap((turn) => turn.traces).map((trace) => trace.model))];
  const cost = runCostBreakdown(showcase);
  const rollout = evalRollout?.scenarios[0] ?? null;

  return (
    <div className={styles.page} data-testid="eval-page">
      <EvalHeader />
      <main className={styles.main}>
        <section className={styles.overviewHeader}>
          <div>
            <p className={styles.eyebrow}>AI evaluation</p>
            <h1>Evaluation overview</h1>
          </div>
          <Link className={styles.cta} href={allPassed ? "/evals/scenarios/conversation-continuity-exit" : `/evals/scenarios/${reviewScenario?.id ?? "conversation-continuity-exit"}`}>
            {allPassed ? "View scenarios" : "View failures"} <span>→</span>
          </Link>
        </section>

        <section className={styles.resultSummary} aria-label="Evaluation result">
          <div className={`${styles.resultLine} ${!allPassed ? (showcase.failed > 0 ? styles.statusFail : styles.statusReview) : ""}`}>
            <i className={styles.dot} aria-hidden="true" />
            <strong>{showcase.passed} passed</strong>
          </div>
          <span>{showcase.failed} failed</span>
          <span>{showcase.cannot_determine} need review</span>
        </section>

        <section className={styles.statStrip} aria-label="Run totals">
          <div className={styles.stat}><strong>{total}</strong><span>scenarios</span></div>
          <div className={styles.stat}><strong>{showcase.turn_count}</strong><span>turns</span></div>
          <div className={styles.stat}><strong>{showcase.agent_call_count}</strong><span>agent calls</span></div>
          <div className={styles.stat}><strong>{cost.totalTokens.toLocaleString()}</strong><span>total tokens</span></div>
        </section>

        {rollout && <section className={styles.section}>
          <div className={styles.splitHeading}>
            <div><p className={styles.eyebrow}>Causal rollout</p><h2>{rollout.title}</h2></div>
            <Link className={styles.cta} href={`/evals/rollouts/${rollout.id}`}>View rollout <span>→</span></Link>
          </div>
          <div className={styles.rolloutSummary}>
            <div className={styles.resultLine}><i className={styles.dot} aria-hidden="true" /><strong>{rollout.status === "pass" ? "Passed" : rollout.status === "fail" ? "Failed" : "Needs review"}</strong></div>
            <span>{rollout.turns.length} actual turns carried forward</span>
          </div>
        </section>}

        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <h2>Coverage</h2>
          </div>
          <div className={styles.coverage}>
            {CATEGORY_ORDER.map((category) => {
              const count = showcase.scenarios.filter((scenario) => scenario.category === category).length;
              return <div className={styles.coverageItem} key={category}><strong>{count}</strong><span>{CATEGORY_LABELS[category]}</span></div>;
            })}
          </div>
        </section>

        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <h2>Run</h2>
          </div>
          <dl className={styles.detailsGrid}>
            <div><dt>Mode</dt><dd>{showcase.llm_mode === "real" ? "Real model" : "Mock"}</dd></div>
            <div><dt>Models</dt><dd>{models.join(", ") || "Not recorded"}</dd></div>
            <div><dt>Published</dt><dd>{showcase.provenance.published_at ?? "Not recorded"}</dd></div>
          </dl>
        </section>

        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <h2>Usage and cost</h2>
          </div>
          <div className={styles.usageGrid}>
            <div><span>Game agents</span><strong>{costValue(cost.agentCost)}</strong><small>{cost.agentTokens.toLocaleString()} tokens</small></div>
            <div><span>Scenario judges</span><strong>{costValue(cost.judgeCost)}</strong><small>{cost.judgeTokens.toLocaleString()} tokens</small></div>
            <div><span>Total usage</span><strong>{cost.totalTokens.toLocaleString()}</strong><small>tokens</small></div>
            <div><span>{cost.exactCost == null ? "Estimated cost" : "Total cost"}</span><strong>{cost.exactCost == null ? range(cost.minimumCost, cost.maximumCost) : money(cost.exactCost)}</strong><small>USD</small></div>
          </div>
          <p className={styles.costNote}>
            {cost.exactCost == null ? "Estimated from the saved token categories and price snapshot. " : "Calculated from the usage and price snapshot saved with the run. "}
            <a href={cost.pricingSource}>GPT-5.6 Luna pricing</a> · {cost.pricingAsOf}
          </p>
        </section>
      </main>
    </div>
  );
}

function money(value: number) { return `$${value.toFixed(2)}`; }
function range(minimum: number | null, maximum: number | null) {
  if (minimum == null || maximum == null) return "Not available";
  if (minimum === maximum) return money(minimum);
  return `${money(minimum)} to ${money(maximum)}`;
}
function costValue(cost: { kind: string; total_usd?: number | null; minimum_usd?: number | null; maximum_usd?: number | null }) { return cost.kind === "exact" && cost.total_usd != null ? money(cost.total_usd) : range(cost.minimum_usd ?? null, cost.maximum_usd ?? null); }

function Unavailable() {
  return <div className={styles.page} data-testid="eval-page"><EvalHeader /><main className={styles.unavailable}><div><h1>Evaluation data unavailable</h1><p>The reviewed report could not be loaded.</p></div></main></div>;
}
