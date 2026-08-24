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
3. **Thread-assisted review** asks one judge to read the complete scenario and
   evaluate qualities code cannot establish, such as voice consistency,
   continuity, specificity, emotional readability, and faithfulness across the
   full sequence.

The judge is a review assistant, never the authority on mechanics. Its outcomes
are `pass`, `fail`, or `cannot_determine`, and they appear next to the raw
evidence that a human needs to agree or disagree.

## Production-Path Execution

Scenarios live in `evals/llm/scenarios/` as typed YAML. A scenario defines
canonical setup, a fixed seed, one or more legal player actions, an authored
semantic target, deterministic turn checks, and one holistic thread-check rubric.

For each turn the runner:

1. builds or restores canonical engine state;
2. arranges only the explicit fixture state;
3. executes the action through `run_turn`;
4. validates structured engine and agent output;
5. writes the complete trace artifact; and
6. optionally makes one judge call over every authored turn, semantic target,
   engine record, and ordered agent output in the scenario.

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

Live calls use role profiles in `src/game/agents/runtime.py`. Shipped defaults
use `gpt-5.6-luna`: voice and multi-object resort orchestration at `medium`,
creative narration and other structured utility work at `low`, and the thread
judge at `medium` reasoning. The medium voice
profile is an intentional adherence tradeoff: the launch-cast eval was stronger
at the cost of roughly 1.5 seconds average latency per voice call. `LLM_GAME_MODEL`
overrides the whole pack; `LLM_GAME_<ROLE>_MODEL` and
`LLM_GAME_<ROLE>_REASONING_EFFORT` isolate a voice, creative, utility,
orchestrator, or judge experiment without changing prompts or game context.

### Hosted showcase

The Vercel app exposes `/evals` as a portfolio-facing view of one curated real
run. `/evals` gives the result and coverage. `/evals/scenarios/<id>` shows the
authored expectation, actual output, and evaluation reasons together, with a
separate run trace for call metadata. Both pages import the reviewed
`web/data/evals/latest.json` artifact at build time. Each turn compares an
ordered reviewed golden against the actual ordered agent results using the same
agent, output-type, and output payload shape. The eval command does not
deploy a run. A reviewer promotes `showcase.json` into that tracked path, pushes
the Git commit, and the Vercel Git integration builds the committed snapshot.
The deployed page does not fetch GitHub data at runtime. General
`review-packet*` directories stay out of deployment, so local playtests are not
published.

Each eval run writes `showcase.json` next to `index.html`. The showcase builder
copies only approved display fields from `GoldenEvalRun`. It excludes prompts,
model inputs, response IDs, hashes, state snapshots, hidden reasoning, and
path-bearing trace fields. It keeps safe structured agent outputs and
model-provided reasoning summaries. A publication test rejects known private
keys, local path patterns, and credential markers in the tracked artifact.
Review the visible prose before you copy a real-and-judged `showcase.json` to
`web/data/evals/latest.json`. New projections retain input, cached-input,
cache-write, output, reasoning, and total token counts. They also store a dated
price snapshot and per-call, game-agent, judge, and total cost estimates. The
hosted view reads those stored estimates. Set exact publication metadata during
review.

## Recorded Evidence

Each live agent call records its agent name, role-selected model, reasoning
effort, retry attempt, latency, token usage, prompt path and SHA-256, serialized
agent input, parsed output, validation failure when applicable, and
model-provided reasoning summary. The trace stores summaries, not hidden chain
of thought. The single thread judge call records the same review-critical model,
effort, latency, token, response, and summary provenance.

Each scenario also writes its production trace as soon as it finishes. A later
report-rendering or judge failure therefore cannot erase the game evidence.

## Review Packet

The generated `index.html` is the primary artifact. It shows:

- scenario goal, structured golden results, and comparison criteria;
- mode, judge status, workers, turns, pass/fail totals, agent calls, latency
  percentiles, and tokens;
- one whole-thread verdict, its rubric, and judge provenance before turn detail;
- collapsed deterministic engine and schema checks, with failures expanded;
- actual dialogue, narration, menus, memories, and engine results;
- agent traces and reasoning summaries; and
- judge criteria, findings, and prompts when enabled.

Reviewers can filter by status, search and sort the scenario rail, select one
complete thread at a time, and expand individual turns. Review in this order:

1. Confirm the mock pack is clean; this establishes fixture and harness health.
2. Filter the live packet to failures and `cannot_determine` results.
3. Read the complete thread and deterministic evidence before accepting a judge
   conclusion.
4. Use per-call inputs, prompt hashes, latency/tokens, and reasoning summaries to
   locate the responsible model, prompt, or runtime boundary.
5. Inspect the stored whole-thread judge payload when the judgment itself looks
   wrong.

## Failure-to-Regression Workflow

Classify a failure at the boundary that owns it:

- illegal state or wrong delta: engine or fixture;
- missing or malformed data: schema or agent commit;
- misleading context: context builder;
- valid but weak prose: the responsible agent prompt;
- weak or vague expectation: scenario golden or thread criterion;
- hard-to-review evidence: report renderer.

Fix the smallest responsible boundary, then convert the failure into a
deterministic check or focused golden scenario. Re-run that scenario, the full
mock pack, and any relevant live case. Never loosen an assertion merely to make
a packet green.

## Maintenance Rules

- Every player-facing beat that crosses an agent boundary ships with a scenario.
- Mechanical behavior must have deterministic tests before narrative evals.
- Prefer structural turn checks to rubric criteria whenever the claim is
  machine-testable.
- Goldens store reviewed agent results in the same shape as actual results.
  Compare contract fields exactly and natural-language fields semantically.
- Update or delete a stale scenario in the same change that alters the game
  contract. Do not support old scenario shapes with compatibility code.
- A passing mock pack proves harness and contract health, not live prose quality.
- Every scenario has exactly one scenario-level thread check. Add dimensions to
  its rubric instead of adding more verdicts or per-turn semantic judge checks.
- A passing judge is evidence for review, not proof that the game is fun.
