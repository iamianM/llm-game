# LLM Evaluation System

Paradise Hearts evaluates generated behavior through the production game path.
The eval runner does not maintain a second prompt harness or a simplified game
loop: every authored turn calls the same `run_turn` function used by the CLI and
FastAPI session loop.

## What the System Proves

The system separates three kinds of confidence:

1. **Deterministic checks** prove schemas, legal actions, engine invariants,
   required commits, menus, memories, resolved participants, and state effects.
2. **Live-agent runs** show how the configured production agents behave against
   the same authored scenarios.
3. **Judge-assisted review** evaluates qualities code cannot establish, such as
   voice fit, continuity, specificity, emotional readability, and faithfulness
   to a resolved event.

The judge is a review assistant, never the authority on mechanics. Its outcomes
are `pass`, `fail`, or `cannot_determine`, and they appear next to the raw
evidence that a human needs to agree or disagree.

## Production-Path Execution

Scenarios live in `evals/llm/scenarios/` as typed YAML. A scenario defines
canonical setup, a fixed seed, one or more legal player actions, authored golden
intent, deterministic checks, and optional judge criteria.

For each turn the runner:

1. builds or restores canonical engine state;
2. arranges only the explicit fixture state;
3. executes the action through `run_turn`;
4. validates structured engine and agent output;
5. writes the trace artifact before any judge is called; and
6. optionally asks the judge to compare authored intent with actual evidence.

Scenarios run independently and in parallel, up to eight workers by default.
Use `--max-workers 1` for sequential diagnosis.

## Current Coverage

The current suite contains **24 scenarios and 86 authored turns**:

- Opening and conversation: first chats across the launch cast, continuity and
  organic exit, wheel exit, and the Day 1 communal introduction.
- Social dynamics: background resort life, private-chat success and rejection,
  and interruption accept, defer, and ignore paths.
- Pairing and endings: opening ceremony, player and NPC proposals, proposal
  decline, Pairing Ceremony sent-home outcome, and final vote.
- Special events: Paradise Suite and the Flush of Hearts announcement.
- Challenges: baseline challenge narration plus Couples Quiz, Lie Detector,
  Pulse Race, Kiss Wed Pass, and Final Couples narration.

The scenario directory is the executable inventory. The complete authoring
schema and available deterministic checks live in
[`evals/llm/scenarios/FORMAT.md`](../../evals/llm/scenarios/FORMAT.md).

## Running the Pack

The deterministic mock run is part of `make qa`:

```bash
uv run python -m src.game.cli llm-eval \
  --out review-packet/llm-eval-mock
```

Run one focused scenario while developing:

```bash
uv run python -m src.game.cli llm-eval \
  --scenarios evals/llm/scenarios/conversation-continuity-exit.yaml \
  --out review-packet/llm-eval-continuity
```

Run the same production path with live agents and the optional judge:

```bash
uv run python -m src.game.cli llm-eval \
  --out review-packet/llm-eval-real \
  --real-llm \
  --judge
```

Live calls use the shared runtime configuration in
`src/game/agents/runtime.py`. The default model is `gpt-5.4-mini` with high
reasoning effort and detailed reasoning summaries; `LLM_GAME_MODEL` can
override the model for an intentional experiment.

## Recorded Evidence

Each live agent call records its agent name, model, reasoning effort, retry
attempt, prompt path, parsed output, validation failure when applicable, and
model-provided reasoning summary. The trace stores summaries, not hidden chain
of thought.

Each scenario also writes its production trace as soon as it finishes. A later
report-rendering or judge failure therefore cannot erase the game evidence.

## Review Packet

The generated `index.html` is the primary artifact. It shows:

- scenario goal and authored golden intent;
- mode, judge status, workers, turns, and pass/fail totals;
- deterministic check results;
- actual dialogue, narration, menus, memories, and engine results;
- agent traces and reasoning summaries; and
- judge criteria, findings, and prompts when enabled.

Reviewers can filter by status, search across scenarios and turns, sort results,
jump between scenario chips, and expand failing turns. Review in this order:

1. Confirm the mock pack is clean; this establishes fixture and harness health.
2. Filter the live packet to failures and `cannot_determine` results.
3. Read deterministic checks and actual output before the judge conclusion.
4. Read the reasoning summary to locate a prompt or context misunderstanding.
5. Inspect the stored judge prompt only when the judgment itself looks wrong.

## Failure-to-Regression Workflow

Classify a failure at the boundary that owns it:

- illegal state or wrong delta: engine or fixture;
- missing or malformed data: schema or agent commit;
- misleading context: context builder;
- valid but weak prose: the responsible agent prompt;
- weak or vague expectation: scenario golden or judge criterion;
- hard-to-review evidence: report renderer.

Fix the smallest responsible boundary, then convert the failure into a
deterministic check or focused golden scenario. Re-run that scenario, the full
mock pack, and any relevant live case. Never loosen an assertion merely to make
a packet green.

## Maintenance Rules

- Every player-facing beat that crosses an agent boundary ships with a scenario.
- Mechanical behavior must have deterministic tests before narrative evals.
- Prefer structural checks to judge checks whenever the claim is machine-testable.
- Goldens describe specific intent and an example of success; they do not demand
  exact wording.
- Update or delete a stale scenario in the same change that alters the game
  contract. Do not support old scenario shapes with compatibility code.
- A passing mock pack proves harness and contract health, not live prose quality.
- A passing judge is evidence for review, not proof that the game is fun.
