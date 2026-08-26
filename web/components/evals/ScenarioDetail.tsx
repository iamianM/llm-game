import styles from "../../app/evals/evals.module.css";
import type { ReactNode } from "react";
import { evalCheckExplanation } from "../../lib/eval-checks";
import { scenarioSummary } from "../../lib/eval-result";
import {
  CATEGORY_LABELS,
  type EvalGoldenCall,
  type EvalScenario,
  type EvalStatus,
  type EvalStory,
  type EvalTrace,
  type EvalTurn,
} from "../../lib/eval-showcase";

export function ScenarioDetail({ scenario }: { scenario: EvalScenario }) {
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
      <div className={styles.view}><ResultsView scenario={scenario} /></div>
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
        <p className={styles.definition}>Combines the deterministic turn checks with the one full-scenario judge verdict.</p>
      </div>
      <div className={styles.evaluationColumn}>
        <p className={styles.sourceLabel}>LLM call · thread judge</p>
        {scenario.judge ? <Status status={scenario.judge.result} /> : <strong>Not run</strong>}
        {scenario.judge && <CallMetrics call={scenario.judge} />}
        {scenario.judge ? (
          <details className={styles.inlineEvaluationDetails}>
            <summary>{scenario.judge.result === "pass" ? "Why it passed" : scenario.judge.result === "fail" ? "Why it failed" : "Why it needs review"}</summary>
            <p>{scenario.judge.reason}</p>
            {scenario.judge.criterion_findings.length > 0 && (
              <ol className={styles.judgeFindings}>
                {scenario.judge.criterion_findings.map((finding) => (
                  <li key={finding.id}>
                    <div className={styles.checkHeading}>
                      <strong>{sentence(finding.reason)}</strong>
                      <Status status={finding.result} />
                    </div>
                    {finding.evidence && <blockquote>{finding.evidence}</blockquote>}
                  </li>
                ))}
              </ol>
            )}
            <ReasoningSummary summaries={scenario.judge.reasoning_summaries} />
            {scenario.judge.evidence && <div><p className={styles.evidenceLabel}>Evidence cited by the judge</p><blockquote className={styles.evidenceQuote}>{scenario.judge.evidence}</blockquote></div>}
            {scenario.judge.criteria.length > 0 && <details className={styles.inlineEvaluationDetails}>
              <summary>What the judge reviewed</summary>
              <p>The judge receives the complete scenario: actions, engine records, reviewed targets, ordered model outputs, deterministic results, and this rubric.</p>
              <ol>{scenario.judge.criteria.map((criterion) => <li key={criterion}>{criterion}</li>)}</ol>
            </details>}
          </details>
        ) : <p>No thread evaluation was recorded.</p>}
      </div>
    </section>
  );
}

function TurnResult({ turn, index }: { turn: EvalTurn; index: number }) {
  const checks = turn.checks.filter((check) => check.id !== "exactly_one_exit");
  const passing = checks.filter((check) => check.result === "pass").length;
  const hasAgentCalls = turn.golden.calls.length > 0 || turn.traces.length > 0;
  return (
    <section className={styles.turnResult}>
      <div className={styles.turnHeader}><h3>{turnTitle(turn.action, index)}</h3><Status status={turn.status} /></div>
      {selectedIntent(turn.action) && <p className={styles.turnIntent}><span>Selected intent</span>{humanize(selectedIntent(turn.action)!)}</p>}
      {(turn.story.engine_result || turn.story.relationship_changes.length > 0 || turn.story.engine_details?.length || turn.story.events.length > 0) && (
        <section className={styles.engineResult}>
          <p className={styles.sourceLabel}>Engine result · deterministic</p>
          {turn.story.engine_result && <p>{turn.story.engine_result}</p>}
          {turn.story.engine_details?.length ? <dl className={styles.engineDetails}>{turn.story.engine_details.map((detail) => <div key={`${detail.label}-${detail.value}`}><dt>{detail.label}</dt><dd>{detail.value}</dd></div>)}</dl> : null}
          {turn.story.relationship_changes.length > 0 && <ul>{turn.story.relationship_changes.map((change) => <li key={change}>{change}</li>)}</ul>}
          {turn.story.events.length > 0 && <ResultList label="Resolved events" values={turn.story.events} />}
        </section>
      )}
      {hasAgentCalls && <CallComparison
        actualCalls={turn.traces.map((trace) => ({ ...trace, output: trace.output, output_type: trace.output_type ?? "Output" }))}
        referenceCalls={turn.golden.calls}
        story={turn.story}
      />}
      <details className={styles.turnEvaluation} open={turn.status !== "pass"}>
        <summary><span>Deterministic engine &amp; schema checks</span><strong>{passing}/{checks.length} passed</strong></summary>
        <p className={styles.checkIntro}>These checks inspect structured state and model contracts. The thread judge grades meaning and writing quality.</p>
        <ul className={styles.checkList}>{checks.map((check) => (
          <li className={check.result === "fail" ? styles.checkFail : check.result === "cannot_determine" ? styles.checkReview : ""} key={check.id}>
            <div className={styles.checkHeading}><strong>{sentence(check.reason)}</strong><Status status={check.result} /></div>
            <details className={styles.checkHelp}><summary>What this proves</summary><p>{evalCheckExplanation(check.id)}</p></details>
            {check.evidence && <blockquote>{check.evidence}</blockquote>}
          </li>
        ))}</ul>
      </details>
    </section>
  );
}

function AppliedGameResult({ story }: { story: EvalStory }) {
  const savedMemoryCount = story.memories.filter((value) => !value.startsWith("Summary:")).length;
  const hasResult = Boolean(story.choices.length || savedMemoryCount || story.resort_changes);
  if (!hasResult) return null;
  return (
    <section className={styles.appliedResult}>
      {story.choices.length > 0 && <div className={styles.appliedChoices}><strong>Choices used by the game</strong><ol>{story.choices.map((choice, index) => <li key={`${choice.label}-${index}`}><span>{choice.label}</span><small>{choice.category} · {choice.risk} risk</small></li>)}</ol></div>}
      {savedMemoryCount > 0 && <p className={styles.commitNote}>{savedMemoryCount} {savedMemoryCount === 1 ? "memory" : "memories"} stored in game state.</p>}
      {story.resort_changes && <ResultList label="Resort changes applied" values={[story.resort_changes]} />}
    </section>
  );
}

function ResultList({ label, values }: { label: string; values: string[] }) {
  return <div className={styles.resultList}><strong>{label}</strong><ul>{values.map((value) => <li key={value}>{value}</li>)}</ul></div>;
}

type DisplayCall = Pick<EvalGoldenCall, "agent" | "output_type"> & Partial<EvalTrace> & {
  output?: unknown;
  criteria?: string[];
};

function CallComparison({ actualCalls, referenceCalls, story }: { actualCalls: DisplayCall[]; referenceCalls: DisplayCall[]; story: EvalStory }) {
  const rowCount = Math.max(actualCalls.length, referenceCalls.length);
  return (
    <div className={styles.callReview}>
      <ol className={styles.callReviewList}>
        {Array.from({ length: rowCount }, (_, index) => (
          <li className={styles.callReviewItem} key={index}>
            <AgentResult actual={actualCalls[index]} index={index} reference={referenceCalls[index]} />
          </li>
        ))}
      </ol>
      {hasAppliedGameResult(story) && <AppliedGameResult story={story} />}
    </div>
  );
}

function AgentResult({ actual, index, reference }: { actual?: DisplayCall; index: number; reference?: DisplayCall }) {
  const agent = actual?.agent ?? reference?.agent ?? "unknown";
  const sameAgent = !actual || !reference || actual.agent === reference.agent;
  const name = sameAgent ? agentLabel(agent) : `${agentLabel(reference.agent)} / ${agentLabel(actual.agent)}`;
  const outputType = actual?.output_type ?? reference?.output_type ?? "Output";
  return (
    <div className={styles.agentCall} data-testid="call-comparison">
      <header className={styles.agentCallHeader}>
        <span>{index + 1}</span>
        <div><strong>{name}</strong><small>{agentRole(agent)}</small></div>
        <em>{outputType}{actual ? ` · attempt ${actual.attempt ?? 1}` : ""}</em>
      </header>
      {actual && <CallMetrics call={actual} />}
      <PairedTraceOutput actual={actual} agent={agent} reference={reference} />
      {actual && <ReasoningSummary summaries={actual.reasoning_summaries} />}
    </div>
  );
}

function PairedTraceOutput({ actual, agent, reference }: { actual?: DisplayCall; agent: string; reference?: DisplayCall }) {
  const expectedOutput = reference && isRecord(reference.output) ? reference.output : null;
  const actualOutput = actual && isRecord(actual.output) ? actual.output : null;
  if (!expectedOutput && reference?.criteria?.length) {
    return <CriteriaTraceOutput actual={actual} criteria={reference.criteria} />;
  }
  if (agent === "heartbreaker_voice" && (expectedOutput || actualOutput)) {
    return <ComparisonFields fields={[
      { key: "player", label: "Player line", reference: textValue(expectedOutput?.player_dialogue), actual: textValue(actualOutput?.player_dialogue) },
      { key: "npc", label: "NPC line", reference: textValue(expectedOutput?.npc_dialogue), actual: textValue(actualOutput?.npc_dialogue) },
      { key: "tone", label: "Tone", reference: toneValue(expectedOutput), actual: toneValue(actualOutput) },
    ]} />;
  }
  if (agent === "contextual_options" && (expectedOutput || actualOutput)) {
    return <ComparisonFields fields={[{ key: "choices", label: "Choices", reference: <ChoiceOutput output={expectedOutput} />, actual: <ChoiceOutput output={actualOutput} /> }]} />;
  }
  if (agent === "conversation_curator" && (expectedOutput || actualOutput)) {
    return <ComparisonFields fields={[
      { key: "recap", label: "Conversation recap", reference: textValue(expectedOutput?.summary), actual: textValue(actualOutput?.summary) },
      { key: "memories", label: "Stored memories", reference: <MemoryOutput output={expectedOutput} />, actual: <MemoryOutput output={actualOutput} /> },
    ]} />;
  }
  if (agent === "event_narrator" && (expectedOutput || actualOutput)) {
    return <ComparisonFields fields={[{ key: "narration", label: "Narration", reference: textValue(expectedOutput?.prose), actual: textValue(actualOutput?.prose) }]} />;
  }
  if (agent === "background_dialogue" && (expectedOutput || actualOutput)) {
    return <ComparisonFields fields={[
      { key: "speaker-a", label: "Speaker A", reference: textValue(expectedOutput?.speaker_a_line), actual: textValue(actualOutput?.speaker_a_line) },
      { key: "speaker-b", label: "Speaker B", reference: textValue(expectedOutput?.speaker_b_line), actual: textValue(actualOutput?.speaker_b_line) },
    ]} />;
  }
  return <ComparisonFields fields={[{
    key: "output",
    label: "Structured output",
    reference: reference ? <TraceOutput agent={reference.agent} output={reference.output} /> : <MissingValue>Not expected</MissingValue>,
    actual: actual ? <TraceOutput agent={actual.agent} output={actual.output} /> : <MissingValue>Not recorded</MissingValue>,
  }]} />;
}

function CriteriaTraceOutput({ actual, criteria }: { actual?: DisplayCall; criteria: string[] }) {
  return (
    <div className={styles.criteriaComparison} data-testid="criteria-comparison">
      <section className={styles.criteriaTarget}>
        <strong>Reviewed criteria</strong>
        <ol>{criteria.map((criterion) => <li key={criterion}>{criterion}</li>)}</ol>
      </section>
      <section className={styles.contextualActual}>
        <strong>Actual output from this thread</strong>
        {actual ? <TraceOutput agent={actual.agent} output={actual.output} /> : <MissingValue>Not recorded</MissingValue>}
      </section>
    </div>
  );
}

type ComparisonField = { key: string; label: string; reference: ReactNode; actual: ReactNode };

function ComparisonFields({ fields }: { fields: ComparisonField[] }) {
  return (
    <div className={styles.comparisonTable}>
      <div className={styles.comparisonTableHeader}><span /><strong>Reviewed target</strong><strong>Actual output</strong></div>
      {fields.map((field) => (
        <section className={styles.comparisonField} data-field={field.key} data-testid="output-comparison-field" key={field.key}>
          <strong>{field.label}</strong>
          <div className={styles.comparisonValue} data-call-source="reference"><span className={styles.mobileValueLabel}>Reviewed target</span>{field.reference}</div>
          <div className={styles.comparisonValue} data-call-source="actual"><span className={styles.mobileValueLabel}>Actual output</span>{field.actual}</div>
        </section>
      ))}
    </div>
  );
}

function ChoiceOutput({ output }: { output: Record<string, unknown> | null }) {
  const options = Array.isArray(output?.options) ? output.options : [];
  if (options.length === 0) return <MissingValue>None recorded</MissingValue>;
  return <ul className={styles.choiceList}>{options.map((raw, index) => {
    const option = isRecord(raw) ? raw : {};
    return <li key={`${String(option.label)}-${index}`}>{String(option.label ?? "Option")}<small>{String(option.category ?? "uncategorized")} · {String(option.risk ?? "unknown")} risk</small></li>;
  })}</ul>;
}

function MemoryOutput({ output }: { output: Record<string, unknown> | null }) {
  const memories = Array.isArray(output?.memories) ? output.memories : [];
  if (memories.length === 0) return <MissingValue>None recorded</MissingValue>;
  return <ul className={styles.memoryList}>{memories.map((raw, index) => {
    const memory = isRecord(raw) ? raw : {};
    const holder = String(memory.holder_id ?? "holder");
    const subject = String(memory.subject_id ?? "subject");
    return <li key={`${holder}-${index}`}><strong>{memoryRelationship(holder, subject)}</strong><span>{String(memory.content ?? "")}</span><small>{memory.durable === false ? "Short-term" : "Durable"}{typeof memory.emotional_weight === "number" ? ` · weight ${memory.emotional_weight}/10` : ""}</small></li>;
  })}</ul>;
}

function MissingValue({ children }: { children: ReactNode }) {
  return <p className={styles.missingValue}>{children}</p>;
}

function textValue(value: unknown) {
  return value ? <p className={styles.comparisonText}>{String(value)}</p> : <MissingValue>Not recorded</MissingValue>;
}

function toneValue(output: Record<string, unknown> | null) {
  if (!output) return <MissingValue>Not recorded</MissingValue>;
  const tone = String(output.npc_tone ?? "not recorded");
  const mood = String(output.npc_mood_after ?? "not recorded");
  return <p className={styles.comparisonText}>{tone} · {mood} mood</p>;
}

function hasAppliedGameResult(story: EvalStory) {
  return Boolean(story.choices.length || story.memories.some((value) => !value.startsWith("Summary:")) || story.resort_changes);
}

type UsageCall = {
  model?: string | null;
  reasoning_effort?: string | null;
  latency_ms?: number | null;
  input_tokens?: number | null;
  cached_input_tokens?: number | null;
  cache_write_tokens?: number | null;
  output_tokens?: number | null;
  reasoning_tokens?: number | null;
  total_tokens?: number | null;
  cost?: EvalTrace["cost"];
  attempt?: number;
};

function CallMetrics({ call }: { call: UsageCall }) {
  return (
    <div className={styles.callEvidence}>
      <div className={styles.callModel}>
        <span>Model</span>
        <strong>{call.model ?? "Not recorded"}</strong>
        <small>{call.reasoning_effort ? `${sentence(call.reasoning_effort)} reasoning` : "Reasoning effort not recorded"}</small>
      </div>
      <dl className={styles.callMetrics}>
        <div><dt>Latency</dt><dd>{call.latency_ms == null ? "—" : `${(call.latency_ms / 1000).toFixed(2)} s`}</dd></div>
        <div><dt>Tokens</dt><dd>{call.total_tokens?.toLocaleString() ?? "—"}</dd></div>
        <div><dt>Cost</dt><dd>{call.cost?.total_usd == null ? "—" : preciseMoney(call.cost.total_usd)}</dd></div>
      </dl>
      <details className={styles.tokenDetails}>
        <summary>Token breakdown</summary>
        <dl>
          <div><dt>Input</dt><dd>{tokenValue(call.input_tokens)}</dd></div>
          <div><dt>Cached input</dt><dd>{tokenValue(call.cached_input_tokens)}</dd></div>
          <div><dt>Cache write</dt><dd>{tokenValue(call.cache_write_tokens)}</dd></div>
          <div><dt>Output</dt><dd>{tokenValue(call.output_tokens)}</dd></div>
          <div><dt>Reasoning</dt><dd>{tokenValue(call.reasoning_tokens)}</dd></div>
          {call.attempt != null && <div><dt>Attempt</dt><dd>{call.attempt}</dd></div>}
        </dl>
      </details>
    </div>
  );
}

function ReasoningSummary({ summaries }: { summaries?: string[] }) {
  if (summaries?.length) {
    return <details className={styles.reasoningSummary}><summary>Reasoning summary · saved</summary>{summaries.map((summary) => <p key={summary}>{summary}</p>)}</details>;
  }
  return <details className={styles.reasoningUnavailable}><summary>Reasoning summary · not returned</summary><p>The call requested a summary, but the model did not return one. Hidden chain-of-thought is not stored or displayed.</p></details>;
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
    return <div>{output.summary ? <div className={styles.curatorSummary}><strong>Conversation recap</strong><p>{String(output.summary)}</p></div> : null}<ul className={styles.memoryList}>{memories.map((raw, index) => {
      const memory = isRecord(raw) ? raw : {};
      const holder = String(memory.holder_id ?? "holder");
      const subject = String(memory.subject_id ?? "subject");
      return <li key={`${holder}-${index}`}><strong>{memoryRelationship(holder, subject)}</strong><span>{String(memory.content ?? "")}</span><small>{memory.durable === false ? "Short-term" : "Durable"}{typeof memory.emotional_weight === "number" ? ` · weight ${memory.emotional_weight}/10` : ""}</small></li>;
    })}</ul></div>;
  }
  if (agent === "event_narrator" && isRecord(output)) return <blockquote className={styles.narration}>{String(output.prose ?? "")}</blockquote>;
  if (agent === "background_dialogue" && isRecord(output)) return <div className={styles.dialogue}><p className={styles.line}><strong>Speaker A</strong><span>{String(output.speaker_a_line ?? "")}</span></p><p className={styles.line}><strong>Speaker B</strong><span>{String(output.speaker_b_line ?? "")}</span></p></div>;
  return <pre className={styles.structuredOutput}>{JSON.stringify(output, null, 2)}</pre>;
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
function selectedIntent(action: string) { return action.match(/intent ([^|]+)/)?.[1]?.trim() ?? null; }
function humanize(value: string) { return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase()); }
function sentence(value: string) { return value.charAt(0).toUpperCase() + value.slice(1); }
function turnLabel(count: number) { return `${count} ${count === 1 ? "turn" : "turns"}`; }
function tokenValue(value?: number | null) { return value == null ? "—" : value.toLocaleString(); }
function preciseMoney(value: number) {
  if (value === 0) return "$0";
  if (value < 0.000001) return "<$0.000001";
  return `$${value.toFixed(6)}`;
}
function agentLabel(agent: string) {
  const labels: Record<string, string> = { heartbreaker_voice: "Heartbreaker Voice", contextual_options: "Contextual Options", conversation_curator: "Conversation Curator", event_narrator: "Event Narrator", resort_orchestrator: "Resort Orchestrator", background_dialogue: "Background Dialogue" };
  return labels[agent] ?? humanize(agent);
}
function agentRole(agent: string) {
  const roles: Record<string, string> = { heartbreaker_voice: "writes the player and NPC exchange", contextual_options: "writes the next response choices", conversation_curator: "records durable memories", event_narrator: "narrates resolved game events", resort_orchestrator: "directs off-screen resort activity", background_dialogue: "writes an NPC-to-NPC exchange" };
  return roles[agent] ?? "structured model output";
}
function memoryRelationship(holder: string, subject: string) {
  const holderName = holder === "player" ? "Player" : humanize(holder);
  const subjectName = subject === "player" ? "the player" : humanize(subject);
  return `${holderName} remembers ${subjectName}`;
}
function isRecord(value: unknown): value is Record<string, unknown> { return Boolean(value) && typeof value === "object" && !Array.isArray(value); }
