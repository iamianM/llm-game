# Build Plan: Phase H7 — AI Self-Play Validation

> Historical build plan. This file is kept for implementation context only.
> Current planning lives in [current-plan.md](current-plan.md).

H1-H5 build the game. H6 makes it readable. H7 makes it self-validating. A new **Player Autopilot** agent picks actions strategically with the goal of winning the final vote. Recorded autopilot traces become a reproducible quality signal: when prompts change, we replay the same autopilot against the same seed and see whether the game still feels coherent.

**Design sources:** None directly — H7 is process infrastructure. Pattern reference: balance simulation in [`src/game/reporting/balance.py`](../src/game/reporting/balance.py), but with an LLM-driven policy instead of random.

**Operating contract:** See [build-plan-H-index.md](build-plan-H-index.md). Smallest phase in the H series; ships last because it depends on H1 (a win condition to optimize for) and H2 (variety to react to).

---

## Architectural Decisions

### Player Autopilot agent

New agent `src/game/agents/player_autopilot.py`. Model: `gpt-4.1-mini`. Prompt: `src/game/agents/prompts/player_autopilot.md` (Claude writes it — install verbatim per R17).

Input each turn: full visible state, available actions list, recent player history (last 3 turns), current outcome trajectory (audience rank, couple strength, etc).

Output: a `PolicyDecision` Pydantic model:

```python
class PolicyDecision(BaseModel):
    chosen_action_index: int                    # which available action to pick
    rationale: str                              # short reason, recorded for review
    confidence: Literal["high", "medium", "low"]
```

The autopilot picks from the **same `available_actions` list** the human would see. It can't invent actions. It can't see hidden state (Type on Paper that hasn't been revealed, NPC private memories, etc.). Same information constraint as a real player.

### CLI autopilot mode

New `play` flag: `--autopilot`. When set:

1. Character creation step also runs through the autopilot (it picks an archetype + stat allocation).
2. Each turn, instead of waiting for user input, the autopilot decides.
3. The trace records both the action and the autopilot's `rationale`.
4. The CLI prints each decision so the user can spectate.
5. The run completes automatically end-to-end.

Output trace file is recorded the same way `--record` does. Compatible with `report packet --trace`.

### Autopilot character creation

Special context for the character creation step: the autopilot picks an archetype based on a personality bias passed in as a flag (`--persona loyal` / `--persona player` / `--persona chaotic`) so we can reproduce "this archetype-style autopilot." Default: `loyal`.

Persona biases stat allocation too. The autopilot prompt receives the persona and picks consistently.

### Trace and report integration

An autopilot trace looks like a manual trace plus `agent_commits.player_autopilot: PolicyDecision | None` per turn. The HTML report (H6) displays the autopilot's rationale in a small italic line under each player action (when present).

The eval dashboard works the same on autopilot traces. The user can compare:

- Manual trace from the user playing
- Autopilot trace with same seed
- See whether assertions match and where the playthroughs diverge

### Eval suite extension

H7 adds two assertions:

- `assert_autopilot_outcome_assigned` — when the trace is an autopilot run, the run completed to a terminal state with `outcome` set. This catches autopilot runs that crash partway.
- `assert_autopilot_rationale_present` — when the trace is an autopilot run, each player-decision turn has a non-empty `rationale`.

These are gated by the trace's `mode` field (added in H7): `mode ∈ {manual, autopilot, mocked}`. Non-autopilot traces skip these assertions.

### Reproducibility

Autopilot decisions are recorded. To re-run the same autopilot session: `play --replay TRACE_PATH`. The same `PolicyDecision` outputs replay from the recorded commits, no fresh LLM calls. Determinism contract: same seed + same recorded commits = same final hash.

When you change something that should be replay-safe, autopilot traces should still reproduce. When you change game mechanics that affect outcomes, autopilot traces will diverge — that's a signal to record a fresh autopilot run.

### Standard pre-release check

A make target: `make autopilot-check`. Runs:

1. `make play --autopilot --seed 42 --record .game_traces/autopilot-check.json` (real LLM)
2. `make verify --playthrough .game_traces/autopilot-check.json`
3. Exit nonzero if any assertion fails.

Use this before commits that touch agents, prompts, or game logic. It's not in `make qa` (LLM cost) but it's the standard "did I break the game?" check.

---

## Changes by file

### New files

| File | Purpose |
|---|---|
| `src/game/agents/player_autopilot.py` | The autopilot agent + PolicyDecision schema |
| `src/game/agents/prompts/player_autopilot.md` | Prompt (Claude writes, install verbatim) |
| `tests/agents/test_player_autopilot.py` | LLM tests for autopilot contract |
| `tests/scenarios/fixtures/autopilot-day1.yaml` | Scenario with recorded autopilot decisions |

### Files changed

- [`src/game/state/models.py`](../src/game/state/models.py): Add `TraceMode` enum (`manual`, `autopilot`, `mocked`). Trace metadata captures `mode`.
- [`src/game/state/trace.py`](../src/game/state/trace.py): `AgentCommits` model adds `player_autopilot: PolicyDecision | None`.
- [`src/game/cli/commands/play.py`](../src/game/cli/commands/play.py):
  - Add `--autopilot` flag.
  - Add `--persona {loyal,player,chaotic}` flag (default `loyal`).
  - When autopilot is on, swap user-input loop for autopilot decision loop.
  - Display each decision and rationale before applying.
  - Trace metadata records `mode=autopilot` and persona.
- [`src/game/engine/recorded_agents.py`](../src/game/engine/recorded_agents.py): Add `RecordedPlayerAutopilot` shim that replays decisions from a trace file.
- [`src/game/eval/playthrough.py`](../src/game/eval/playthrough.py): Add two new assertions; both gated by trace mode.
- [`src/game/reporting/html_blocks.py`](../src/game/reporting/html_blocks.py): Per-turn card optionally renders the autopilot rationale beneath the action.
- [`src/game/reporting/stylish/`](../src/game/reporting/stylish/): Header block notes the trace mode (e.g. "Autopilot run · persona: loyal · seed 42").
- `Makefile`: Add `autopilot-check` target.

---

## Acceptance criteria

- [ ] `make qa` green.
- [ ] `make test-llm` green.
- [ ] `make play --autopilot --record .game_traces/test.json` runs end-to-end without user input.
- [ ] The autopilot picks the character creation archetype + stat allocation + each turn's action.
- [ ] Every player-action turn in the resulting trace has `agent_commits.player_autopilot.rationale` set.
- [ ] The autopilot trace replays via `play --replay TRACE_PATH` with byte-identical final hash.
- [ ] Personas affect autopilot behavior: loyal autopilot stays with original partner at Flush of Hearts; chaotic autopilot tends to escalate flirts and pick risky options; player-persona autopilot tries to optimize the final vote outcome.
- [ ] `verify --playthrough` on an autopilot trace passes both new assertions plus all prior assertions.
- [ ] HTML report displays the autopilot rationale per player turn.
- [ ] `make autopilot-check` runs and exits zero on a healthy build.
- [ ] Scenario fixture `autopilot-day1.yaml` replays deterministically.

---

## Tests

### LLM tests (opt-in)

- `tests/agents/test_player_autopilot.py`:
  - `test_autopilot_picks_from_available_actions`
  - `test_autopilot_rationale_not_empty`
  - `test_autopilot_confidence_in_enum`
  - `test_autopilot_persona_loyal_picks_loyal_options`
  - `test_autopilot_persona_chaotic_picks_risky_options`
  - `test_autopilot_invalid_index_rejected_and_retried`

### Non-LLM tests

- `tests/cli/test_play.py`:
  - `test_play_autopilot_runs_end_to_end_with_mock_agent`
  - `test_play_autopilot_records_rationale_per_turn`
  - `test_play_autopilot_replay_byte_identical`

### Scenario fixtures (mock LLM)

- `tests/scenarios/fixtures/autopilot-day1.yaml`: locked hash with recorded autopilot decisions for the first day.

---

## Evals (new playthrough assertions)

- `assert_autopilot_outcome_assigned` — gated by `mode == autopilot`. Run completed; `state.outcome ∈ RunOutcome`.
- `assert_autopilot_rationale_present` — gated by `mode == autopilot`. Every player-action turn has a non-empty rationale.

Aggregate stats: `autopilot_actions_total`, `autopilot_average_confidence`, `autopilot_run_outcome`.

---

## Anti-goals

- ❌ No "autopilot is smarter than human" claims. The autopilot uses the same available_actions as a human. No hidden-state cheating.
- ❌ No autopilot in `make qa`. LLM cost. Use `make autopilot-check` separately.
- ❌ No multi-step lookahead. Autopilot picks one action per turn based on current state. No tree search.
- ❌ No reward shaping at runtime. The autopilot prompt expresses goals; the engine doesn't grade decisions.
- ❌ No new game mechanics in H7.
- ❌ No editing the autopilot prompt without explicit user direction (R17).

---

## Done checklist for Codex

- [ ] Read [build-plan-H-index.md](build-plan-H-index.md) pre-flight
- [ ] Wait for Claude to write `src/game/agents/prompts/player_autopilot.md` and approve
- [ ] Add `TraceMode` enum and `PolicyDecision` model
- [ ] Write `src/game/agents/player_autopilot.py`
- [ ] Install the autopilot prompt verbatim (R17)
- [ ] Update `state/trace.py` to record autopilot commits
- [ ] Add `RecordedPlayerAutopilot` in `engine/recorded_agents.py`
- [ ] Add `--autopilot` and `--persona` flags to `play.py`
- [ ] Update HTML blocks to render rationale
- [ ] Update stylish header to show trace mode
- [ ] Add `autopilot-check` Makefile target
- [ ] Write LLM tests for autopilot
- [ ] Write non-LLM CLI tests for autopilot flow
- [ ] Add scenario fixture `autopilot-day1.yaml`
- [ ] Extend `eval/playthrough.py`
- [ ] Run `make qa`; fix root causes
- [ ] Run `make test-llm`
- [ ] Run `make autopilot-check` once and verify
- [ ] Append to `docs/build-log.md`
- [ ] Commit: `Phase H7: AI self-play validation`
