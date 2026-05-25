# Build Plan: Phase H1 — Win Condition + Character Creation

> Historical build plan. This file is kept for implementation context only.
> Current planning lives in [current-plan.md](current-plan.md).

The current run starts with hardcoded player stats and ends on day 6 with no outcome. The player has no ownership of their character at the beginning and no stakes at the end. H1 fixes both. Pre-game flow gives the player a real character. Day 6 evening fires a final vote ceremony that resolves the entire run into a named outcome.

After H1 the game has a start and an end. Every subsequent phase builds toward making the middle worthwhile.

**Design sources:** [00-Game-Start-And-Setup.md](../00-Game-Start-And-Setup.md), [10-Elimination-System.md § Audience/Public Perception System](../10-Elimination-System.md), [10-Elimination-System.md § Voting and Eliminations](../10-Elimination-System.md), [02-Core-Mechanics.md § Player Stats](../02-Core-Mechanics.md).

**Operating contract:** See [build-plan-H-index.md](build-plan-H-index.md). One commit, `make qa` green, build log appended, R17 honored.

---

## Architectural Decisions

### Player archetypes (H1)

Three starting archetypes, each with a stat bonus and one starter advantage:

| Archetype | Stat bonus | Starter advantage |
|---|---|---|
| **Heartthrob** | charm +3 | Starts with chemistry +5 with one random islander of their gender preference |
| **Class Clown** | banter +3 | Starts at public perception 60 instead of 50 |
| **Loyal Friend** | loyalty +3 | Friendship +5 with all starting islanders |

Each archetype is authored as a content file under `content/player_archetypes/<id>.md` with frontmatter: `id`, `display_name`, `stat_bonus_name`, `stat_bonus_value`, `starter_advantage` (a structured token, see below), and prose body for narration. Content lint validates the schema.

### Stat allocation

Player allocates `30 - stat_bonus_value` points across the five stats. Each stat must end in `[3, 9]`. The archetype bonus is added to the chosen stat after allocation (so total is exactly 30).

Stat allocation runs as a CLI mini-flow before the first day begins. Player sees each stat with a default value, can `+` and `-` until the budget is exhausted and all five are in range. Final confirmation card shows the character (archetype, stats, starter advantage) and an option to reroll.

### Reroll mechanic

Player can reroll exactly once. Rerolling resets the archetype choice and stat allocation back to the start. After reroll is used, the only way back is `/quit` and restart.

### Character creation persistence

The character creation flow is itself recorded as turn 0 entries in the trace. Schema: `agent_commits.character_creation: CharacterCreation | None` for turn 0 only. CharacterCreation contains the archetype id, the stat allocation, and whether a reroll happened.

This means scenario fixtures can pin a character. New action kind: `CREATE_CHARACTER`. Validates that the player has no started game yet. The replay path reuses the recorded character.

### Public perception drives the outcome

Public perception per islander already exists in state ([state/models.py](../src/game/state/models.py)). H1 makes it drive the final outcome:

- **Each day end**, audience scoring runs: each surviving islander's public perception updates based on the day's events (positive moments +1–+3, negative moments -1–-3, drama -1 to subject -2 to instigator, etc.). The math is deterministic algorithmic, not LLM. Each ceremony or interruption already updates perception in G8.
- **Couple audience score** = average of the two partners' public perceptions, plus a couple-strength bonus.
- **End of day** prints a small audience ranking: "Couples ranked: 1. Maya & Liam (78), 2. You & Chloe (72), 3. Marcus & Sophie (60). Single islanders are out of the running."

### Final vote ceremony

Day 6 evening triggers a new ceremony: `final_vote`. Logic in [engine/final_vote.py](../src/game/engine/final_vote.py):

1. Compute final couple ranking by (audience_score + couple_strength_bonus).
2. Top couple wins.
3. Second couple is runner-up.
4. Single islanders are "left single" (not eliminated, just unpartnered at the end).
5. If the player was eliminated earlier in the run, the outcome is already `ELIMINATED` — final vote still fires for narration but the player doesn't have an outcome stake.

### Run outcome enum

New `RunOutcome` enum in [state/models.py](../src/game/state/models.py):

```python
class RunOutcome(StrEnum):
    WON_AS_COUPLE = "won_as_couple"
    RUNNER_UP_COUPLE = "runner_up_couple"
    LEFT_SINGLE = "left_single"
    ELIMINATED = "eliminated"
```

`GameState.outcome: RunOutcome | None = None` set when the final vote fires (or when the player is eliminated mid-run).

### Audience meter visible

Each end-of-phase trace record gains an `audience_snapshot` field showing each couple's audience score and ranking. The CLI prints it after each `advance_phase` turn that ends a day. The HTML report shows it as a small ranking table per day.

---

## Changes by file

### New files

| File | Lines (est) | Purpose |
|---|---|---|
| `src/game/engine/character_creation.py` | ~150 | Pre-game character creation logic, validation, audit trail |
| `src/game/engine/final_vote.py` | ~120 | Final vote ceremony, couple ranking, outcome computation |
| `src/game/engine/audience.py` | ~80 | Audience scoring math, end-of-day ranking computation |
| `content/player_archetypes/heartthrob.md` | ~30 | Archetype frontmatter + prose |
| `content/player_archetypes/class_clown.md` | ~30 | Archetype frontmatter + prose |
| `content/player_archetypes/loyal_friend.md` | ~30 | Archetype frontmatter + prose |
| `tests/engine/test_character_creation.py` | ~120 | Unit tests for character creation flow |
| `tests/engine/test_final_vote.py` | ~150 | Unit tests for final vote and outcome assignment |
| `tests/engine/test_audience.py` | ~80 | Unit tests for audience scoring math |
| `tests/scenarios/fixtures/character-creation.yaml` | ~30 | Scenario: heartthrob with custom stats |
| `tests/scenarios/fixtures/day6-final-vote.yaml` | ~80 | Scenario: run reaches final vote and outcome set |

### Files changed

- [`src/game/state/models.py`](../src/game/state/models.py): Add `RunOutcome` enum. Add `outcome: RunOutcome | None` to GameState. Add `audience_snapshot` to phase-end TurnTrace records. Bump `SCHEMA_VERSION`.
- [`src/game/engine/actions.py`](../src/game/engine/actions.py): Add `CREATE_CHARACTER` action kind. Validation rejects everything else when the game hasn't been created yet.
- [`src/game/engine/turn.py`](../src/game/engine/turn.py): Handle `CREATE_CHARACTER` at turn 0. On day 6 evening advance_phase, fire `final_vote`. Set state.outcome.
- [`src/game/engine/ceremonies.py`](../src/game/engine/ceremonies.py): Add `final_vote_ceremony(state) -> CeremonyEvent`. Player-elimination path also sets `outcome = ELIMINATED`.
- [`src/game/engine/perception.py`](../src/game/engine/perception.py): Add end-of-day audience scoring nudges (algorithmic, not new LLM calls).
- [`src/game/agents/event_narrator.py`](../src/game/agents/event_narrator.py): The Event Narrator handles `final_vote` events with appropriate dramatic prose. No prompt change needed — the existing prompt covers the new event kind via context.
- [`src/game/cli/commands/play.py`](../src/game/cli/commands/play.py): If no character exists at session start, run the character creation flow. Print archetype options, accept selection, accept stat allocation, accept reroll, then begin day 1.
- [`src/game/cli/commands/play_render.py`](../src/game/cli/commands/play_render.py): New helpers for rendering archetype cards, stat allocation interface, character confirmation card, end-of-day audience ranking, final outcome announcement.
- [`src/game/reporting/html_blocks.py`](../src/game/reporting/html_blocks.py): New blocks for character_creation, audience_ranking_per_day, final_outcome.
- [`src/game/eval/playthrough.py`](../src/game/eval/playthrough.py): Add `assert_outcome_assigned` (run ends with a defined outcome, not None) and `assert_audience_ranking_per_day` (audience_snapshot field present in at least one turn per day).
- [`src/game/content/lint.py`](../src/game/content/lint.py): Validate `content/player_archetypes/` — exactly three files, each with required frontmatter fields.
- [`src/game/content/models.py`](../src/game/content/models.py): Add `PlayerArchetype` model.
- [`src/game/content/loader.py`](../src/game/content/loader.py): Load `content/player_archetypes/` into the `ContentIndex`.

---

## Acceptance criteria

Each item is binary and testable.

- [ ] `make qa` green.
- [ ] `make test-llm` green (no new LLM tests in H1 but existing must still pass).
- [ ] `make play` opens with a character creation flow before day 1.
- [ ] Character creation: player can pick exactly one of three archetypes.
- [ ] Character creation: stat allocation respects 30-point budget, each stat in [3, 9].
- [ ] Character creation: player can reroll exactly once.
- [ ] Character creation: a final character card displays before day 1 begins.
- [ ] Scenario fixture `character-creation.yaml` replays to a known hash (mocked LLM).
- [ ] Day 6 evening fires a `final_vote` ceremony.
- [ ] `state.outcome` is set to one of the four `RunOutcome` values when the run ends.
- [ ] If the player wins as a couple, the outcome message names the partner.
- [ ] If the player is eliminated mid-run, `outcome = ELIMINATED` is set immediately.
- [ ] Each end-of-day turn includes an `audience_snapshot` in the trace.
- [ ] CLI prints couple ranking after each end-of-day advance_phase.
- [ ] HTML report shows audience ranking per day and final outcome panel.
- [ ] `verify --playthrough` includes two new assertions: `assert_outcome_assigned` and `assert_audience_ranking_per_day`. Both pass on a fresh real-LLM playthrough.
- [ ] Scenario fixture `day6-final-vote.yaml` runs the full 6 days under mock LLM and assertions confirm `state.outcome` is set.

---

## Tests

### Engine unit tests (non-LLM)

- `tests/engine/test_character_creation.py`:
  - `test_create_character_assigns_archetype`
  - `test_create_character_rejects_invalid_stat_allocation_total`
  - `test_create_character_rejects_stat_out_of_range`
  - `test_create_character_rejects_when_game_already_created`
  - `test_create_character_applies_archetype_bonus`
  - `test_create_character_applies_starter_advantage_heartthrob`
  - `test_create_character_applies_starter_advantage_class_clown`
  - `test_create_character_applies_starter_advantage_loyal_friend`
  - `test_reroll_resets_stats_and_archetype`
  - `test_second_reroll_rejected`
- `tests/engine/test_final_vote.py`:
  - `test_final_vote_assigns_winner_couple_outcome`
  - `test_final_vote_assigns_runner_up_outcome`
  - `test_final_vote_player_left_single_outcome`
  - `test_final_vote_does_not_override_existing_elimination`
  - `test_final_vote_fires_only_on_day_6_evening`
  - `test_final_vote_ties_broken_deterministically_by_rng_fork`
  - `test_final_vote_uses_audience_score_plus_couple_strength`
  - `test_final_vote_emits_ceremony_event`
- `tests/engine/test_audience.py`:
  - `test_audience_snapshot_includes_all_active_couples`
  - `test_audience_snapshot_ranks_by_score_descending`
  - `test_audience_score_combines_avg_perception_and_couple_strength`
  - `test_audience_snapshot_excludes_eliminated_islanders`

### Scenario fixtures (mock LLM)

- `tests/scenarios/fixtures/character-creation.yaml`: pins a Heartthrob with charm 9 / banter 6 / eq 4 / graft 5 / loyalty 6. Assertions hash matches after creation.
- `tests/scenarios/fixtures/day6-final-vote.yaml`: runs through 6 days (mock LLM) and asserts the final state hash includes `outcome`.

### CLI tests

- `tests/cli/test_play.py`:
  - `test_play_runs_character_creation_when_no_character`
  - `test_play_skips_character_creation_when_replaying`
  - `test_play_renders_audience_ranking_at_day_end`
  - `test_play_renders_final_outcome_message`

---

## Evals (new playthrough assertions)

Added to [`src/game/eval/playthrough.py`](../src/game/eval/playthrough.py):

- **`assert_outcome_assigned`** — Final state's `outcome` is not None. Passes iff `state.outcome ∈ RunOutcome`. Without this, the run had no resolution.
- **`assert_audience_ranking_per_day`** — At least one trace turn per day has an `audience_snapshot` populated. Passes iff every day_index in the trace appears in at least one snapshot.

Both are added to the dashboard. The "Aggregate Stats" table gains: `outcome`, `final_audience_rank`. The "Interesting Turns" listing surfaces the final_vote turn and the audience snapshot turn from each day.

---

## Anti-goals

- ❌ No procedural NPC generation in H1. Cast remains Chloe/Maya/Liam + Aisha bombshell. H3 might add more.
- ❌ No new Big 5 / Type on Paper mechanics. Those are H3.
- ❌ No new archetypes beyond the three named. H1 is the minimum viable creation flow.
- ❌ No multiple-stat archetype bonuses. Each archetype bumps exactly one stat.
- ❌ No starter advantage that's hidden — every advantage is visible on the character card.
- ❌ No public perception tuning in this phase (just wiring). Balance tuning happens organically as plays expose issues.
- ❌ No "skip character creation" CLI flag. Every fresh play starts with creation. Replay reads from trace.
- ❌ No prompt edits without user direction (R17).
- ❌ No cost limits or budget caps (per prior decision).

---

## Done checklist for Codex

- [ ] Read [build-plan-H-index.md](build-plan-H-index.md) pre-flight checklist
- [ ] Re-read [00-Game-Start-And-Setup.md](../00-Game-Start-And-Setup.md) and [10-Elimination-System.md](../10-Elimination-System.md)
- [ ] Add `RunOutcome` enum and bump `SCHEMA_VERSION`
- [ ] Add `CREATE_CHARACTER` action kind to `ActionKind`
- [ ] Write `engine/character_creation.py`
- [ ] Write `engine/final_vote.py`
- [ ] Write `engine/audience.py`
- [ ] Author the three `content/player_archetypes/*.md` files
- [ ] Extend `content/lint.py` to validate archetypes
- [ ] Extend `content/models.py` and `content/loader.py` for `PlayerArchetype`
- [ ] Wire character creation into `cli/commands/play.py`
- [ ] Add rendering helpers in `cli/commands/play_render.py`
- [ ] Add HTML blocks to `reporting/html_blocks.py`
- [ ] Update `engine/turn.py` to handle CREATE_CHARACTER and fire final vote on day 6 evening
- [ ] Update `engine/ceremonies.py` to set elimination outcome
- [ ] Update `engine/perception.py` for end-of-day audience scoring
- [ ] Regenerate all scenario fixtures (SCHEMA_VERSION bump → fixture hashes change)
- [ ] Write the new test files listed above
- [ ] Extend `eval/playthrough.py` with the two new assertions
- [ ] Run `make qa`; fix root cause on any failure
- [ ] Run `make test-llm`; existing tests must still pass
- [ ] Append to `docs/build-log.md`
- [ ] Commit: `Phase H1: win condition and character creation`
