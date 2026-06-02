# Build Plan: Phase H5 — Flush of Hearts

> Historical build plan. This file is kept for implementation context only.
> Current planning lives in [current-plan.md](current-plan.md).

Flush of Hearts is the show's signature mid-run twist: the cast splits boys/girls and gets sent to a second resort with new arrivals. Loyalty is tested. The return ceremony reveals each side's choice simultaneously, producing the season's biggest drama beat. H5 implements the structural mechanic plus enough authored content for one full pass.

**Design sources:** [12-Challenges-And-Events.md § Flush of Hearts](../12-Challenges-And-Events.md), [10-Elimination-System.md § Heart Throb System](../10-Elimination-System.md), [09-Social-Dynamics.md](../09-Social-Dynamics.md).

**Operating contract:** See [build-plan-H-index.md](build-plan-H-index.md). Largest content drop in the H series. Implement it last unless an earlier phase requires a Flush of Hearts hook.

---

## Architectural Decisions

### Two-resort state

Flush of Hearts introduces a second resort with its own cast at its own locations. The state model gains a `resort` field on `GameState`:

```python
class ResortName(StrEnum):
    MAIN = "main"
    FLUSH_OF_HEARTS = "flush_of_hearts"

class GameState(BaseModel):
    resort: ResortName = ResortName.MAIN
    flush_of_hearts_state: FlushOfHeartsState | None = None
    ...
```

`FlushOfHeartsState` tracks: separation start day, return day, the new arrivals on each side, the player's decision at return, etc.

### Flush of Hearts cast

Flush of Hearts introduces 3 new heartbreakers on each side (6 total). They are content-authored just like the main cast, under `content/flush_of_hearts_cast/`. Each has full personality fields (Big 5, attachment, Type on Paper) per H3.

For v0, hardcode 6 named Heart Throb heartbreakers. Procedural generation comes later.

### Locations

Flush of Hearts adds 3 new Location enum values: `FLUSH_POOL`, `FLUSH_KITCHEN`, `FLUSH_TERRACE`. The resort map renders only locations matching the player's current `resort`.

### Phase flow

Flush of Hearts fires when the Producer text on day 4 morning announces it. Sequence:

1. **Day 4 morning, TEXT phase:** `flush_of_hearts_announce` producer text fires.
2. **Day 4 morning advance:** cast separates. Player's gender goes to Flush of Hearts. Three new Flush of Hearts heartbreakers join each side. State `resort = FLUSH_OF_HEARTS`. Original partners remain in `main_resort_partners` snapshot for the return ceremony.
3. **Day 4-5 at Flush of Hearts:** player interacts with the new cast at Flush of Hearts locations. Conversations work normally but only with Flush of Hearts heartbreakers. Background dialogue happens with the Flush of Hearts cast. Memories form normally.
4. **Day 5 evening, Flush of Hearts Pairing Ceremony:** player chooses to return with original partner, return with a Flush of Hearts heartbreaker, or return single.
5. **Day 6 morning:** return ceremony at the main resort. Player's choice is revealed simultaneously with the opposite-gender side's choices. Drama, narration, possible elimination of original partners who got swapped.
6. **Day 6 normal:** play continues to final vote.

### New action: FLUSH_DECISION

At the Day 5 evening Flush of Hearts Pairing Ceremony, the player picks:

- `RETURN_WITH_ORIGINAL` — go back with the original partner. Loyalty +5 with original partner, big public_perception bump for loyalty.
- `RETURN_WITH_NEW_ID:<id>` — go back with a Flush of Hearts heartbreaker. Original partner gets stolen. Heavy public_perception drop for disloyalty.
- `RETURN_SINGLE` — neither. Loyalty bump but no partner.

These are presented as a special ceremony action menu — not the conversation wheel.

### Return ceremony narration

The Event Narrator gets a special context for the return ceremony: both sides' choices simultaneously revealed. The narration covers each couple at a time: "Player returns from Flush of Hearts with [name]. Original partner [name], who had stayed loyal, watches in [reaction]." Memories form for everyone present at very high weight (9-10).

### Audience impact

Flush of Hearts outcomes massively affect public perception:

| Outcome | Player perception | Original partner perception |
|---|---|---|
| Returns with original (both stayed loyal) | +10 | +5 |
| Returns with original (original cheated) | +8 (sympathy) | -10 |
| Returns with Flush of Hearts (original stayed) | -12 (snake) | +8 (sympathy) |
| Returns with Flush of Hearts (both cheated) | -4 | -4 |
| Returns single | +3 | varies |

This is the biggest perception swing in the run.

---

## Changes by file

### New files

| File | Purpose |
|---|---|
| `src/game/engine/flush_of_hearts.py` | Flush of Hearts flow: separation, return ceremony, perception updates |
| `content/locations/flush_pool.md` | Flush of Hearts pool flavor |
| `content/locations/flush_kitchen.md` | Flush of Hearts kitchen flavor |
| `content/locations/flush_terrace.md` | Flush of Hearts terrace flavor |
| `content/flush_of_hearts_cast/blake.md` | New heartbreaker (m) |
| `content/flush_of_hearts_cast/jordan.md` | New heartbreaker (m) |
| `content/flush_of_hearts_cast/marcus.md` | New heartbreaker (m) |
| `content/flush_of_hearts_cast/sophie.md` | New heartbreaker (f) |
| `content/flush_of_hearts_cast/zara.md` | New heartbreaker (f) |
| `content/flush_of_hearts_cast/nia.md` | New heartbreaker (f) |
| `content/producer_texts/flush_of_hearts_announce.md` | Producer text for the announcement |
| `tests/engine/test_flush_of_hearts.py` | Unit tests for the flow |
| `tests/scenarios/fixtures/flush-of-hearts-arrive.yaml` | Scenario: day 4 morning Flush of Hearts fires |
| `tests/scenarios/fixtures/flush-of-hearts-return.yaml` | Scenario: day 6 return ceremony with cheating outcome |

### Files changed

- [`src/game/state/models.py`](../src/game/state/models.py):
  - Add `ResortName` enum, `FlushOfHeartsState`.
  - Add `FLUSH_POOL`, `FLUSH_KITCHEN`, `FLUSH_TERRACE` to `Location`.
  - Add `resort`, `flush_of_hearts_state` to `GameState`.
  - Bump `SCHEMA_VERSION`.
- [`src/game/engine/actions.py`](../src/game/engine/actions.py):
  - Add `FLUSH_DECISION` action kind.
  - `available_actions` filters heartbreakers to those in the player's current resort.
  - At Day 5 evening when at Flush of Hearts, the menu shows ONLY the three FLUSH_DECISION options.
- [`src/game/engine/turn.py`](../src/game/engine/turn.py):
  - On day 4 morning advance when resort = MAIN, trigger Flush of Hearts flow.
  - On day 6 morning at MAIN, fire return ceremony.
  - Handle `FLUSH_DECISION` action.
- [`src/game/engine/flush_of_hearts.py`](../src/game/engine/flush_of_hearts.py):
  - `enter_flush_of_hearts(state)` — splits cast, adds Flush of Hearts cast, sets state.resort.
  - `return_ceremony(state, decision)` — applies decision, perception updates, eliminations, narration setup.
  - `compute_npc_flush_choices(state)` — algorithmic decisions for NPCs (do their original partners stay loyal? do new Flush of Hearts heartbreakers pair with stayed-behind heartbreakers?).
- [`src/game/engine/perception.py`](../src/game/engine/perception.py): Handle Flush of Hearts perception updates per the table.
- [`src/game/engine/resort.py`](../src/game/engine/resort.py): Orchestrator validation extends to reject NPC movements across resorts (Flush of Hearts cast can't move to main, and vice versa).
- [`src/game/agents/resort_orchestrator.py`](../src/game/agents/resort_orchestrator.py): Context now includes the player's current resort. Orchestrator only knows about NPCs in the same resort.
- [`src/game/agents/event_narrator.py`](../src/game/agents/event_narrator.py): Handles new event kinds: `flush_of_hearts_arrival`, `flush_of_hearts_return_reveal`.
- [`src/game/cli/commands/play.py`](../src/game/cli/commands/play.py): At Day 5 evening at Flush of Hearts, present the FLUSH_DECISION menu. At Day 6 morning return ceremony, render the simultaneous reveal dramatically.
- [`src/game/cli/commands/play_render.py`](../src/game/cli/commands/play_render.py): Map view at Flush of Hearts shows Flush of Hearts locations. Return ceremony rendering.
- [`src/game/reporting/html_blocks.py`](../src/game/reporting/html_blocks.py): Flush of Hearts splits the timeline visually (a vertical divider showing "← MAIN | FLUSH OF HEARTS →" with reveal moment as a centerpiece).
- [`src/game/eval/playthrough.py`](../src/game/eval/playthrough.py): Add `assert_flush_of_hearts_phase_observed`, `assert_flush_of_hearts_return_resolved`, `assert_flush_of_hearts_perception_swing`.
- [`src/game/content/lint.py`](../src/game/content/lint.py): Validate `content/flush_of_hearts_cast/` — exactly 6 files, 3 of each gender, with required personality fields.
- [`src/game/content/loader.py`](../src/game/content/loader.py): Load Flush of Hearts cast.

---

## Acceptance criteria

- [ ] `make qa` green.
- [ ] `make test-llm` green.
- [ ] Day 4 morning: a `flush_of_hearts_announce` text fires.
- [ ] Day 4 morning advance: cast splits. Player ends up at Flush of Hearts with 3 new opposite-gender heartbreakers + 3 new same-gender heartbreakers.
- [ ] Day 4-5 at Flush of Hearts: player can interact with the new cast normally (intent wheels, follow-ups, gossip).
- [ ] NPCs left behind at the main resort continue to have their own background conversations (orchestrator runs in both resorts independently).
- [ ] Day 5 evening: player gets the three FLUSH_DECISION options.
- [ ] Day 6 morning return ceremony: choices revealed simultaneously, dramatic Event Narrator output.
- [ ] Perception updates per the table.
- [ ] Scenario fixture `flush-of-hearts-arrive.yaml` replays with locked hash showing Day 4 morning Flush of Hearts entry.
- [ ] Scenario fixture `flush-of-hearts-return.yaml` replays with locked hash showing Day 6 reveal with a "cheating" choice and perception swing.
- [ ] Three new eval assertions pass.

---

## Tests

### Engine unit tests (non-LLM)

- `tests/engine/test_flush_of_hearts.py`:
  - `test_flush_of_hearts_enter_separates_cast_by_gender`
  - `test_flush_of_hearts_enter_adds_new_heartbreakers`
  - `test_flush_of_hearts_locations_only_visible_at_flush`
  - `test_resort_main_locations_hidden_at_flush`
  - `test_return_with_original_increases_loyalty_perception`
  - `test_return_with_flush_of_hearts_drops_perception_when_original_loyal`
  - `test_return_single_modest_perception_bump`
  - `test_orchestrator_only_sees_same_resort_npcs`
  - `test_npc_flush_choices_deterministic_from_rng`
  - `test_eliminated_heartbreakers_dont_return_to_main`

### Scenario fixtures (mock LLM)

- `tests/scenarios/fixtures/flush-of-hearts-arrive.yaml`: locked hash after Day 4 morning advance.
- `tests/scenarios/fixtures/flush-of-hearts-return.yaml`: locked hash after Day 6 return ceremony.

---

## Evals (new playthrough assertions)

- `assert_flush_of_hearts_phase_observed` — at least one trace turn has `state.resort == "flush_of_hearts"`.
- `assert_flush_of_hearts_return_resolved` — `state.flush_of_hearts_state.player_decision` is set when the run reaches day 6+.
- `assert_flush_of_hearts_perception_swing` — public perception of the player changed by ≥ 6 (absolute) between day 4 morning and day 6 morning.

Aggregate stats: `flush_of_hearts_visited` (bool), `flush_of_hearts_player_decision`, `flush_of_hearts_partners_swapped`.

---

## Anti-goals

- ❌ No procedural Flush of Hearts cast generation in H5. Six hardcoded heartbreakers only.
- ❌ No "skip Flush of Hearts" flag for testing. The flow fires on schedule.
- ❌ No Flush of Hearts extending beyond Day 5 evening. Hard stop at return day 6.
- ❌ No multiple Flush of Hearts visits in one run.
- ❌ No prompt edits (R17). Existing Heartbreaker Voice prompt covers Flush of Hearts cast since they have full personality fields.

---

## Done checklist for Codex

- [ ] Read [build-plan-H-index.md](build-plan-H-index.md) pre-flight
- [ ] Re-read [12-Challenges-And-Events.md § Flush of Hearts](../12-Challenges-And-Events.md)
- [ ] Add `ResortName`, `FlushOfHeartsState`, three new locations
- [ ] Bump `SCHEMA_VERSION`
- [ ] Author the 6 Flush of Hearts cast files
- [ ] Author the 3 Flush of Hearts location files
- [ ] Author `flush_of_hearts_announce.md` producer text
- [ ] Write `engine/flush_of_hearts.py`
- [ ] Wire phase flow in `engine/turn.py`
- [ ] Add `FLUSH_DECISION` action handling
- [ ] Update orchestrator to be resort-aware
- [ ] Update Event Narrator context for arrival and return narration
- [ ] Update CLI for Flush of Hearts map, decision menu, return ceremony
- [ ] Update HTML blocks for Flush of Hearts split timeline
- [ ] Update content lint + loader
- [ ] Regenerate scenario fixtures
- [ ] Write engine tests
- [ ] Add scenario fixtures `flush-of-hearts-arrive.yaml` and `flush-of-hearts-return.yaml`
- [ ] Extend `eval/playthrough.py` with three new assertions
- [ ] Run `make qa`; fix root causes
- [ ] Run `make test-llm`
- [ ] Append to `docs/build-log.md`
- [ ] Commit: `Phase H5: Flush of Hearts`
