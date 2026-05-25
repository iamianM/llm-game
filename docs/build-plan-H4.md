# Build Plan: Phase H4 — Hideaway + Couple Strength

> Historical build plan. This file is kept for implementation context only.
> Current planning lives in [current-plan.md](current-plan.md).

Couples currently exist as a tuple of two ids and a `formed_on_day` date. There's no concept of a couple's *strength* and no reward for investing in one partner. H4 adds Couple Strength as a derived stat and unlocks the Hideaway — a private overnight stay reserved for high-strength couples. Bombshell stealing becomes properly mechanized: a steal succeeds against couple strength, not against vibes.

**Design sources:** [12-Challenges-And-Events.md § The Hideaway](../12-Challenges-And-Events.md), [02-Core-Mechanics.md § Couple Strength](../02-Core-Mechanics.md), [10-Elimination-System.md § Bombshell System](../10-Elimination-System.md).

**Operating contract:** See [build-plan-H-index.md](build-plan-H-index.md).

---

## Architectural Decisions

### Couple Strength as a derived stat

```python
def couple_strength(state, couple) -> int:
    partner_a_rel = relationship_with_player_or_npc(state, couple.partner_a_id, couple.partner_b_id)
    partner_b_rel = relationship_with_player_or_npc(state, couple.partner_b_id, couple.partner_a_id)
    return (partner_a_rel.affection + partner_a_rel.trust + partner_b_rel.affection + partner_b_rel.trust) // 4
```

Computed every time it's needed; not stored. Surfaces in the CLI couple status panel and in HTML reports.

Couple strength of 70+ unlocks Hideaway eligibility. Below 70, the Hideaway option does not appear in evening menus.

### Hideaway as a unique location and intent flavor

Hideaway is a new `Location` enum value: `HIDEAWAY`. Only accessible by invitation when the player and a partner couple has couple strength ≥ 70 and it's an evening phase on day 4, 5, or 6.

When eligible, the player's evening menu gains a `HIDEAWAY` action: `Spend the night in the Hideaway with [partner]`. Picking it transitions:

1. Player and partner move to `HIDEAWAY` location.
2. A special two-exchange conversation flow runs with an intent menu unique to Hideaway: `intimate`, `vulnerable`, `affirm`, `playful`, `exit`.
3. Each exchange uses Islander Voice with `intent_kind` prefixed `hideaway_*`.
4. At the end, big bonuses: chemistry +15, affection +10, trust +10 to the partner.
5. A high-weight memory (weight 9) forms for both player and partner: tagged `hideaway_night`, `intimate`, `committed`.
6. The villa orchestrator is told for the next morning to fire reactions: jealous islanders nudge their public_perception of the couple downward, supportive islanders nudge upward.
7. Hideaway can fire **once per run** — locked after first use.

### Bombshell stealing properly mechanized

Currently a bombshell can target a player's partner during recoupling and the partner can be stolen if the bombshell has higher chemistry. H4 makes this stake real:

```
steal_chance = 50 + (bombshell_chemistry × 3) - couple_strength + (bombshell_archetype_modifier)
clamp [10, 90]
```

If the bombshell's target is in a couple with strength ≥ 70, the player's couple is heavily protected. If the target is in a couple at strength 30 or below, the bombshell likely wins. The Hideaway is the most direct way to push couple strength above 70.

Steal resolution happens at recoupling ceremonies (day 3 and day 5) and is its own roll. Steal success generates ceremony narration and a high-weight memory for everyone present.

### State extensions

```python
class HideawayState(BaseModel):
    used_on_day: int | None = None
    partner_id: str | None = None
    deltas_applied: bool = False

class Couple(BaseModel):
    # existing fields
    formed_on_day: int
    partner_a_id: str
    partner_b_id: str
    # H4 adds:
    has_used_hideaway: bool = False
    last_steal_attempt_chance: int | None = None
```

`GameState` gains `hideaway: HideawayState = HideawayState()`. Bump `SCHEMA_VERSION`.

### Bombshell stealing in ceremonies

`engine/ceremonies.py` recoupling logic extends:

- For each bombshell (or any islander not currently in a couple), check if they want to steal a partner. If yes, target the partner with highest mutual chemistry.
- Run the steal roll. On success: bombshell takes that partner, the abandoned partner is moved to single or eliminated.
- On miss: bombshell stays single (or pairs with a lower-tier match).
- The ceremony event narrates the result. The CLI shows a dramatic "Steal attempted by [bombshell]: [target_partner]" prompt before resolving.

For the player specifically: if a bombshell tries to steal the player's partner, the player gets a brief notification but cannot defend mechanically — the math is the math. The Hideaway is the preemptive defense.

---

## Changes by file

### New files

| File | Purpose |
|---|---|
| `src/game/engine/hideaway.py` | Hideaway invitation logic, exchange flow, deltas |
| `src/game/engine/couples.py` | Couple Strength computation, ranking, steal math |
| `content/hideaway.md` | Hideaway location content (prose mood) |
| `tests/engine/test_hideaway.py` | Unit tests for Hideaway flow |
| `tests/engine/test_couples.py` | Unit tests for couple strength + steal math |
| `tests/scenarios/fixtures/hideaway-night.yaml` | Scenario: player invites partner to Hideaway, deltas apply |

### Files changed

- [`src/game/state/models.py`](../src/game/state/models.py):
  - Add `HIDEAWAY` to `Location` enum.
  - Add `HideawayState`, extend `Couple` with H4 fields.
  - Add `hideaway: HideawayState` to `GameState`. Bump `SCHEMA_VERSION`.
- [`src/game/engine/actions.py`](../src/game/engine/actions.py):
  - Add `HIDEAWAY` action kind for the invitation action.
  - `available_actions` includes HIDEAWAY in evening menus when eligibility met (couple strength ≥ 70, day in {4,5,6}, hideaway unused, player in a couple).
- [`src/game/engine/turn.py`](../src/game/engine/turn.py): Handle `HIDEAWAY` action — calls `engine/hideaway.py` to set up the special conversation, applies the deltas, marks hideaway as used.
- [`src/game/engine/ceremonies.py`](../src/game/engine/ceremonies.py): Recoupling resolves steal attempts. Each bombshell rolls steal chance against couples it can target. Steal results emit a separate `CeremonyEvent` of kind `steal_attempt` (with `success` flag) and `partner_stolen` if successful.
- [`src/game/engine/rules.py`](../src/game/engine/rules.py): `_apply_intent` for `hideaway_*` intent_kinds dispatches to hideaway-specific delta logic.
- [`src/game/agents/islander_voice.py`](../src/game/agents/islander_voice.py): Context block for Hideaway exchanges includes the Hideaway prose flavor from content. No prompt edit needed — the existing prompt handles ad-hoc intent_kinds.
- [`src/game/cli/commands/play.py`](../src/game/cli/commands/play.py): Evening menu shows the Hideaway option when eligible. Hideaway flow is a brief two-exchange interactive sequence.
- [`src/game/cli/commands/play_render.py`](../src/game/cli/commands/play_render.py): Couple status panel shows couple strength for player's couple. Hideaway card renders prominently when entered.
- [`src/game/reporting/html_blocks.py`](../src/game/reporting/html_blocks.py): Couple strength visible per-day; Hideaway turn gets a distinct card style.
- [`src/game/eval/playthrough.py`](../src/game/eval/playthrough.py): Add `assert_couple_strength_visible`, `assert_hideaway_eligibility_observed_when_high_cs`, `assert_steal_attempt_observed_with_bombshell`.

---

## Acceptance criteria

- [ ] `make qa` green.
- [ ] `make test-llm` green.
- [ ] Couple strength is computed and displayed in the CLI couple-status panel and HTML report.
- [ ] When player's couple strength is ≥ 70 and it's evening on day 4-6, the Hideaway option appears in the evening menu.
- [ ] Hideaway is consumable once per run — the option disappears after use.
- [ ] Hideaway applies the chemistry/affection/trust deltas correctly.
- [ ] Hideaway generates a high-weight memory for both player and partner.
- [ ] Recoupling now resolves steal attempts mechanically with a visible roll.
- [ ] Successful steal results in partner-swap + elimination of the abandoned partner.
- [ ] Scenario fixture `hideaway-night.yaml` replays to a known hash showing the Hideaway fired and deltas applied.
- [ ] Three new eval assertions pass on a real-LLM playthrough.

---

## Tests

### Engine unit tests (non-LLM)

- `tests/engine/test_couples.py`:
  - `test_couple_strength_averages_partners_relationships`
  - `test_couple_strength_zero_when_no_relationship`
  - `test_couple_ranking_orders_by_strength_then_perception`
  - `test_steal_chance_includes_chemistry_minus_couple_strength`
  - `test_steal_chance_clamped_to_10_90`
  - `test_steal_success_swaps_partners`
  - `test_steal_failure_keeps_couple_intact`
- `tests/engine/test_hideaway.py`:
  - `test_hideaway_unlocks_at_couple_strength_70`
  - `test_hideaway_locked_below_threshold`
  - `test_hideaway_unavailable_before_day_4`
  - `test_hideaway_unavailable_in_morning_phase`
  - `test_hideaway_consumable_once_per_run`
  - `test_hideaway_applies_correct_deltas`
  - `test_hideaway_creates_high_weight_memory_for_both_partners`
  - `test_hideaway_intent_kinds_dispatch_correctly`

### Scenario fixtures (mock LLM)

- `tests/scenarios/fixtures/hideaway-night.yaml`: locked hash showing Hideaway fired on day 5 evening with player at couple strength 78.

---

## Evals (new playthrough assertions)

- `assert_couple_strength_visible` — at least one trace turn has a `couple_strength` field in its visible_state or audience_snapshot.
- `assert_hideaway_eligibility_observed_when_high_cs` — if the playthrough achieves couple strength ≥ 70, the Hideaway option appeared in at least one menu.
- `assert_steal_attempt_observed_with_bombshell` — at least one bombshell ceremony triggered a `steal_attempt` event in the trace.

Aggregate stats: `max_couple_strength_reached`, `hideaway_used`, `steal_attempts_total`, `steal_successes`.

---

## Anti-goals

- ❌ No repeating Hideaway. Once per run, ever.
- ❌ No "Hideaway for non-couple" path. Player must be in a couple.
- ❌ No procedural Hideaway location variants. One location, one mood, all runs.
- ❌ No defensive mechanic against steal beyond couple strength. The math is the math.
- ❌ No prompt edits (R17).

---

## Done checklist for Codex

- [ ] Read [build-plan-H-index.md](build-plan-H-index.md) pre-flight
- [ ] Re-read [12-Challenges-And-Events.md](../12-Challenges-And-Events.md), [02-Core-Mechanics.md](../02-Core-Mechanics.md), [10-Elimination-System.md](../10-Elimination-System.md)
- [ ] Extend `Location` with `HIDEAWAY`
- [ ] Add `HideawayState`, extend `Couple` model
- [ ] Bump `SCHEMA_VERSION`
- [ ] Author `content/hideaway.md`
- [ ] Write `engine/hideaway.py`
- [ ] Write `engine/couples.py`
- [ ] Update `engine/actions.py` for the HIDEAWAY action availability rules
- [ ] Update `engine/ceremonies.py` for steal resolution
- [ ] Update `engine/rules.py` for hideaway intent dispatch
- [ ] Update Islander Voice context block to include Hideaway flavor
- [ ] Update CLI rendering (couple status panel, Hideaway flow)
- [ ] Update HTML blocks for couple strength and Hideaway cards
- [ ] Regenerate scenario fixtures
- [ ] Write `test_couples.py`, `test_hideaway.py`
- [ ] Add scenario fixture `hideaway-night.yaml`
- [ ] Extend `eval/playthrough.py` with three new assertions
- [ ] Run `make qa`; fix root causes
- [ ] Run `make test-llm`
- [ ] Append to `docs/build-log.md`
- [ ] Commit: `Phase H4: Hideaway and couple strength`
