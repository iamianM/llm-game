# Build Plan: Phase G8 — Social Friction, Interruptions, Dashboard

> Historical build plan. This file is kept for implementation context only.
> Current planning lives in [current-plan.md](current-plan.md).

Phase G shipped a living villa with conversations, memories, and gossip. G7 surfaced enough of that for the user to actually play and review. G8 fixes the four things the first real playthrough exposed:

1. **Initial conversation rolls still uncapped.** Picking a Friendly intent with Banter 8 = 95% success regardless of risk. The cap added in G7 only applies to follow-up options. Conversations feel frictionless because they are.
2. **Wheel exit options don't close conversations.** "Leave it there" generates a goodbye exchange and the wheel comes back for more. Exits aren't exits.
3. **Pull-for-chat is unconditional.** `Talk to Chloe` always starts a conversation even when Chloe is mid-flirt with Liam. The Pull System from [09-Social-Dynamics.md](../09-Social-Dynamics.md) is absent.
4. **No NPC interruptions.** Players exist in a bubble during their own conversations. NPCs never approach mid-chat. The interruption system from [09-Social-Dynamics.md](../09-Social-Dynamics.md) is also absent.

Plus: G8 introduces a **playthrough eval layer** so future recorded sessions can be assertion-checked, and **enhanced session HTML** so you can read a playthrough and see exactly what happened in each turn including the success math.

Read [`ENGINEERING.md`](../ENGINEERING.md), [`docs/qa-strategy.md`](qa-strategy.md), [`docs/build-plan-G.md`](build-plan-G.md), and the design docs cited above before starting.

---

## Operating Contract

Same shape as G. One commit per sub-phase. `make qa` green at each. Append to `docs/build-log.md`. Stop and report only if: 2+ sessions on one sub-phase, `make qa` red and you can't fix it, scope expansion, or an API/model failure.

Five sub-phases, ship in order. After G8.4 lands, the user plays one more recorded session and runs the new playthrough eval to confirm feature coverage. After G8.5 (dashboard) lands, the user reviews the enhanced session HTML for the feel check.

---

## Architectural Decisions

### Risk-by-category for initial intents

`Intent` Pydantic model gains an optional `risk: Literal["safe","low","medium","high"]` field. Default mapping by category when not explicitly set:

| Category | Default risk |
|---|---|
| friendly | low |
| banter | low |
| flirty | medium |
| deep | high |
| supportive | safe |
| gossip | medium |

The mapping lives as a constant in `engine/intents.py`. Authors can override per-intent in `content/intents.yaml` if a specific intent should be unusually safe or risky. Apply the existing `RISK_SUCCESS_CAP` to `intent_success_chance` the same way it's applied in `follow_up_success_chance`.

### Conversation exit semantics

Two distinct exit paths, both end the conversation but they look different to the player and to the math:

| Path | Trigger | Exchange? | Curator? | Relationship effect |
|---|---|---|---|---|
| **Graceful wheel exit** | RESPOND_WITH with `option.category == "exit"` OR `intent_kind in EXIT_INTENT_KINDS` | Yes — Islander Voice writes a goodbye exchange | Yes | `trust +1` for ending warmly |
| **Walk away** | Top-level `END_CONVERSATION` action | No | Yes (curates what was said so far) | `affection -1` for being curt |

`EXIT_INTENT_KINDS = {"end_softly", "walk_away", "change_subject_and_drift"}`. Note that "walk_away" appears in both — the *option intent* and the *top-level command* — but the path differs based on whether it came via RESPOND_WITH or END_CONVERSATION.

### Pull-for-chat

`PullAttempt` Pydantic model captures the new social roll:

```python
class PullAttempt(BaseModel):
    target_id: str
    started_from_location: Location
    success: bool
    chance: int
    roll: int
    blocked_conversation_id: str | None       # the NPC convo the target was in, if any
    deflection_line: str | None               # NPC-voice deflection if pull failed
```

Lives in `engine/pull.py`. Triggered automatically when player picks `START_CONVERSATION` and the target is in an active `NPCNPCConversation`. If the target is alone, no pull roll — conversation starts normally.

Pull chance formula:

```
chance = 50 + (graft × 4) + (player_affection_with_target ÷ 4)
       - (target_other_chemistry ÷ 3)
       + privacy_modifier
risk = derived from chance: safe ≥85, low 70-84, medium 50-69, high <50
clamp to [10, 90]
```

Where:
- `graft` is `state.player.stats.graft`
- `player_affection_with_target` is `state.islanders[target].relationship.affection`
- `target_other_chemistry` is the chemistry score the target NPC has with the player relative to whoever they're currently chatting with — for v0 just use `target.relationship.chemistry` as a proxy (target's chemistry with player; high chemistry = wants to be pulled away)
- `privacy_modifier`: bedroom +10, terrace +5, pool 0, kitchen -5 (busier = harder to pull)

On miss: no conversation starts. Engine generates a brief deflection exchange via Islander Voice with `intent_kind="pull_rejected"`. Small `affection -1` to the target (you imposed). Bystanders at the location form a witnessed memory ("X tried to pull Y away from Z and got brushed off").

On success: the target's existing NPC conversation closes with `reason="pulled_away"`. Curator runs on that closed convo (producing memories for the abandoned partner — gossip fuel). Then the player's new conversation starts as normal.

### NPC interruptions

`NPCInterruption` Pydantic model added to `VillaUpdate`:

```python
class NPCInterruption(BaseModel):
    interrupter_id: str
    reason: Literal["jealous", "has_gossip", "drawn_to_topic", "needs_to_talk"]
    urgency: Literal["polite", "insistent", "dramatic"]
```

The Villa Orchestrator decides when to fire one (prompt update). At most one per turn. Cannot fire if the player has no active conversation. Cannot fire if `state.active_conversation.pending_interruption is not None` (one at a time).

When an interruption fires, it's stored as `state.active_conversation.pending_interruption`. On the next turn's wheel, three special options appear at the top (code-injected, not LLM-generated):

| Option | intent_kind | Effect |
|---|---|---|
| **Welcome them** | `accept_interruption` | Current conversation closes via Curator. New conversation starts with interrupter. Slight `affection -2` with current target (you left them) and `affection +3` with interrupter (you welcomed them). |
| **Politely defer** | `defer_interruption` | EQ roll. Success: interrupter accepts the deferral, leaves with `affection -1` (mild snub). Miss: interrupter takes offense, `affection -3`, forms a memory tagged `snubbed_publicly`. Current conversation continues. |
| **Ignore them** | `ignore_interruption` | Current conversation continues. Interrupter walks away with `affection -4` and forms a high-weight memory tagged `ignored_in_public`. |

The Contextual Options agent still runs to produce normal follow-ups, but the wheel renders the three interruption options first (visually distinct: "**Interruption: Maya wants to talk** (urgency: insistent — jealousy)") followed by the regular wheel.

Bystanders at the location form witness memories about how the player handled the interruption.

### Playthrough eval layer (new L7)

`python -m src.game.cli verify --playthrough TRACE_PATH` runs feature-coverage assertions on a recorded trace and outputs a structured report. This is the "did the playthrough actually exercise the systems?" check.

Different from L4 scenario fixtures (which assert exact mechanical hashes). L7 asserts gameplay-feel signals:

- "Conversations include at least one wheel exit AND one walk-away."
- "At least one START_CONVERSATION triggered a pull attempt."
- "At least one pull attempt failed."
- "At least one NPC interruption fired and was responded to."
- "Memories generated by curator ≥ 3 per major NPC."
- "Success rolls below 60% occurred at least 3 times across the playthrough."
- "Gossip option surfaced and was picked at least once."

Each assertion is a small Pydantic check function. The runner outputs which passed, which failed, and a one-line "why" per failure. Useful for the user to confirm a recorded playthrough exercised the system properly. Goes alongside the existing L4 scenario suite.

### Dashboard views

Two HTML surfaces:

**Enhanced session.html.** Per-turn cards gain:
- **Success math breakdown:** `Banter (8) × 5 + affection (15) ÷ 4 + risk (low: +5) = 88. Rolled 47. Success.` Visible reasoning for every roll.
- **Mini villa map per turn:** small left-rail summary of "who's where" at the start of the turn.
- **Memories formed this turn:** if any Curator batches fired, list the memories with their tags and weight.
- **Pull attempts:** when a pull fires, show the chance, the roll, success/fail, and the deflection line if miss.
- **Interruption events:** when an interruption fires, render it prominently with the urgency tag and the player's response.
- **Color-coded event types:** success greens, miss reds, pull attempts oranges, interruptions purples.
- **Collapsible turn cards** for long playthroughs (≥30 turns).

**New playthrough-eval.html.** A separate page generated from `verify --playthrough` output:
- Top: red/green pass-fail per assertion.
- Middle: aggregate stats (turns, conversations, memories, pulls, interruptions, success rate by category).
- Bottom: "interesting turns" — auto-flagged moments worth re-reading (the failed roll, the interrupted moment, the gossip pick).
- Linked from `index.html`.

---

## Phase G8.1 — Balance + Exits

**Design source:** [02-Core-Mechanics.md § Interaction Success Formula](../02-Core-Mechanics.md), [05-Interaction-System.md § Hybrid Menu System](../05-Interaction-System.md), [11-Conversation-Flow.md § Conversation Endings](../11-Conversation-Flow.md).

**Scope.** Cap initial intent rolls by category. Make wheel exit options actually close the conversation. Add walk-away penalty.

**Changes.**

- `content/intents.yaml`: add `risk` field per intent (optional). Where omitted, default-by-category applies (table in Architectural Decisions). For v0 leave the YAML alone and rely on the default mapping. Bump `SCHEMA_VERSION` if any model changes (likely none here).
- `src/game/engine/intents.py`: add `Intent.risk: Literal["safe","low","medium","high"] | None = None`. Add `CATEGORY_DEFAULT_RISK` constant. Add helper `effective_risk(intent) -> Risk` that returns the explicit risk or the category default.
- `src/game/engine/rules.py`:
  - `intent_success_chance` now applies the same `RISK_SUCCESS_CAP` already used by `follow_up_success_chance`. Add the risk modifier into the formula too (using `effective_risk(intent)`).
  - In the RESPOND_WITH handling: when the chosen option's `category == "exit"` OR `intent_kind in EXIT_INTENT_KINDS`, after applying deltas, generate the exchange via Islander Voice (the normal path), then close the conversation. Run Curator. Apply `trust +1` to the target (graceful exit bonus).
  - END_CONVERSATION path: apply `affection -1` to the active conversation's target before closing. Curator still runs.
- `src/game/engine/turn.py`: update the conversation-close path to handle the new "wheel-exit triggers close" flow. Make sure Curator and close happen after Islander Voice generates the exchange, not before (otherwise the goodbye exchange doesn't get into the curated memory batch).
- `src/game/cli/commands/play.py`: rename the top-level `END_CONVERSATION` label from `"End conversation"` to `"Walk away (curt)"` for the player to see the distinction. Add a `/help` blurb explaining the difference.

**Tests (engine, non-LLM).**

- `tests/engine/test_rules.py`:
  - `test_initial_intent_chance_capped_by_category_default` — Friendly intent with banter 10 caps at low (80), not 95.
  - `test_initial_intent_explicit_risk_overrides_default` — Intent with explicit `risk: high` caps at 50.
  - `test_wheel_exit_closes_conversation` — RESPOND_WITH with end_softly option closes the active conversation.
  - `test_wheel_exit_applies_trust_bonus` — exit option result includes trust +1 delta.
  - `test_wheel_exit_runs_curator` — Curator is invoked when conversation closes via wheel exit (use mock curator, assert called).
  - `test_walk_away_applies_affection_penalty` — END_CONVERSATION reduces target affection by 1.
  - `test_walk_away_runs_curator` — Curator runs on whatever exchanges occurred before the walk-away.
  - `test_end_conversation_without_active_does_not_crash` — END_CONVERSATION when no active conv is a no-op (or raises cleanly).

**Acceptance criteria.**

- `make qa` green.
- Picking "Tell a joke" (banter, default low risk) with banter 8 produces success_chance ≤ 80, not 95.
- Picking a wheel "Exit" option closes the conversation, generates a goodbye exchange, applies trust +1, and runs the Curator.
- Picking top-level "Walk away" closes the conversation silently, applies affection -1, and runs the Curator.
- New tests above all pass.

**Anti-goals.**

- No changes to follow-up math (G7 already capped follow-ups).
- No changes to Pull-for-chat or interruption logic (those are G8.2 and G8.3).
- No changes to the wheel rendering or prompt files (G8 doesn't touch prompts).

---

## Phase G8.2 — Pull-for-Chat

**Design source:** [09-Social-Dynamics.md § The Pull System](../09-Social-Dynamics.md).

**Scope.** When the player picks `START_CONVERSATION` and the target is in an active NPC-NPC conversation, run a pull roll. On miss, the target deflects with a brief in-voice line and no conversation starts. On success, the target's existing conversation closes (with memories generated) and the player's conversation begins.

**Changes.**

- `src/game/engine/pull.py` (new):
  - `class PullAttempt(BaseModel)` per Architectural Decisions.
  - `pull_chance(state, target_id) -> int` — pure function, no LLM.
  - `target_in_active_conversation(state, target_id) -> NPCNPCConversation | None` — helper.
  - `attempt_pull(state, target_id, rng) -> PullAttempt` — rolls, returns structured result.
- `src/game/engine/rules.py`:
  - `apply_action` for `START_CONVERSATION`: before opening the new conversation, check if target is in another convo. If yes, call `attempt_pull`. If miss: do NOT open the player's conversation, do NOT call Islander Voice for the player's intent. Instead, generate a pull-rejection exchange (Islander Voice with `intent_kind="pull_rejected"` and the deflection context). Apply `affection -1` to target. Add witness memories for bystanders. Return the MechanicalResult with `success=False`, `tags=["pull_rejected"]`, and the `PullAttempt` recorded in `MechanicalResult.pull_attempt: PullAttempt | None`.
  - If hit: close the target's existing NPCNPCConversation with reason `"pulled_away"`. Run Curator on that closed conv. Open the player's new conversation as normal.
- `src/game/state/models.py`:
  - Add `pull_attempt: PullAttempt | None = None` to `MechanicalResult`.
  - Hash-include `pull_attempt.target_id`, `success`, `chance`, `roll`, `blocked_conversation_id`. Hash-exclude `deflection_line` (LLM prose).
- `src/game/cli/commands/play.py`: when a pull attempt is recorded, the turn output shows it explicitly: `"You tried to pull Chloe (62% chance) — she demurred."` followed by the deflection exchange if miss.
- `src/game/reporting/html.py`: pull attempts get their own card style (orange).

**Tests (engine, non-LLM).**

- `tests/engine/test_pull.py` (new):
  - `test_pull_chance_higher_with_more_graft` — graft 9 gives higher chance than graft 3 at same affection.
  - `test_pull_chance_lower_when_target_chemistry_strong` — high target chemistry reduces chance.
  - `test_pull_chance_privacy_modifier_applied` — bedroom > pool > kitchen.
  - `test_pull_chance_clamped_to_10_90` — extreme inputs respect the clamp.
  - `test_target_in_active_conversation_returns_correct_conv` — utility correctness.
  - `test_pull_succeeds_when_target_alone_no_roll_needed` — START_CONVERSATION on a target not in any NPC convo skips the pull entirely.
- `tests/engine/test_rules.py`:
  - `test_start_conversation_with_pull_success_opens_new_convo` — high-chance pull succeeds, player's conversation starts, target's old convo closes.
  - `test_start_conversation_with_pull_failure_does_not_open` — guaranteed-fail pull (chance capped at 10, roll forced higher via mocked RNG) does not start the player's conv.
  - `test_pull_failure_applies_affection_penalty` — target loses 1 affection.
  - `test_pull_failure_bystanders_get_witness_memory` — bystanders at the location form witnessed memories tagged `saw_pull_rejected`.
  - `test_pull_success_closes_targets_existing_conv` — when pull succeeds, the target's old convo closes with reason `pulled_away`.
  - `test_pull_attempt_recorded_in_mechanical_result` — the `pull_attempt` field is populated on START_CONVERSATION when there was a contested target.

**Tests (LLM, opt-in `-m llm`).**

- `tests/agents/test_islander_voice_pull_rejected.py`:
  - Parametrized over the four NPCs (Chloe, Maya, Liam, Aisha bombshell).
  - Asserts: prose is 20-100 words, in character (uses the archetype voice), not warm-accepting, references the fact that the NPC was busy with someone else.

**Acceptance criteria.**

- `make qa` green.
- `make test-llm` green: 4 new pull-rejection tests pass.
- In `make play`, when an NPC is in a background convo at your target location, picking `Talk to X` fires a roll. You see the chance, the roll, and either the conversation starts or a deflection exchange plays.
- Pull-rejection produces witnessed memories for bystanders.
- Pull success closes the target's prior conversation cleanly with `reason=pulled_away` and curates it.

**Anti-goals.**

- No pull rolls for conversations the player is already in (pulls only apply on START).
- No "pull continues for multiple turns" — single roll, instant outcome.
- No prompt changes — Islander Voice already handles ad-hoc `intent_kind` values.

---

## Phase G8.3 — NPC Interruptions

**Design source:** [09-Social-Dynamics.md § Conversation Interruptions](../09-Social-Dynamics.md).

**Scope.** The Villa Orchestrator can fire an NPC interruption during the player's active conversation. When it fires, the player's next wheel shows three special options (Welcome / Defer / Ignore) at the top with appropriate flavor. Each option has its own mechanical outcome and memory effects.

**Changes.**

- `src/game/state/models.py`:
  - `class NPCInterruption(BaseModel)` per Architectural Decisions.
  - Add `pending_interruption: NPCInterruption | None = None` to `Conversation` (player's active conversation, not NPCNPC).
  - Hash-include: `interrupter_id`, `reason`, `urgency`. (Interruptions are state-affecting decisions.)
- `src/game/agents/villa_orchestrator.py`:
  - Extend `VillaUpdate` to include `npc_interruptions: list[NPCInterruption] = []` (max 1 element per turn enforced by validator).
  - Update the prompt at `src/game/agents/prompts/villa_orchestrator.md` (Claude rewrites — install verbatim).
- `src/game/engine/villa.py`:
  - `validate_villa_update` rejects: more than one interruption per turn, interruption when player has no active conversation, interruption when one is already pending, interruption where interrupter_id is at a different location than the player.
  - `apply_villa_update` writes the interruption to `state.active_conversation.pending_interruption`.
- `src/game/engine/actions.py`:
  - When the player's active conversation has a `pending_interruption`, `available_actions` injects three interruption-handling options as `RESPOND_WITH` actions with new intent_kinds: `accept_interruption`, `defer_interruption`, `ignore_interruption`. These are NOT generated by the Contextual Options LLM — they're code-injected. Display labels: "Welcome them (Maya, jealous)", "Politely defer", "Ignore them."
- `src/game/engine/rules.py`:
  - Handle the three new intent_kinds in `apply_action` / `_apply_follow_up`:
    - `accept_interruption`: close current conversation (Curator runs). Open new conversation with interrupter as target. Apply deltas (current target: affection -2; interrupter: affection +3). Clear pending_interruption.
    - `defer_interruption`: EQ roll using `defer_chance(state, interrupter_id)` (formula: 50 + eq*4 + interrupter affection ÷ 4). On success: interrupter accepts gracefully, walks off, affection -1 with interrupter. On miss: interrupter offended, affection -3, witnessed memory tagged `snubbed_publicly`. Current conv continues. Clear pending_interruption.
    - `ignore_interruption`: current conv continues. Interrupter walks off with affection -4 and high-weight memory tagged `ignored_in_public`. Clear pending_interruption.
  - Add `IslanderState.tags_to_remember` mechanism: interruptions where the player handled them poorly (`snubbed_publicly`, `ignored_in_public`) become memories with weight 7-8 (very gossip-worthy).
- `src/game/cli/commands/play.py`:
  - When `state.active_conversation.pending_interruption` is set, render the interruption block above the wheel: `*** Interruption: Maya wants to talk (insistent, jealous) ***`.
- `src/game/reporting/html.py`: interruption turns get their own card style (purple).

**Tests (engine, non-LLM).**

- `tests/engine/test_interruptions.py` (new):
  - `test_orchestrator_can_emit_interruption_in_villa_update` — VillaUpdate schema accepts NPCInterruption.
  - `test_villa_update_rejects_two_interruptions_in_one_turn`.
  - `test_villa_update_rejects_interruption_when_no_player_conv`.
  - `test_villa_update_rejects_interruption_when_one_already_pending`.
  - `test_villa_update_rejects_interruption_at_wrong_location`.
  - `test_pending_interruption_injects_three_wheel_options`.
  - `test_accept_interruption_closes_current_starts_new`.
  - `test_accept_interruption_applies_relationship_deltas` — current target -2 affection, interrupter +3.
  - `test_defer_interruption_eq_roll_success_path`.
  - `test_defer_interruption_eq_roll_failure_path` — affection -3, memory tagged `snubbed_publicly`.
  - `test_ignore_interruption_keeps_current_drops_affection_4`.
  - `test_interruption_cleared_after_player_responds`.

**Tests (LLM, opt-in `-m llm`).**

- `tests/agents/test_villa_orchestrator_interruptions.py`:
  - 5 parametrized scenarios (player flirting with Chloe + Maya at same loc with jealousy memory; player deep-talking Liam + Aisha at same loc with gossip; etc.). Asserts: orchestrator outputs at least one interruption in scenarios where the interrupter has clear motivation, zero when motivation is absent.

**Acceptance criteria.**

- `make qa` green.
- `make test-llm` green: 5 new orchestrator-interruption tests pass.
- In `make play`, during your conversation with Chloe, the wheel sometimes shows `*** Interruption: Maya wants to talk ***` with three Welcome/Defer/Ignore options at the top.
- Each option produces distinct mechanical and memory outcomes per the table in Architectural Decisions.
- The interruption clears from state once the player responds.
- Bystanders form witness memories when the player snubs or ignores someone publicly.

**Anti-goals.**

- No more than one pending interruption per turn.
- No chained interruptions (interrupter can't be interrupted by a fourth person in the same wheel).
- No prompt-driven generation of the three interruption-handling options — they're code-injected so the mechanical contract is guaranteed.
- No interruptions during ceremonies or phase transitions (orchestrator validation rejects them).

---

## Phase G8.4 — Playthrough Eval Layer

**Design source:** [docs/qa-strategy.md § Test Layers](qa-strategy.md). This adds a new L7 layer specifically for verifying recorded playthroughs exercise the system.

**Scope.** New CLI command `verify --playthrough TRACE_PATH` runs structured feature-coverage assertions on a recorded trace. Output goes to stdout as a checklist + structured JSON (so the dashboard can render it).

**Changes.**

- `src/game/eval/playthrough.py` (new):
  - `class PlaythroughAssertion(BaseModel)` with `name`, `description`, `passed: bool`, `detail: str`.
  - `class PlaythroughReport(BaseModel)` with `assertions: list[PlaythroughAssertion]`, `aggregate_stats: dict[str, int|float]`, `interesting_turns: list[InterestingTurn]`.
  - `class InterestingTurn(BaseModel)` — turn index + reason it was flagged (e.g. `"first_pull_failure"`, `"failed_high_risk_flirt"`, `"interruption_ignored"`).
  - `evaluate(trace_records: list[dict]) -> PlaythroughReport` — runs every assertion against the trace.
- Initial assertion suite (each in its own pure function):
  - `assert_at_least_one_wheel_exit`
  - `assert_at_least_one_walk_away`
  - `assert_at_least_one_pull_attempt`
  - `assert_at_least_one_pull_failure`
  - `assert_at_least_one_interruption_fired`
  - `assert_at_least_one_interruption_response_per_kind` (accept, defer, ignore — at least two of three exercised)
  - `assert_memory_coverage_per_major_npc` — every non-eliminated NPC has ≥3 memories by run end.
  - `assert_low_success_chance_rolls_present` — at least 3 rolls with chance ≤ 60% in the trace.
  - `assert_gossip_surfaced_and_picked` — at least one RESPOND_WITH with `category="gossip"`.
  - `assert_background_dialogues_generated` — at least 10 background dialogue commits.
  - `assert_ceremony_event_observed` — recoupling or bombshell event fired.
- `src/game/cli/commands/verify.py`: extend the existing `verify` subcommand:
  - Existing `verify --all` continues to verify scenario fixtures (L4).
  - New `verify --playthrough TRACE_PATH` runs the new eval and prints the report. Exit code: 0 if all assertions pass, 1 if any fail.
  - Pretty-print output: ✓/✗ per assertion, aggregate stats block, list of interesting turns.
- `src/game/cli/commands/report.py`:
  - Add `report eval-dashboard --trace TRACE_PATH --out PATH` that runs the eval and renders an HTML dashboard.
  - Existing `report packet --trace` should also embed a link to the eval dashboard if one exists.

**Tests (engine, non-LLM).**

- `tests/eval/test_playthrough.py` (new):
  - `test_evaluate_empty_trace_fails_most_assertions` — empty trace produces all-fail report.
  - `test_assertion_at_least_one_wheel_exit_detects_correctly` — feed a trace with one wheel exit, passes; without, fails.
  - Same parametric structure for each of the 11 assertions: positive case, negative case, exact-boundary case.
  - `test_interesting_turn_detection_flags_pull_failure` — a trace with a failed pull produces an interesting-turn entry for that turn.
  - `test_report_exit_code_zero_when_all_pass` — CLI returns 0 if assertions all pass.
  - `test_report_exit_code_one_when_any_fail` — CLI returns 1 if any fail.

**Acceptance criteria.**

- `make qa` green.
- `python -m src.game.cli verify --playthrough .game_traces/manual-day1.json` runs and produces a structured report.
- The 11 assertions evaluate correctly against the existing recorded trace (which is one turn — so most will fail). User runs a new full playthrough, regenerates, and most pass.
- The CLI exits non-zero when assertions fail.
- The assertion code is small and obvious — each is a single pure function over `list[dict]` (the trace records).

**Anti-goals.**

- No LLM-based assertions in this phase (no "judge agent" yet). All assertions are structural over trace data.
- No assertion of game feel beyond presence/absence. ("Was this conversation good?" stays human judgment.)
- No regression against existing scenario fixtures. L4 stays untouched.

---

## Phase G8.5 — Dashboard + Enhanced Session HTML

**Design source:** This document. Inspired by steno's dashboard.html pattern.

**Scope.** Enhance `session.html` so a recorded playthrough is genuinely reviewable. Add `playthrough-eval.html` as the dashboard for the new eval layer.

**Changes.**

- `src/game/reporting/html.py`:
  - Per-turn card gains a **"Math" subsection**: `Banter (8) × 5 + affection (15) ÷ 4 + risk (low: +5) = 88. Rolled 47. → Success.` Visible at all times, not collapsed.
  - Per-turn card gains a **"Villa snapshot" subsection** showing the pre-turn villa map (4 locations × who's where) and active NPC convos with topic.
  - Per-turn card gains a **"Memories this turn" subsection**: if Curator batches fired, render each memory as `Holder: "content" — weight N, tags: [...]`.
  - Per-turn card gains a **"Pull attempt" subsection** when present: chance, roll, result, deflection line if applicable.
  - Per-turn card gains an **"Interruption" subsection** when present: interrupter, reason, urgency, player's response.
  - **Color coding via CSS classes**: `.outcome-success` (green), `.outcome-miss` (red), `.pull-attempt` (orange), `.interruption` (purple).
  - **Collapsible turn cards** via `<details>` HTML element. Default-collapsed when total turns > 20.
- `src/game/reporting/eval_dashboard.py` (new):
  - `render_eval_dashboard(report: PlaythroughReport) -> str`.
  - Top section: pass/fail checklist with each assertion + reason.
  - Middle: aggregate stats grid (n_turns, n_conversations, n_memories, n_pulls, success_rate_per_category, n_interruptions).
  - Bottom: "Interesting turns" list with links into `session.html#turn-N`.
- `src/game/cli/commands/report.py`:
  - `report packet --trace PATH --out PATH` now generates both `session.html` (enhanced) and `playthrough-eval.html`.
  - `index.html` links to both.

**Tests (engine, non-LLM).**

- `tests/cli/test_report.py`:
  - `test_session_html_includes_math_subsection`.
  - `test_session_html_includes_villa_snapshot`.
  - `test_session_html_renders_memories_when_curator_fired`.
  - `test_session_html_renders_pull_attempt`.
  - `test_session_html_renders_interruption_block`.
  - `test_session_html_uses_collapsible_cards_when_many_turns`.
  - `test_eval_dashboard_renders_pass_fail_grid`.
  - `test_eval_dashboard_links_to_interesting_turns`.

**Acceptance criteria.**

- `make qa` green.
- Opening `review-packet/session.html` from a real playthrough shows every turn with the success math visible, the villa snapshot, any memories formed, any pull attempts, any interruptions, color-coded.
- Opening `review-packet/playthrough-eval.html` shows the pass/fail checklist for the 11 assertions plus aggregate stats and links to interesting turns.
- A playthrough trace ≥ 30 turns renders without HTML overflow problems (collapsible cards make it scannable).

**Anti-goals.**

- No JavaScript beyond `<details>`/`<summary>` native HTML5. No chart library, no JS frameworks. Pure HTML+CSS as established in the report stack.
- No external CSS or fonts. Self-contained.
- No graphs of progression-over-time (e.g. line charts of relationship values). The user looks at turns directly.

---

## Prompts

The villa orchestrator prompt gets one additive update for interruption support. I (Claude) own the rewrite per R17 — Codex installs verbatim.

- [`src/game/agents/prompts/villa_orchestrator.md`](../src/game/agents/prompts/villa_orchestrator.md) — **G8.3.** I add an `## Interruptions` section to the prompt describing the new `npc_interruptions` output field, when to fire, and the four reason/urgency vocabularies. Existing sections unchanged.

No other prompt changes in G8. Pull rejection reuses Islander Voice with `intent_kind="pull_rejected"` — the existing prompt's fallback handling for unknown intent_kinds covers it.

The contextual_options prompt is unchanged. The three interruption-handling options are **code-injected** into the wheel by the engine, not generated by the LLM. This is deliberate: the mechanical contract on those three options has to be guaranteed, not subject to LLM phrasing drift.

---

## Global Anti-Goals (G8-specific)

Hold across all sub-phases:

- ❌ No cost optimization. Same as G.
- ❌ No new agents beyond what G shipped. G8 reuses Islander Voice, Contextual Options, Curator, Villa Orchestrator, Background Dialogue.
- ❌ No prompt rewrites except the one villa_orchestrator update I own.
- ❌ No `# type: ignore`, no `--no-verify`. R5.
- ❌ No backwards compat for old recordings. If schema changes, fixtures regenerate. R12.
- ❌ No chained interruptions / pulls. One per turn per kind.
- ❌ No LLM-judge layer in eval (deferred to a hypothetical G9).
- ❌ No abandonment of the existing `verify --all` (scenario fixtures still work — G8 only adds `verify --playthrough`).

---

## Done Definition

Phase G8 is done when:

1. Commits G8.1, G8.2, G8.3, G8.4, G8.5 each exist with `make qa` green.
2. `docs/build-log.md` has an entry per sub-phase.
3. `make test-llm` passes all new opt-in tests (≥9 new tests).
4. `make play` exercises all four new mechanics live: initial intents respect risk; wheel exits actually exit; pull-for-chat fires with a roll when target is busy; interruptions appear with three options.
5. The user plays one full session via `make play --record .game_traces/manual-day2.json` (or whichever name).
6. `python -m src.game.cli verify --playthrough .game_traces/manual-day2.json` passes ≥9 of the 11 assertions (some assertions like "gossip picked" depend on player choice and may be 0).
7. `python -m src.game.cli report packet --trace .game_traces/manual-day2.json --out review-packet` produces both `session.html` (enhanced) and `playthrough-eval.html`.
8. The user reads the enhanced session HTML and confirms: success math feels right, pull moments feel earned, interruption moments feel earned, exits feel distinct.

After this, the next phase is Phase H (Vite UI) or H' (depth — Big 5, archetypes, Type on Paper, win condition, character creation). Decision depends on whether the user wants more *content depth* or a *real interactive surface* after G8 lands.
