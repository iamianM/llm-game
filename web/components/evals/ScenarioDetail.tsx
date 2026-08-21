import styles from "../../app/evals/evals.module.css";
import { scenarioCostBreakdown } from "../../lib/eval-cost";
import { scenarioSummary } from "../../lib/eval-result";
import { CATEGORY_LABELS, type EvalGoldenCall, type EvalScenario, type EvalShowcase, type EvalStatus, type EvalTurn } from "../../lib/eval-showcase";
import { ScenarioTabs } from "./ScenarioTabs";

export type ScenarioView = "results" | "technical";

export function ScenarioDetail({ scenario, showcase, view }: { scenario: EvalScenario; showcase: EvalShowcase; view: ScenarioView }) {
  return (
    <article>
      <header className={styles.scenarioHeader}>
        <div className={styles.scenarioMeta}>
          <Status status={scenario.status} />
          <span>{CATEGORY_LABELS[scenario.category]}</span>
          <span>{turnLabel(scenario.turns.length)}</span>
        </div>
        <h2>{scenario.title}</h2>
        <p className={styles.question}>{scenario.question}</p>
      </header>
      <ScenarioTabs scenarioId={scenario.id} view={view} />
      <div className={styles.view}>
        {view === "results" && <ResultsView scenario={scenario} />}
        {view === "technical" && <TechnicalView scenario={scenario} showcase={showcase} />}
      </div>
    </article>
  );
}

function ResultsView({ scenario }: { scenario: EvalScenario }) {
  const firstTurns = scenario.turns.slice(0, 4);
  const remainingTurns = scenario.turns.slice(4);
  return (
    <>
      <ScenarioEvaluation scenario={scenario} />
      <h3 className={styles.viewHeading}>Turn results</h3>
      {firstTurns.map((turn, index) => <TurnResult index={index} key={turn.id} turn={turn} />)}
      {remainingTurns.length > 0 && (
        <details className={styles.moreTurns}>
          <summary>Show remaining {remainingTurns.length} turns</summary>
          {remainingTurns.map((turn, index) => <TurnResult index={index + 4} key={turn.id} turn={turn} />)}
        </details>
      )}
    </>
  );
}

function ScenarioEvaluation({ scenario }: { scenario: EvalScenario }) {
  return (
    <section className={styles.scenarioEvaluation}>
      <div className={styles.evaluationColumn}>
        <p className={styles.sourceLabel}>Overall result</p>
        <Status status={scenario.status} />
        <p>{scenarioSummary(scenario)}</p>
      </div>
      <div className={styles.evaluationColumn}>
        <p className={styles.sourceLabel}>Thread judge · full scenario{scenario.judge?.model ? ` · ${scenario.judge.model}` : ""}</p>
        {scenario.judge ? <Status status={scenario.judge.result} /> : <strong>Not run</strong>}
        <p>{scenario.judge?.reason ?? "No thread evaluation was recorded."}</p>
        {scenario.judge?.evidence && <div><p className={styles.evidenceLabel}>Evidence cited by the judge</p><blockquote className={styles.evidenceQuote}>{scenario.judge.evidence}</blockquote></div>}
        {scenario.judge?.criteria.length ? (
          <details className={styles.inlineEvaluationDetails}>
            <summary>Evaluation criteria</summary>
            <ol>{scenario.judge.criteria.map((criterion) => <li key={criterion}>{criterion}</li>)}</ol>
          </details>
        ) : null}
      </div>
    </section>
  );
}

function TurnResult({ turn, index }: { turn: EvalTurn; index: number }) {
  const checks = turn.checks.filter((check) => check.id !== "exactly_one_exit");
  const passing = checks.filter((check) => check.result === "pass").length;
  return (
    <section className={styles.turnResult}>
      <div className={styles.turnHeader}>
        <h3>{turnTitle(turn.action, index)}</h3>
        <Status status={turn.status} />
      </div>
      <div className={styles.comparisonGrid}>
        <section className={styles.comparisonPanel}>
          <p className={styles.sourceLabel}>Reviewed golden · expected calls</p>
          <AgentResultSequence calls={turn.golden.calls} empty="No model call expected." />
          <details className={styles.goldenCriteria}>
            <summary>Comparison criteria</summary>
            <p>{turn.golden.criteria}</p>
          </details>
        </section>
        <section className={styles.comparisonPanel}>
          <p className={styles.sourceLabel}>Actual calls · in order</p>
          <AgentCallSequence turn={turn} />
        </section>
      </div>
      <details className={styles.turnEvaluation} open={turn.status !== "pass"}>
        <summary><span>Engine &amp; schema checks</span><strong>{passing}/{checks.length} passed</strong></summary>
        <ul className={styles.checkList}>{checks.map((check) => (
          <li className={check.result === "fail" ? styles.checkFail : check.result === "cannot_determine" ? styles.checkReview : ""} key={check.id}>
            <div className={styles.checkHeading}><strong>{sentence(check.reason)}</strong><Status status={check.result} /></div>
            {check.evidence && <blockquote>{check.evidence}</blockquote>}
          </li>
        ))}</ul>
      </details>
    </section>
  );
}

function AgentCallSequence({ turn }: { turn: EvalTurn }) {
  const calls = turn.traces.map((trace) => ({
    agent: trace.agent,
    output_type: trace.output_type ?? "Output",
    output: trace.output,
    reasoning_summaries: trace.reasoning_summaries,
  }));
  return <AgentResultSequence calls={calls} empty="Engine-only turn. No model was called." showReasoning />;
}

type DisplayCall = Pick<EvalGoldenCall, "agent" | "output_type"> & {
  output: unknown;
  reasoning_summaries?: string[];
};

function AgentResultSequence({ calls, empty, showReasoning = false }: { calls: DisplayCall[]; empty: string; showReasoning?: boolean }) {
  if (calls.length === 0) return <p className={styles.empty}>{empty}</p>;
  return <ol className={styles.agentSequence}>{calls.map((call, index) => (
    <li className={styles.agentCall} key={`${call.agent}-${index}`}>
      <div className={styles.agentCallHeader}>
        <span>{index + 1}</span>
        <div><strong>{agentLabel(call.agent)}</strong><small>{agentRole(call.agent)}</small></div>
        <em>{call.output_type}</em>
      </div>
      <TraceOutput agent={call.agent} output={call.output} />
      {showReasoning && (call.reasoning_summaries?.length ? (
        <details className={styles.reasoningSummary}><summary>Model reasoning summary</summary>{call.reasoning_summaries.map((summary) => <p key={summary}>{summary}</p>)}</details>
      ) : <p className={styles.reasoningUnavailable}>No model reasoning summary was returned for this call.</p>)}
    </li>
  ))}</ol>;
}

function TraceOutput({ agent, output }: { agent: string; output: unknown }) {
  if (!output) return <p className={styles.empty}>Structured output was not retained in this published run.</p>;
  if (agent === "heartbreaker_voice" && isRecord(output)) {
    return <div className={styles.dialogue}>
      <p className={styles.line}><strong>Player line</strong><span>{String(output.player_dialogue ?? "")}</span></p>
      <p className={`${styles.line} ${styles.npc}`}><strong>NPC line</strong><span>{String(output.npc_dialogue ?? "")}</span></p>
      <p className={styles.tone}>Tone: {String(output.npc_tone ?? "not recorded")} · mood: {String(output.npc_mood_after ?? "not recorded")}</p>
    </div>;
  }
  if (agent === "contextual_options" && isRecord(output)) {
    const options = Array.isArray(output.options) ? output.options : [];
    return <ul className={styles.choiceList}>{options.map((raw, index) => {
      const option = isRecord(raw) ? raw : {};
      return <li key={`${String(option.label)}-${index}`}>{String(option.label ?? "Option")} · {String(option.category ?? "uncategorized")} · {String(option.risk ?? "unknown")} risk</li>;
    })}</ul>;
  }
  if (agent === "conversation_curator" && isRecord(output)) {
    const memories = Array.isArray(output.memories) ? output.memories : [];
    return <div>{output.summary ? <p>{String(output.summary)}</p> : null}<ul className={styles.memoryList}>{memories.map((raw, index) => {
      const memory = isRecord(raw) ? raw : {};
      return <li key={`${String(memory.holder_id)}-${index}`}><strong>{String(memory.holder_id ?? "holder")}</strong> → {String(memory.subject_id ?? "subject")}: {String(memory.content ?? "")}</li>;
    })}</ul></div>;
  }
  if (agent === "event_narrator" && isRecord(output)) return <blockquote className={styles.narration}>{String(output.prose ?? "")}</blockquote>;
  if (agent === "background_dialogue" && isRecord(output)) return <div className={styles.dialogue}><p className={styles.line}><strong>Speaker A</strong><span>{String(output.speaker_a_line ?? "")}</span></p><p className={styles.line}><strong>Speaker B</strong><span>{String(output.speaker_b_line ?? "")}</span></p></div>;
  return <pre className={styles.structuredOutput}>{JSON.stringify(output, null, 2)}</pre>;
}

function TechnicalView({ scenario, showcase }: { scenario: EvalScenario; showcase: EvalShowcase }) {
  const cost = scenarioCostBreakdown(scenario, showcase.accounting.total.cost);
  const models = [...new Set([...scenario.turns.flatMap((turn) => turn.traces.map((trace) => trace.model)), ...(scenario.judge?.model ? [scenario.judge.model] : [])])];
  return (
    <>
      <h3 className={styles.viewHeading}>Run trace</h3>
      <div className={styles.technicalIntro}>
        <div><span>Mode</span><strong>{showcase.llm_mode === "real" ? "Real model" : "Mock"}</strong></div>
        <div><span>Model</span><strong>{models.join(", ") || "Not recorded"}</strong></div>
        <div><span>Game agents</span><strong>{cost.agentTokens.toLocaleString()} tokens</strong></div>
        <div><span>Thread judge</span><strong>{cost.judgeTokens.toLocaleString()} tokens</strong></div>
        <div><span>{cost.exactCost == null ? "Estimated cost" : "Cost"}</span><strong>{costLabel(cost)}</strong></div>
      </div>
      <p className={styles.technicalNote}>
        {cost.exactCost == null ? "This historical run retained total tokens but not the input/output split, so its cost is a range. New runs save the exact usage split and per-call estimate. " : "The run saved input, cached input, cache-write, output, and reasoning usage for each call. "}
        <a href={cost.pricingSource}>Price snapshot</a> · {cost.pricingAsOf}
      </p>
      {scenario.turns.map((turn, index) => (
        <section className={styles.technicalTurn} key={turn.id}>
          <h3>{turnTitle(turn.action, index)}</h3>
          {turn.traces.length > 0 ? (
            <div className={styles.traceScroller}>
              <table className={styles.traceTable}>
                <thead><tr><th>Agent call</th><th>Output</th><th>Model</th><th>Effort</th><th>Latency</th><th>Tokens</th><th>Cost</th></tr></thead>
                <tbody>{turn.traces.map((trace, traceIndex) => <tr key={`${trace.agent}-${traceIndex}`}><td>{agentLabel(trace.agent)}</td><td>{trace.output_type ?? "Not recorded"}</td><td>{trace.model}</td><td>{trace.reasoning_effort}</td><td>{trace.latency_ms ? `${trace.latency_ms.toLocaleString()} ms` : "—"}</td><td>{trace.total_tokens?.toLocaleString() ?? "—"}</td><td>{trace.cost?.total_usd != null ? money(trace.cost.total_usd) : "—"}</td></tr>)}</tbody>
              </table>
            </div>
          ) : <p className={styles.empty}>Engine-only turn. No model call.</p>}
        </section>
      ))}
    </>
  );
}

function Status({ status }: { status: EvalStatus }) {
  const extra = status === "fail" ? styles.statusFail : status === "cannot_determine" ? styles.statusReview : "";
  return <span className={`${styles.status} ${extra}`}><i className={styles.dot} />{statusLabel(status)}</span>;
}

function statusLabel(status: EvalStatus) {
  if (status === "cannot_determine") return "Needs human review";
  return status === "pass" ? "Passed" : "Failed";
}

function turnTitle(action: string, index: number) {
  const target = action.match(/target ([^|]+)/)?.[1]?.trim();
  if (target) return `${humanize(action.split(" | ")[0])} · ${humanize(target)}`;
  return index > 0 ? `Turn ${index + 1} · ${humanize(action.split(" | ")[0])}` : humanize(action.split(" | ")[0]);
}

function humanize(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function sentence(value: string) { return value.charAt(0).toUpperCase() + value.slice(1); }

function turnLabel(count: number) { return `${count} ${count === 1 ? "turn" : "turns"}`; }
function money(value: number) { return `$${value.toFixed(2)}`; }

function costLabel(cost: ReturnType<typeof scenarioCostBreakdown>) {
  if (cost.exactCost != null) return money(cost.exactCost);
  if (cost.minimumCost != null && cost.maximumCost != null) return `${money(cost.minimumCost)}–${money(cost.maximumCost)}`;
  return "Not available";
}

function agentLabel(agent: string) {
  const labels: Record<string, string> = {
    heartbreaker_voice: "Heartbreaker Voice",
    contextual_options: "Contextual Options",
    conversation_curator: "Conversation Curator",
    event_narrator: "Event Narrator",
    resort_orchestrator: "Resort Orchestrator",
    background_dialogue: "Background Dialogue",
  };
  return labels[agent] ?? humanize(agent);
}

function agentRole(agent: string) {
  const roles: Record<string, string> = {
    heartbreaker_voice: "writes the player and NPC exchange",
    contextual_options: "writes the next response choices",
    conversation_curator: "records durable memories",
    event_narrator: "narrates resolved game events",
    resort_orchestrator: "directs off-screen resort activity",
    background_dialogue: "writes an NPC-to-NPC exchange",
  };
  return roles[agent] ?? "structured model output";
}

function isRecord(value: unknown): value is Record<string, unknown> { return Boolean(value) && typeof value === "object" && !Array.isArray(value); }
