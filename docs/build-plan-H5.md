# Build Plan: Phase H5 — Casa Amor

> Historical build plan. This file is kept for implementation context only.
> Current planning lives in [current-plan.md](current-plan.md).

Casa Amor is the show's signature mid-run twist: the cast splits boys/girls and gets sent to a second villa with new arrivals. Loyalty is tested. The return ceremony reveals each side's choice simultaneously, producing the season's biggest drama beat. H5 implements the structural mechanic plus enough authored content for one full pass.

**Design sources:** [12-Challenges-And-Events.md § Casa Amor](../12-Challenges-And-Events.md), [10-Elimination-System.md § Bombshell System](../10-Elimination-System.md), [09-Social-Dynamics.md](../09-Social-Dynamics.md).

**Operating contract:** See [build-plan-H-index.md](build-plan-H-index.md). Largest content drop in the H series. Implement it last unless an earlier phase requires a Casa Amor hook.

---

## Architectural Decisions

### Two-villa state

Casa Amor introduces a second villa with its own cast at its own locations. The state model gains a `villa` field on `GameState`:

```python
class VillaName(StrEnum):
    MAIN = "main"
    CASA_AMOR = "casa_amor"

class GameState(BaseModel):
    villa: VillaName = VillaName.MAIN
    casa_amor_state: CasaAmorState | None = None
    ...
```

`CasaAmorState` tracks: separation start day, return day, the new arrivals on each side, the player's decision at return, etc.

### Casa Amor cast

Casa Amor introduces 3 new islanders on each side (6 total). They are content-authored just like the main cast, under `content/casa_amor_cast/`. Each has full personality fields (Big 5, attachment, Type on Paper) per H3.

For v0, hardcode 6 named bombshell islanders. Procedural generation comes later.

### Locations

Casa Amor adds 3 new Location enum values: `CASA_POOL`, `CASA_KITCHEN`, `CASA_TERRACE`. The villa map renders only locations matching the player's current `villa`.

### Phase flow

Casa Amor fires when the Producer text on day 4 morning announces it. Sequence:

1. **Day 4 morning, TEXT phase:** `casa_amor_announce` producer text fires.
2. **Day 4 morning advance:** cast separates. Player's gender goes to Casa Amor. Three new Casa Amor islanders join each side. State `villa = CASA_AMOR`. Original partners remain in `main_villa_partners` snapshot for the return ceremony.
3. **Day 4-5 at Casa Amor:** player interacts with the new cast at Casa Amor locations. Conversations work normally but only with Casa Amor islanders. Background dialogue happens with the Casa Amor cast. Memories form normally.
4. **Day 5 evening, Casa Amor recoupling:** player chooses to return with original partner, return with a Casa Amor islander, or return single.
5. **Day 6 morning:** return ceremony at the main villa. Player's choice is revealed simultaneously with the opposite-gender side's choices. Drama, narration, possible elimination of original partners who got swapped.
6. **Day 6 normal:** play continues to final vote.

### New action: CASA_DECISION

At the Day 5 evening Casa Amor recoupling, the player picks:

- `RETURN_WITH_ORIGINAL` — go back with the original partner. Loyalty +5 with original partner, big public_perception bump for loyalty.
- `RETURN_WITH_NEW_ID:<id>` — go back with a Casa Amor islander. Original partner gets stolen. Heavy public_perception drop for disloyalty.
- `RETURN_SINGLE` — neither. Loyalty bump but no partner.

These are presented as a special ceremony action menu — not the conversation wheel.

### Return ceremony narration

The Event Narrator gets a special context for the return ceremony: both sides' choices simultaneously revealed. The narration covers each couple at a time: "Player returns from Casa Amor with [name]. Original partner [name], who had stayed loyal, watches in [reaction]." Memories form for everyone present at very high weight (9-10).

### Audience impact

Casa Amor outcomes massively affect public perception:

| Outcome | Player perception | Original partner perception |
|---|---|---|
| Returns with original (both stayed loyal) | +10 | +5 |
| Returns with original (original cheated) | +8 (sympathy) | -10 |
| Returns with Casa Amor (original stayed) | -12 (snake) | +8 (sympathy) |
| Returns with Casa Amor (both cheated) | -4 | -4 |
| Returns single | +3 | varies |

This is the biggest perception swing in the run.

---

## Changes by file

### New files

| File | Purpose |
|---|---|
| `src/game/engine/casa_amor.py` | Casa Amor flow: separation, return ceremony, perception updates |
| `content/locations/casa_pool.md` | Casa Amor pool flavor |
| `content/locations/casa_kitchen.md` | Casa Amor kitchen flavor |
| `content/locations/casa_terrace.md` | Casa Amor terrace flavor |
| `content/casa_amor_cast/blake.md` | New islander (m) |
| `content/casa_amor_cast/jordan.md` | New islander (m) |
| `content/casa_amor_cast/marcus.md` | New islander (m) |
| `content/casa_amor_cast/sophie.md` | New islander (f) |
| `content/casa_amor_cast/zara.md` | New islander (f) |
| `content/casa_amor_cast/nia.md` | New islander (f) |
| `content/producer_texts/casa_amor_announce.md` | Producer text for the announcement |
| `tests/engine/test_casa_amor.py` | Unit tests for the flow |
| `tests/scenarios/fixtures/casa-amor-arrive.yaml` | Scenario: day 4 morning casa amor fires |
| `tests/scenarios/fixtures/casa-amor-return.yaml` | Scenario: day 6 return ceremony with cheating outcome |

### Files changed

- [`src/game/state/models.py`](../src/game/state/models.py):
  - Add `VillaName` enum, `CasaAmorState`.
  - Add `CASA_POOL`, `CASA_KITCHEN`, `CASA_TERRACE` to `Location`.
  - Add `villa`, `casa_amor_state` to `GameState`.
  - Bump `SCHEMA_VERSION`.
- [`src/game/engine/actions.py`](../src/game/engine/actions.py):
  - Add `CASA_DECISION` action kind.
  - `available_actions` filters islanders to those in the player's current villa.
  - At Day 5 evening when at Casa Amor, the menu shows ONLY the three CASA_DECISION options.
- [`src/game/engine/turn.py`](../src/game/engine/turn.py):
  - On day 4 morning advance when villa = MAIN, trigger Casa Amor flow.
  - On day 6 morning at MAIN, fire return ceremony.
  - Handle `CASA_DECISION` action.
- [`src/game/engine/casa_amor.py`](../src/game/engine/casa_amor.py):
  - `enter_casa_amor(state)` — splits cast, adds Casa Amor cast, sets state.villa.
  - `return_ceremony(state, decision)` — applies decision, perception updates, eliminations, narration setup.
  - `compute_npc_casa_choices(state)` — algorithmic decisions for NPCs (do their original partners stay loyal? do new Casa Amor islanders pair with stayed-behind islanders?).
- [`src/game/engine/perception.py`](../src/game/engine/perception.py): Handle Casa Amor perception updates per the table.
- [`src/game/engine/villa.py`](../src/game/engine/villa.py): Orchestrator validation extends to reject NPC movements across villas (Casa Amor cast can't move to main, and vice versa).
- [`src/game/agents/villa_orchestrator.py`](../src/game/agents/villa_orchestrator.py): Context now includes the player's current villa. Orchestrator only knows about NPCs in the same villa.
- [`src/game/agents/event_narrator.py`](../src/game/agents/event_narrator.py): Handles new event kinds: `casa_amor_arrival`, `casa_amor_return_reveal`.
- [`src/game/cli/commands/play.py`](../src/game/cli/commands/play.py): At Day 5 evening at Casa Amor, present the CASA_DECISION menu. At Day 6 morning return ceremony, render the simultaneous reveal dramatically.
- [`src/game/cli/commands/play_render.py`](../src/game/cli/commands/play_render.py): Map view at Casa Amor shows Casa Amor locations. Return ceremony rendering.
- [`src/game/reporting/html_blocks.py`](../src/game/reporting/html_blocks.py): Casa Amor splits the timeline visually (a vertical divider showing "← MAIN | CASA AMOR →" with reveal moment as a centerpiece).
- [`src/game/eval/playthrough.py`](../src/game/eval/playthrough.py): Add `assert_casa_amor_phase_observed`, `assert_casa_amor_return_resolved`, `assert_casa_amor_perception_swing`.
- [`src/game/content/lint.py`](../src/game/content/lint.py): Validate `content/casa_amor_cast/` — exactly 6 files, 3 of each gender, with required personality fields.
- [`src/game/content/loader.py`](../src/game/content/loader.py): Load Casa Amor cast.

---

## Acceptance criteria

- [ ] `make qa` green.
- [ ] `make test-llm` green.
- [ ] Day 4 morning: a `casa_amor_announce` text fires.
- [ ] Day 4 morning advance: cast splits. Player ends up at Casa Amor with 3 new opposite-gender islanders + 3 new same-gender islanders.
- [ ] Day 4-5 at Casa Amor: player can interact with the new cast normally (intent wheels, follow-ups, gossip).
- [ ] NPCs left behind at the main villa continue to have their own background conversations (orchestrator runs in both villas independently).
- [ ] Day 5 evening: player gets the three CASA_DECISION options.
- [ ] Day 6 morning return ceremony: choices revealed simultaneously, dramatic Event Narrator output.
- [ ] Perception updates per the table.
- [ ] Scenario fixture `casa-amor-arrive.yaml` replays with locked hash showing Day 4 morning Casa Amor entry.
- [ ] Scenario fixture `casa-amor-return.yaml` replays with locked hash showing Day 6 reveal with a "cheating" choice and perception swing.
- [ ] Three new eval assertions pass.

---

## Tests

### Engine unit tests (non-LLM)

- `tests/engine/test_casa_amor.py`:
  - `test_casa_amor_enter_separates_cast_by_gender`
  - `test_casa_amor_enter_adds_new_islanders`
  - `test_casa_amor_locations_only_visible_at_casa`
  - `test_villa_main_locations_hidden_at_casa`
  - `test_return_with_original_increases_loyalty_perception`
  - `test_return_with_casa_amor_drops_perception_when_original_loyal`
  - `test_return_single_modest_perception_bump`
  - `test_orchestrator_only_sees_same_villa_npcs`
  - `test_npc_casa_choices_deterministic_from_rng`
  - `test_eliminated_islanders_dont_return_to_main`

### Scenario fixtures (mock LLM)

- `tests/scenarios/fixtures/casa-amor-arrive.yaml`: locked hash after Day 4 morning advance.
- `tests/scenarios/fixtures/casa-amor-return.yaml`: locked hash after Day 6 return ceremony.

---

## Evals (new playthrough assertions)

- `assert_casa_amor_phase_observed` — at least one trace turn has `state.villa == "casa_amor"`.
- `assert_casa_amor_return_resolved` — `state.casa_amor_state.player_decision` is set when the run reaches day 6+.
- `assert_casa_amor_perception_swing` — public perception of the player changed by ≥ 6 (absolute) between day 4 morning and day 6 morning.

Aggregate stats: `casa_amor_visited` (bool), `casa_amor_player_decision`, `casa_amor_partners_swapped`.

---

## Anti-goals

- ❌ No procedural Casa Amor cast generation in H5. Six hardcoded islanders only.
- ❌ No "skip Casa Amor" flag for testing. The flow fires on schedule.
- ❌ No Casa Amor extending beyond Day 5 evening. Hard stop at return day 6.
- ❌ No multiple Casa Amor visits in one run.
- ❌ No prompt edits (R17). Existing Islander Voice prompt covers Casa Amor cast since they have full personality fields.

---

## Done checklist for Codex

- [ ] Read [build-plan-H-index.md](build-plan-H-index.md) pre-flight
- [ ] Re-read [12-Challenges-And-Events.md § Casa Amor](../12-Challenges-And-Events.md)
- [ ] Add `VillaName`, `CasaAmorState`, three new locations
- [ ] Bump `SCHEMA_VERSION`
- [ ] Author the 6 Casa Amor cast files
- [ ] Author the 3 Casa Amor location files
- [ ] Author `casa_amor_announce.md` producer text
- [ ] Write `engine/casa_amor.py`
- [ ] Wire phase flow in `engine/turn.py`
- [ ] Add `CASA_DECISION` action handling
- [ ] Update orchestrator to be villa-aware
- [ ] Update Event Narrator context for arrival and return narration
- [ ] Update CLI for Casa Amor map, decision menu, return ceremony
- [ ] Update HTML blocks for Casa Amor split timeline
- [ ] Update content lint + loader
- [ ] Regenerate scenario fixtures
- [ ] Write engine tests
- [ ] Add scenario fixtures `casa-amor-arrive.yaml` and `casa-amor-return.yaml`
- [ ] Extend `eval/playthrough.py` with three new assertions
- [ ] Run `make qa`; fix root causes
- [ ] Run `make test-llm`
- [ ] Append to `docs/build-log.md`
- [ ] Commit: `Phase H5: Casa Amor`
