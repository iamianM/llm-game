# Build Plan: Phase H8 — Time Budget, NPC Autonomy, Pacing Evals

> Historical build plan. This file is kept for implementation context only.
> Current planning lives in [current-plan.md](current-plan.md).

The H1–H7 phases built a complete game arc, but the autopilot loop Codex hit exposed three structural gaps:

1. **No automatic phase progression.** Days only advance when the player picks `ADVANCE_PHASE`. A real Love Island day passes on its own — phases have time budgets. Without this, the autopilot (or any inefficient player) can spend 100+ turns inside Day 1 Morning.
2. **NPCs almost never leave conversations on their own.** The `departure_probability` formula in `engine/conversation.py` requires either many exchanges or recent failures. With friendly autopilot picks, NPCs build affection and the chance approaches zero. The Villa Orchestrator can move NPCs around the villa but cannot pull a partner out of the player's active conversation.
3. **The eval suite checks feature presence, not pacing.** It catches "Hideaway didn't fire" but not "Day 1 took 60 turns."

H8 closes all three. It also addresses **test suite performance** — the regression slices should be fast and independent, and currently they're not.

**Design sources:** [05-Interaction-System.md § Time Management](../05-Interaction-System.md), [08-Daily-Loop.md § The Four Phases](../08-Daily-Loop.md), [09-Social-Dynamics.md § Conversation Interruptions](../09-Social-Dynamics.md), [11-Conversation-Flow.md § Organic Conversation Endings](../11-Conversation-Flow.md).

**Operating contract:** See [build-plan-H-index.md](build-plan-H-index.md). H8 ships after H7. Three sub-phases that can each commit independently. The user records one short real-LLM session after H8.3 to validate pacing.

---

## Architectural Decisions

### Time as a budgeted resource per phase

Each phase has a fixed minute budget. Each action carries a `time_cost`. When the cumulative cost in a phase reaches or exceeds the budget, the engine forces `advance_phase` automatically.

Phase budgets:

| Phase | Budget (minutes) | Behavior |
|---|---|---|
| `MORNING` | 120 | Open social phase. Time elapses with talk/move actions. |
| `CHALLENGE` | 0 | Fires the challenge and auto-advances in the same turn. |
| `AFTERNOON` | 120 | Open social phase. Same shape as morning. |
| `TEXT` | 30 | Producer text fires, brief reaction window. |
| `EVENING` | 60 | Ceremony fires (if scheduled), then short post-ceremony social window. |

Action costs:

| Action | Cost (minutes) |
|---|---|
| `START_CONVERSATION` | 20 |
| `RESPOND_WITH` | 5 (continuing an open convo is cheaper than starting one) |
| `END_CONVERSATION` | 0 |
| `MOVE` | 5 |
| `HIDEAWAY` | 60 (consumes most of the phase) |
| `CHALLENGE_RESPONSE` | 0 |
| `CASA_DECISION` | 10 |
| `RECOUPLE` | 0 (ceremony-managed) |
| `ADVANCE_PHASE` | 0 (manual override) |
| Slash commands (`/state`, `/hash`, etc.) | 0 |

State extension on `GameState`:

```python
class PhaseClock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phase: Phase
    budget_minutes: int
    elapsed_minutes: int = 0

    @property
    def remaining(self) -> int:
        return max(0, self.budget_minutes - self.elapsed_minutes)

    @property
    def expired(self) -> bool:
        return self.elapsed_minutes >= self.budget_minutes


class GameState(BaseModel):
    ...
    phase_clock: PhaseClock
```

`GameState.phase_clock` is set fresh whenever a new phase begins via `advance_phase`. Bump `SCHEMA_VERSION` to 16.

`run_turn` flow becomes:

1. Apply player action → `MechanicalResult`.
2. Deduct `time_cost` for the action from `phase_clock.elapsed_minutes`.
3. Run Villa Orchestrator + background dialogue per existing flow.
4. If `phase_clock.expired` after step 2, call `advance_phase(state)` and reset `phase_clock`. Mark the trace record's `auto_advance: True`.
5. Return `TurnResult` with `phase_clock` snapshot included.

`auto_advance` is recorded so traces can distinguish player-driven phase changes from time-expired ones.

CLI feedback (in `play_render.py`):
- After each turn: show `Time remaining: 75 min`.
- When `phase_clock.remaining ≤ 20`: print `It's getting late — phase will end soon.`
- When auto-advance fires: print `Time passes. → afternoon.` before the next state print.

### NPC summoning out of player conversations

The Villa Orchestrator already drives off-screen NPC behavior each turn. H8 adds one new output type: **`npc_summoned_elsewhere`** — the orchestrator's way of saying "this NPC needs to leave their current conversation."

```python
class NPCSummon(BaseModel):
    model_config = ConfigDict(extra="forbid")
    npc_id: str
    from_conversation_id: str          # active player conv or NPC-NPC conv id
    reason: Literal[
        "chemistry_partner_arrived",   # someone they're into just showed up
        "friend_needs_them",            # close friend signaled
        "drama_pull",                   # gossip-worthy moment elsewhere
        "needs_space",                  # personality-driven (avoidant retreats)
        "phase_pressure",               # time pressure pushing them on
    ]
    target_location: Location
```

Added to `VillaUpdate.npc_summoned_elsewhere: list[NPCSummon]`.

When the orchestrator emits a summon for the player's current conversation target:

- Engine validates the summon (NPC actually was in that conversation, target_location exists, etc.). Reject otherwise (R2).
- Engine closes the player's active conversation with `reason: "npc_summoned_elsewhere"`.
- Curator runs on the closed conversation (Curator output already handles any close reason).
- NPC's location is updated to `target_location`.
- A short notification renders in the CLI: `Chloe excuses herself: "Liam just walked in, give me a minute."` (The exit line is generated via Islander Voice with a special intent kind `summoned_exit`, which the engine recognizes and the prompt handles as a brief in-voice goodbye.)
- The player's wheel disappears; they're back to the top-level action menu.

When the orchestrator emits a summon for an NPC in an NPC-NPC conversation, the same logic applies but no notification fires (the player isn't there).

The orchestrator's decision is driven by context already in the prompt (recent memories, mood, who's where) plus the new factors documented in the prompt update below.

### Probabilistic arrival rolls

Currently when the Villa Orchestrator moves an NPC X to the player's location while the player is in a conversation, X just appears in the visible state — silently. H8 adds a **probabilistic interruption / pull roll** that fires automatically when an NPC arrives at the player's location during the player's active conversation.

Two independent rolls when X arrives:

**Roll A: Interruption attempt** (X wants to talk to the player).

```
interruption_chance = base 12
  + (relationship_with_player.chemistry × 2)    # X has chemistry with player
  + (recent_gossip_memory_count × 5)             # X has hot gossip to share
  + jealousy_modifier                            # 15 if player's current target is X's high-chem partner
  + mood_modifier                                # ±5 by X's mood
  - 10 if player_target has high public_perception      # less likely to break up popular couple
clamp to [5, 75]
```

If the roll hits, an `NPCInterruption` fires for the next player turn (existing G8 mechanics: Welcome / Defer / Ignore options surface in the wheel). The trace records the chance and the roll.

**Roll B: Pull-away attempt** (X wants to pull the player's current target away).

```
pull_chance = base 8
  + (X_to_target.chemistry × 2)                  # X has chemistry with player's target
  + (recent_drama_memory_count × 4)              # X has reason to talk to target
  - couple_strength_of_target_couple             # if target is in player's couple
  + jealousy_modifier                            # 10 if X is target's couple-partner
clamp to [3, 60]
```

If the pull roll hits, the orchestrator on the *next* turn issues an `NPCSummon` for the player's target. Conversation closes per the summoning flow. From the player's POV: "Aisha walked in. Maya excuses herself: 'I should go say hi.'"

Both rolls are computed and recorded in the trace (whether they hit or not). The engine does the math; the orchestrator decides whether to *act* on a hit. This separation lets us tune balance without changing the agent.

### Eval pacing assertions (no LLM judge)

H8 adds five pacing assertions to `src/game/eval/playthrough.py`:

| Assertion | Pass condition | Catches |
|---|---|---|
| `phase_action_count_reasonable` | mean(actions per phase) ≤ 12 across the trace | Autopilot or player getting stuck in one phase |
| `npc_initiated_exit_observed` | ≥ 1 conversation closed with reason in `{npc_left, npc_summoned_elsewhere}` | NPCs feeling like puppets that never leave |
| `day_progression_reasonable` | final state day ≥ 5 OR run ended via elimination/outcome | Trace ends prematurely or stagnates |
| `time_expired_advance_observed` | ≥ 1 trace record has `auto_advance: True` | Time budget actually fires |
| `npc_arrival_rolls_observed` | ≥ 2 arrival rolls (any hit-or-miss) recorded across the trace | Probabilistic interruption layer running |

These are structural counts, same shape as existing assertions. The user reviews aggregate stats and individual failures; no LLM judge added.

### Eval suite performance

The user is right that the test suite is slow despite assertions being independent. The H8 audit:

1. **Profile current pytest run.** Use `pytest --durations=20` to identify the slow tests. Most likely culprits:
   - Scenario fixtures replaying the full engine each (each ~1-2 sec)
   - Content loading happening per-test instead of once-per-session
   - LLM tests not properly skipped when running non-LLM suite (each adds latency through network setup)
2. **Add `pytest-xdist`** to enable parallel test execution via `pytest -n auto`. Engine tests are pure; scenario fixtures are deterministic and replay from independent state. They parallelize trivially.
3. **Session-scope content loading.** `tests/conftest.py` adds a session-scoped fixture that loads `content/` once and shares the index across tests via dependency injection. The current per-test loading (~20ms each × 200+ tests) is the bulk of the wall time.
4. **Lazy LLM client construction.** Agent classes (OpenAIIslanderVoice etc.) currently call `OpenAI()` in `__init__`. Move to lazy construction inside `generate()` so non-LLM tests that mock the agent don't pay the OpenAI client startup.

After these changes, `make test` should run in under 30 seconds on a modern dev machine vs. the current several minutes.

---

## Phase H8.1 — Time Budget

**Scope.** Add `PhaseClock` to state. Wire action time costs. Auto-advance when budget expires. Surface time remaining in CLI and HTML.

**Changes.**

### New files

| File | Purpose |
|---|---|
| `src/game/engine/time_budget.py` | `PhaseClock` helpers, action cost table, deduction logic |
| `tests/engine/test_time_budget.py` | Unit tests for the budget + auto-advance flow |
| `tests/scenarios/fixtures/time-budget-expiry.yaml` | Scenario: player spends 6 × Talk = 120 min in morning → auto-advance |

### Files changed

- [`src/game/state/models.py`](../src/game/state/models.py):
  - Add `PhaseClock` Pydantic model.
  - Add `phase_clock: PhaseClock` to `GameState`. Default to `PhaseClock(phase=MORNING, budget_minutes=120)` for new games.
  - Bump `SCHEMA_VERSION` to 16.
- [`src/game/engine/phases.py`](../src/game/engine/phases.py):
  - Add `PHASE_BUDGETS: dict[Phase, int]` constant mapping phase → minutes.
  - Modify `advance_phase(state)` to also reset `phase_clock` to the new phase's budget.
- [`src/game/engine/time_budget.py`](../src/game/engine/time_budget.py) (new):
  - `ACTION_TIME_COST: dict[ActionKind, int]` constant.
  - `deduct_time(state, action) -> int` returns the cost deducted.
  - `check_auto_advance(state) -> bool` returns True if budget expired.
- [`src/game/engine/turn.py`](../src/game/engine/turn.py):
  - After applying mechanical result, call `deduct_time(state, action)`.
  - After Villa Orchestrator + background dialogue runs, call `check_auto_advance`. If True, call `advance_phase` and mark the trace `auto_advance: True`.
- [`src/game/state/trace.py`](../src/game/state/trace.py): `TurnTrace` gains `auto_advance: bool = False` and `phase_clock_snapshot: PhaseClock`. Hash-included.
- [`src/game/cli/commands/play_render.py`](../src/game/cli/commands/play_render.py):
  - State render includes `Time remaining: {n} min`.
  - When `remaining ≤ 20`: print warning line.
  - When auto-advance fires: print `(Time passes. → next phase.)`.
- [`src/game/reporting/html_blocks.py`](../src/game/reporting/html_blocks.py): Each turn card shows time elapsed/remaining. Auto-advance turns get a small "⏰" marker.
- [`src/game/eval/playthrough.py`](../src/game/eval/playthrough.py): Add `time_expired_advance_observed` assertion, `phase_action_count_reasonable` assertion. Aggregate stat: `auto_advances_total`, `avg_actions_per_phase`.

### Acceptance criteria

- [ ] `make qa` green.
- [ ] `make test-llm` green.
- [ ] A player who picks `START_CONVERSATION` 6 times in a row in MORNING phase sees auto-advance fire (6 × 20 = 120 min).
- [ ] Each turn shows the time remaining count.
- [ ] CHALLENGE phase auto-advances within 1 turn (budget = 0).
- [ ] TEXT phase auto-advances after 1-2 actions (budget = 30, but most actions cost ≥ 5).
- [ ] EVENING phase has 60 min — ceremony fires, brief post-window for chats.
- [ ] Scenario fixture `time-budget-expiry.yaml` deterministic hash matches.
- [ ] New eval assertions pass on a real-LLM playthrough.

### Anti-goals

- ❌ No variable time costs based on archetype or stats. Cost table is fixed.
- ❌ No "time-buy" mechanic where player can spend stats to gain extra minutes.
- ❌ No phase-skip slash command — auto-advance is the only path beyond manual `ADVANCE_PHASE`.
- ❌ No new agents.

---

## Phase H8.2 — NPC Autonomy (Summoning + Arrival Rolls)

**Scope.** Villa Orchestrator can pull NPCs out of conversations (player or NPC-NPC). When an NPC arrives at the player's location during an active conversation, the engine rolls for interruption and pull-away independently. Prompt updated.

**Changes.**

### New files

| File | Purpose |
|---|---|
| `src/game/engine/arrival_rolls.py` | Roll logic for `interruption_chance` and `pull_chance` |
| `tests/engine/test_arrival_rolls.py` | Unit tests for both rolls |
| `tests/engine/test_npc_summoned.py` | Unit tests for the summoning flow |
| `tests/scenarios/fixtures/npc-summoned-exit.yaml` | Scenario: orchestrator summons player's target mid-convo |
| `tests/scenarios/fixtures/arrival-roll-interrupt.yaml` | Scenario: NPC arrives, interruption roll hits |

### Files changed

- [`src/game/state/models.py`](../src/game/state/models.py):
  - Add `NPCSummon` Pydantic model.
  - Add `arrival_rolls: list[ArrivalRoll] = []` field on `TurnTrace` and on `TurnResult` (for visibility). `ArrivalRoll` records `arriving_npc_id`, `interruption_chance`, `interruption_rolled`, `interruption_hit`, `pull_chance`, `pull_rolled`, `pull_hit`.
- [`src/game/agents/villa_orchestrator.py`](../src/game/agents/villa_orchestrator.py):
  - Extend `VillaUpdate` to include `npc_summoned_elsewhere: list[NPCSummon] = []`.
- [`src/game/agents/prompts/villa_orchestrator.md`](../src/game/agents/prompts/villa_orchestrator.md): Claude updates the prompt to describe the new `npc_summoned_elsewhere` output and when to fire it. Codex installs verbatim per R17.
- [`src/game/engine/villa.py`](../src/game/engine/villa.py):
  - `validate_villa_update` validates each `NPCSummon`: npc must be at the from_conversation's location, conversation must exist and be open, target_location must be a real Location, npc must be a participant.
  - `apply_villa_update` processes summoning: closes the named conversation with `reason: "npc_summoned_elsewhere"`, moves the NPC, runs Curator on the closed convo.
- [`src/game/engine/arrival_rolls.py`](../src/game/engine/arrival_rolls.py) (new):
  - `interruption_chance(state, arriving_npc) -> int`
  - `pull_chance(state, arriving_npc, target_id) -> int`
  - `roll_arrival(state, arriving_npc, rng) -> ArrivalRoll`
  - Integrates with `engine/turn.py`: after movements apply, for each NPC that just arrived at the player's location while the player has an active conversation, roll both. Hits queue events for the next turn (interruption pending or summon pending).
- [`src/game/engine/turn.py`](../src/game/engine/turn.py): Calls arrival rolls after orchestrator applies movements. If interruption hits, sets `state.active_conversation.pending_interruption`. If pull hits, sets a `state.pending_pull_attempt` field that the next orchestrator turn can act on (by emitting an `NPCSummon` for the targeted NPC).
- [`src/game/engine/conversation.py`](../src/game/engine/conversation.py): `close_conversation` accepts `"npc_summoned_elsewhere"` as a reason. `departure_probability` extended with: avoidant attachment +10 after deep tag, anxious attachment +8 after recent miss, secure attachment unchanged. Big 5 personality factors land here.
- [`src/game/agents/islander_voice.py`](../src/game/agents/islander_voice.py): When `intent_kind == "summoned_exit"`, the Islander Voice generates a brief in-voice goodbye that references *why* they're leaving (drawn from `NPCSummon.reason`). The existing prompt already handles ad-hoc intent kinds; the context block passes the reason.
- [`src/game/cli/commands/play_render.py`](../src/game/cli/commands/play_render.py):
  - Renders the goodbye exchange when summoned.
  - Each turn's villa update prints any arrival rolls: `Aisha arrived. Interruption roll: 38/50 → miss. Pull roll: 41/35 → hit.`
- [`src/game/reporting/html_blocks.py`](../src/game/reporting/html_blocks.py): Arrival rolls get their own card style.
- [`src/game/eval/playthrough.py`](../src/game/eval/playthrough.py): Add `npc_initiated_exit_observed` assertion (any conversation closed with `npc_left` or `npc_summoned_elsewhere`), `npc_arrival_rolls_observed` assertion. Aggregate stats: `arrival_rolls_total`, `arrival_interrupt_hits`, `arrival_pull_hits`, `npc_summoned_total`.

### Acceptance criteria

- [ ] `make qa` green.
- [ ] `make test-llm` green.
- [ ] When an NPC arrives at the player's location while the player is in an active conversation, the trace records an `ArrivalRoll` with both chances and roll outcomes.
- [ ] On an interruption hit, the next turn's wheel shows the three interruption-handling options (existing G8 mechanics).
- [ ] On a pull hit, the next orchestrator turn issues an `NPCSummon` and the player's target leaves the conversation with a brief in-voice goodbye.
- [ ] The closed conversation's Curator output records `npc_summoned_elsewhere` as the reason.
- [ ] `departure_probability` now incorporates attachment style (avoidant + deep tag adds +10, etc.).
- [ ] Scenario fixtures `npc-summoned-exit.yaml` and `arrival-roll-interrupt.yaml` replay to known hashes.
- [ ] New eval assertions pass on a real-LLM playthrough.

### Anti-goals

- ❌ No NPC-initiated re-entry into the same conversation. Once an NPC is summoned out, they don't return to that conversation in the same phase.
- ❌ No player override of arrival rolls. The math is the math.
- ❌ No double-counting: one ArrivalRoll per NPC per arrival. If they move away and come back, that's a new arrival.
- ❌ No prompt edits beyond the villa_orchestrator update Claude writes.

---

## Phase H8.3 — Eval Pacing + Test Performance

**Scope.** Add pacing assertions to the eval suite. Profile and speed up the pytest run via parallelism, session-scoped content loading, lazy LLM client construction.

**Changes.**

### New files

| File | Purpose |
|---|---|
| `tests/conftest.py` (modify) | Add session-scoped `content_index` fixture. Existing fixtures rewritten to consume it. |
| `docs/qa-strategy.md` (modify) | Document the new pacing assertions and the test-perf changes. |

### Files changed

- [`pyproject.toml`](../pyproject.toml): Add `pytest-xdist` to dev dependencies.
- [`Makefile`](../Makefile): `test` target becomes `uv run pytest -m "not llm" -n auto`. `test-llm` stays serial (the LLM tests share rate-limited resources). Add `test-fast` target that runs only the engine unit tests in parallel for ultra-quick iteration.
- [`src/game/agents/islander_voice.py`](../src/game/agents/islander_voice.py): `OpenAI()` client construction moves from `__init__` to a `@cached_property` so non-LLM paths don't construct it.
- [`src/game/agents/contextual_options.py`](../src/game/agents/contextual_options.py): Same lazy client construction.
- [`src/game/agents/event_narrator.py`](../src/game/agents/event_narrator.py): Same.
- [`src/game/agents/conversation_curator.py`](../src/game/agents/conversation_curator.py): Same.
- [`src/game/agents/villa_orchestrator.py`](../src/game/agents/villa_orchestrator.py): Same.
- [`src/game/agents/background_dialogue.py`](../src/game/agents/background_dialogue.py): Same.
- [`src/game/agents/player_autopilot.py`](../src/game/agents/player_autopilot.py): Same.
- [`tests/conftest.py`](../tests/conftest.py):
  - Session-scoped fixture `content_index` returns one loaded `ContentIndex`.
  - Existing `load_fixture_snapshot` continues to work.
- [`src/game/eval/playthrough.py`](../src/game/eval/playthrough.py): Add the five new pacing assertions (see Architectural Decisions table). New aggregate stats: `avg_actions_per_phase`, `auto_advances_total`, `npc_summoned_total`.

### Acceptance criteria

- [ ] `make qa` green.
- [ ] `make test` runs in under 30 seconds on a typical dev machine (was several minutes).
- [ ] `pytest --durations=20` shows no individual test taking longer than 2 seconds.
- [ ] `pytest -n auto` runs tests in parallel without flakiness.
- [ ] Non-LLM tests do not import `openai` or construct OpenAI clients.
- [ ] All five new pacing assertions exist and have positive + negative unit tests in `tests/eval/test_playthrough.py`.
- [ ] All five pacing assertions pass on a fresh real-LLM playthrough generated with H8.1 + H8.2 in place.

### Anti-goals

- ❌ No reducing test coverage to make the suite faster. We parallelize, we don't delete.
- ❌ No new test runner. `pytest` remains.
- ❌ No LLM judge in the eval layer. Claude reviews raw aggregate stats and per-assertion pass/fail.

---

## Prompt update for H8.2

I (Claude) update [`villa_orchestrator.md`](../src/game/agents/prompts/villa_orchestrator.md) to add a new section after the existing `## Hard rules` block. Pre-written here so Codex installs verbatim during H8.2:

```markdown
## NPC summoning (pulling out of conversations)

You may pull an NPC out of any active conversation — the player's conversation or any NPC-NPC conversation — via the `npc_summoned_elsewhere` output field. Use this when an Islander has a strong reason to leave where they are.

Each `NPCSummon`:

- `npc_id` — the Islander leaving.
- `from_conversation_id` — the conversation they're leaving. Must be currently active.
- `reason` — one of: `chemistry_partner_arrived`, `friend_needs_them`, `drama_pull`, `needs_space`, `phase_pressure`.
- `target_location` — where they're going. Must be different from their current location.

### When to fire a summon

- **`chemistry_partner_arrived`** — an islander the NPC has high chemistry with just walked into a different location, and the NPC is currently with someone they don't share that chemistry with.
- **`friend_needs_them`** — an NPC the holder has a strong friendship memory with appears upset or in drama elsewhere.
- **`drama_pull`** — the NPC just heard or witnessed something gossip-worthy and wants to share it with someone else.
- **`needs_space`** — the NPC has been in a deep or vulnerable exchange for multiple exchanges and (per their personality) wants to step away. Avoidant attachment especially.
- **`phase_pressure`** — the phase clock is close to expiry and the NPC has somewhere they need to be before it ends.

### Limits

- At most **one summon per turn**. Use sparingly. Most turns have none.
- Do not summon the player. The player ends their own conversations.
- Do not summon an NPC and continue their conversation in the same turn. Pick one.
- Do not summon someone you also moved this turn. Moves are for off-screen-to-off-screen drift; summons are for in-conversation extraction.
```

No other prompt changes. The new `summoned_exit` intent kind in Islander Voice is handled by the existing ad-hoc intent fallback in `islander_voice_context`.

---

## Tests by sub-phase

### H8.1 — Time Budget tests

`tests/engine/test_time_budget.py`:
- `test_phase_clock_initialized_to_phase_budget`
- `test_deduct_time_subtracts_action_cost`
- `test_phase_clock_remaining_caps_at_zero`
- `test_check_auto_advance_when_expired`
- `test_check_auto_advance_when_remaining`
- `test_run_turn_auto_advances_when_budget_expires`
- `test_run_turn_records_auto_advance_flag`
- `test_morning_six_talks_triggers_auto_advance`
- `test_challenge_phase_auto_advances_immediately`
- `test_text_phase_auto_advances_after_brief_actions`
- `test_phase_advance_resets_clock`
- `test_phase_clock_in_state_hash`

### H8.2 — NPC autonomy tests

`tests/engine/test_arrival_rolls.py`:
- `test_interruption_chance_includes_chemistry_with_player`
- `test_interruption_chance_includes_gossip_memory_count`
- `test_interruption_chance_includes_jealousy_modifier`
- `test_interruption_chance_clamped_5_75`
- `test_pull_chance_includes_chemistry_with_target`
- `test_pull_chance_subtracts_couple_strength`
- `test_pull_chance_clamped_3_60`
- `test_roll_arrival_records_full_breakdown`
- `test_arrival_roll_only_fires_when_player_in_conversation`
- `test_arrival_roll_only_fires_when_npc_just_arrived`

`tests/engine/test_npc_summoned.py`:
- `test_villa_update_validates_summon_npc_in_named_conversation`
- `test_villa_update_validates_summon_target_location_real`
- `test_apply_summon_closes_player_conversation`
- `test_apply_summon_closes_npc_npc_conversation`
- `test_apply_summon_runs_curator`
- `test_apply_summon_moves_npc_to_target_location`
- `test_summoned_exit_intent_kind_handled_by_voice_context`
- `test_departure_probability_increases_for_avoidant_after_deep`
- `test_departure_probability_increases_for_anxious_after_miss`

### H8.3 — Eval pacing tests

`tests/eval/test_playthrough.py`:
- `test_phase_action_count_reasonable_passes_with_balanced_trace`
- `test_phase_action_count_reasonable_fails_with_30_actions_in_one_phase`
- `test_npc_initiated_exit_observed_passes_with_summoned_close`
- `test_npc_initiated_exit_observed_fails_with_only_player_exits`
- `test_day_progression_reasonable_passes_at_day_5`
- `test_day_progression_reasonable_fails_at_day_2`
- `test_time_expired_advance_observed_passes_when_auto_advance_in_trace`
- `test_npc_arrival_rolls_observed_passes_with_two_rolls`

### Performance tests

`tests/conftest_test.py` (meta-test to verify performance changes):
- `test_session_scoped_content_index_used_by_default`
- `test_no_openai_imports_in_non_llm_tests`
- `test_pytest_xdist_available`

---

## Scenario fixtures

- `time-budget-expiry.yaml` — Player picks 6 × START_CONVERSATION on day 1 morning. The 6th triggers auto-advance. Locked hash.
- `npc-summoned-exit.yaml` — Player is in conversation with Maya. Orchestrator (mocked) emits NPCSummon for Maya. Conversation closes with reason `npc_summoned_elsewhere`. Locked hash.
- `arrival-roll-interrupt.yaml` — Player in conversation with Chloe. Aisha arrives. Arrival roll hits interruption. Next turn shows interruption options. Locked hash.

---

## Acceptance criteria for Phase H8 overall

After all three sub-phases commit:

- [ ] `make qa` green at each commit.
- [ ] `make test` finishes in under 30 seconds.
- [ ] `make play` shows time remaining per turn and auto-advances when the budget expires.
- [ ] In a real-LLM playthrough, at least one NPC leaves a conversation on their own initiative (visible in trace as `npc_summoned_elsewhere` or `npc_left`).
- [ ] In a real-LLM playthrough, at least two arrival rolls are recorded.
- [ ] In a real-LLM playthrough, the average actions-per-phase is ≤ 12.
- [ ] In a real-LLM playthrough, the run reaches at least Day 5 within 150 total turns.
- [ ] The eval dashboard surfaces the new pacing stats prominently.
- [ ] `verify --playthrough` includes the five new assertions and they all pass on a healthy run.

---

## Global anti-goals (H8-specific)

- ❌ No LLM judge agent in the eval layer. Claude reviews raw stats and per-assertion pass/fail.
- ❌ No time budget tuning per archetype, persona, or player choice. Budgets are fixed constants.
- ❌ No new agents. NPC summoning uses the existing Villa Orchestrator output; arrival rolls are deterministic engine math.
- ❌ No changes to the autopilot prompt or rails — the rails added during H7 stay. H8's auto-advance removes the *need* for most rails, but the rails remain as belt-and-suspenders.
- ❌ No reducing test coverage. Performance comes from parallelism + caching, not deletion.

---

## Done checklist for Codex

H8 ships as three commits. Each follows the standard pre-flight + per-commit checklist from [build-plan-H-index.md](build-plan-H-index.md).

### H8.1 — Time Budget

- [ ] Add `PhaseClock` Pydantic model
- [ ] Add `phase_clock: PhaseClock` to `GameState`, bump `SCHEMA_VERSION`
- [ ] Write `engine/time_budget.py` with cost table and helpers
- [ ] Wire into `engine/turn.py` with auto-advance
- [ ] Update `engine/phases.py` to reset clock on advance
- [ ] Update CLI rendering for time remaining + auto-advance notification
- [ ] Update HTML rendering with time markers
- [ ] Extend `state/trace.py` with `auto_advance` and `phase_clock_snapshot`
- [ ] Regenerate all scenario fixtures
- [ ] Write `test_time_budget.py`
- [ ] Add scenario fixture `time-budget-expiry.yaml`
- [ ] Extend `eval/playthrough.py` with two new assertions
- [ ] Run `make qa`; fix root causes
- [ ] Run `make test-llm`
- [ ] Append to `docs/build-log.md`
- [ ] Commit: `Phase H8.1: time budget per phase`

### H8.2 — NPC Autonomy

- [ ] Wait for Claude's updated `villa_orchestrator.md` prompt (provided in this doc)
- [ ] Install the prompt update verbatim per R17
- [ ] Add `NPCSummon`, extend `VillaUpdate` schema, extend `TurnTrace` with `arrival_rolls`
- [ ] Write `engine/arrival_rolls.py`
- [ ] Update `engine/villa.py` validate + apply for `NPCSummon`
- [ ] Wire into `engine/turn.py` after orchestrator runs
- [ ] Update `engine/conversation.py` to accept `"npc_summoned_elsewhere"` close reason and extend `departure_probability` with attachment factors
- [ ] Update Islander Voice context to handle `summoned_exit` intent kind
- [ ] Update CLI rendering for goodbye exchange + arrival rolls
- [ ] Update HTML rendering for arrival roll cards
- [ ] Regenerate scenario fixtures
- [ ] Write `test_arrival_rolls.py`, `test_npc_summoned.py`
- [ ] Add scenario fixtures `npc-summoned-exit.yaml`, `arrival-roll-interrupt.yaml`
- [ ] Extend `eval/playthrough.py` with two new assertions
- [ ] Add LLM test for orchestrator emitting summons in plausible contexts
- [ ] Run `make qa`; fix root causes
- [ ] Run `make test-llm`
- [ ] Append to `docs/build-log.md`
- [ ] Commit: `Phase H8.2: NPC autonomy and arrival rolls`

### H8.3 — Eval Pacing + Performance

- [ ] Add `pytest-xdist` to dev dependencies
- [ ] Update Makefile `test` target with `-n auto`
- [ ] Add `test-fast` target
- [ ] Add session-scoped `content_index` fixture in `tests/conftest.py`
- [ ] Move OpenAI client construction in every agent to lazy `cached_property`
- [ ] Profile `pytest --durations=20` and document slow tests in build log
- [ ] Verify no `import openai` in test files outside `tests/agents/`
- [ ] Add the three remaining pacing assertions in `eval/playthrough.py` (already added two in H8.1 and H8.2)
- [ ] Write `test_playthrough.py` positive + negative tests for each new assertion
- [ ] Update `docs/qa-strategy.md` to document new assertions and the performance changes
- [ ] Update eval dashboard rendering to surface pacing stats
- [ ] Run `make qa`; verify total wall time ≤ 30 sec
- [ ] Run `make test-llm`
- [ ] Append to `docs/build-log.md`
- [ ] Commit: `Phase H8.3: eval pacing assertions and test perf`

### After all three commit

- [ ] Run one real-LLM autopilot session: `python -m src.game.cli play --autopilot --persona loyal --seed 42 --max-turns 100 --record .game_traces/h8-validation-loyal.json`
- [ ] Run one real-LLM autopilot session: `python -m src.game.cli play --autopilot --persona chaotic --seed 42 --max-turns 100 --record .game_traces/h8-validation-chaotic.json`
- [ ] Verify both with `python -m src.game.cli verify --playthrough <path>`
- [ ] Generate packets for both with `python -m src.game.cli report packet --trace <path> --out review-packet-h8-<persona>`
- [ ] Post both packet paths to the user with assertion counts and observed pacing stats
- [ ] User reviews both packets and confirms days feel paced, NPCs feel autonomous, no loops

---

## What this phase produces

After H8 commits and the validation runs land:

1. The autopilot loop pattern Codex hit is structurally impossible — phases auto-advance.
2. NPCs sometimes leave the player mid-conversation when their personality or context warrants it. The player experiences this as people excusing themselves to talk to others, exactly like the show.
3. Arrival rolls give the social space a real probabilistic layer — not every walk-by is dramatic, but some are.
4. The test suite runs in seconds instead of minutes, so iteration tightens.
5. The eval suite catches not just feature presence but rhythm — pacing regressions surface as red assertions instead of slipping through.

After H8, the H series is structurally complete. The user records one manual session + the two autopilot personas, reviews all three packets, and the decision shifts to Phase I (UI) or Phase J (depth) per the H-index sequencing.
