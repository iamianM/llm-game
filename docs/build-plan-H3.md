# Build Plan: Phase H3 — NPC Personality Depth

Through G8, NPCs differ only by archetype label (sweetheart / joker / friend). The Islander Voice prompt sees archetype prose; mechanical math doesn't. H3 adds Big 5 OCEAN traits, attachment styles, and Type on Paper preferences to each NPC. Compatibility math becomes strategic: figuring out what an NPC likes is a real game layer.

**Design sources:** [03-LLM-Architecture.md § Personality System](../03-LLM-Architecture.md), [02-Core-Mechanics.md § Success Calculation Details](../02-Core-Mechanics.md), [05-Interaction-System.md § Preference Matching](../05-Interaction-System.md).

**Operating contract:** See [build-plan-H-index.md](build-plan-H-index.md).

---

## Architectural Decisions

### Personality model extension

Each `IslanderState` gains four nested objects:

```python
class Big5(BaseModel):
    openness: int = Field(ge=1, le=10)
    conscientiousness: int = Field(ge=1, le=10)
    extraversion: int = Field(ge=1, le=10)
    agreeableness: int = Field(ge=1, le=10)
    neuroticism: int = Field(ge=1, le=10)

class AttachmentStyle(StrEnum):
    SECURE = "secure"
    ANXIOUS = "anxious"
    AVOIDANT = "avoidant"
    FEARFUL = "fearful"

class TypeOnPaper(BaseModel):
    physical_type: str          # short prose, e.g. "tall, athletic, dark features"
    personality_type: list[str] # e.g. ["funny", "confident", "ambitious"]
    values: list[str]           # e.g. ["loyalty", "adventure", "honesty"]
    dealbreakers: list[str]     # e.g. ["arrogance", "laziness", "drama"]

class IslanderState(BaseModel):
    ...
    big5: Big5
    attachment: AttachmentStyle
    type_on_paper: TypeOnPaper
    familiarity_with_player: int = Field(default=0, ge=0, le=100)
```

These exist for **every** non-player islander (including bombshells). Player has no Big 5 — the player is the camera.

### Familiarity stat

`familiarity_with_player` grows with every conversation: +1 per exchange in player conversations the islander participates in, +2 per closed conversation with the player as direct target. Caps at 100. Drives Type on Paper revelations.

### Type on Paper revelations

Type on Paper is hidden by default. Bits of it surface as familiarity grows:

| Familiarity threshold | Reveals |
|---|---|
| 25 | `physical_type` |
| 50 | `personality_type` |
| 75 | `values` |
| 100 | `dealbreakers` |

Revealed bits show up in the player's state view as a known fact. They also feed into the Islander Voice context so the LLM can naturally have the NPC reference their type ("I love how confident you are — that's exactly my thing").

### Compatibility math

The H3 success-chance formula extends the H1-cap formula with a compatibility bonus:

```
chance = base_50
       + (stat × stat_multiplier)
       + (affection ÷ 4)
       + risk_modifier
       + mood_modifier
       + compatibility_bonus
       - dealbreaker_penalty
clamp by RISK_SUCCESS_CAP
```

Where:

- `compatibility_bonus = matches(player, npc.type_on_paper) × 4`, max +20.
- `dealbreaker_penalty = 15 if player has any of npc.dealbreakers else 0`.

A "match" is checked by:

- `physical_type` (player picks at character creation extension): match = +1.
- `personality_type` tag matched against player's archetype starter advantage: match = +1 per tag.
- `values` matched against player's archetype: match = +1 per tag.

Player archetype gets matched against the NPC's Type on Paper at every roll. So with Heartthrob (high charm, "physical type: tall, well-groomed") matching Chloe whose physical_type starts with "warm, kind people" — no physical match, but possibly value-match via shared values.

Dealbreakers are absolute: -15 to chance whenever player exhibits a tagged dealbreaker behavior. Detected from accumulated tags in player's recent action history (e.g. tag `betrayed_partner` from a bold flirt while coupled triggers dealbreaker `disloyalty`).

### Attachment style behavior

Attachment styles modify the deltas applied to relationship math:

| Style | Flirty success | Flirty miss | Deep success | Deep miss |
|---|---|---|---|---|
| Secure | normal | normal | +1 trust bonus | normal |
| Anxious | normal | -3 trust extra | normal | +2 trust bonus |
| Avoidant | -1 chemistry below baseline | normal | -2 trust normalized | normal |
| Fearful | wide swing: +2 or -2 randomly | normal | -1 mood swing | normal |

Encoded in `engine/compatibility.py` as `attachment_delta_modifier(style, intent, success)`. Applied after the base intent delta in `_apply_intent` and `_apply_follow_up`.

### NPC initialization

Cast in `state/models.py` `new_game()` gets fixed Big 5 / attachment / Type on Paper values per NPC:

| NPC | Big 5 (O, C, E, A, N) | Attachment | TypeOnPaper highlights |
|---|---|---|---|
| Chloe | 7, 6, 9, 8, 4 | secure | values warmth, loyalty; dealbreaker arrogance |
| Maya | 8, 5, 9, 5, 6 | anxious | values humor, attention; dealbreaker neglect |
| Liam | 5, 8, 6, 7, 3 | secure | values steadiness, depth; dealbreaker flakiness |
| Aisha (bombshell) | 8, 7, 9, 5, 6 | avoidant | values ambition, edge; dealbreaker neediness |

These are stored as the new game's deterministic default. Future H8+ can layer procedural generation; for H3 they're hardcoded.

### Islander Voice prompt context

The Islander Voice prompt input is extended to include the NPC's Big 5 and attachment style summary. The prompt itself does not change (R17) — the existing context block accepts new fields. The NPC's voice naturally varies because the prompt sees their personality numbers and treats them appropriately.

For revealed Type on Paper bits, the prompt context includes a `known_preferences` block (only the revealed bits) so the LLM can reference them naturally.

---

## Changes by file

### New files

| File | Purpose |
|---|---|
| `src/game/engine/compatibility.py` | Big 5 + attachment + Type on Paper math |
| `tests/engine/test_compatibility.py` | Unit tests for compatibility math |
| `tests/scenarios/fixtures/type-on-paper-reveal.yaml` | Scenario: familiarity grows, reveals fire |

### Files changed

- [`src/game/state/models.py`](../src/game/state/models.py): Add `Big5`, `AttachmentStyle`, `TypeOnPaper`. Extend `IslanderState` with personality + familiarity. Bump `SCHEMA_VERSION`.
- [`src/game/state/models.py`](../src/game/state/models.py) `new_game()`: hardcoded personality table per NPC.
- [`src/game/engine/rules.py`](../src/game/engine/rules.py): success-chance formula extends with compatibility bonus and dealbreaker penalty. Delta application extends with attachment modifier.
- [`src/game/engine/chance.py`](../src/game/engine/chance.py): `ChanceBreakdown` gains `compatibility_bonus`, `dealbreaker_penalty`, `attachment_delta` fields. Math-rendering updated.
- [`src/game/engine/turn.py`](../src/game/engine/turn.py): every closed player-NPC conversation bumps target's `familiarity_with_player` by +2; every exchange in any conversation bumps the visible NPC's familiarity by +1.
- [`src/game/agents/islander_voice.py`](../src/game/agents/islander_voice.py): `IslanderVoiceContext` extends with `big5_summary`, `attachment_style`, `revealed_preferences`. Builder passes them when calling the agent.
- [`src/game/cli/commands/play.py`](../src/game/cli/commands/play.py): when a Type on Paper bit reveals (a state field crosses the threshold), print a one-line notification: `*** Discovered: Chloe values warmth and loyalty. ***`
- [`src/game/cli/commands/play_render.py`](../src/game/cli/commands/play_render.py): `_print_state` shows familiarity per NPC + revealed Type on Paper bits.
- [`src/game/reporting/html_blocks.py`](../src/game/reporting/html_blocks.py): per-turn card shows revealed-this-turn Type on Paper bits prominently.
- [`src/game/eval/playthrough.py`](../src/game/eval/playthrough.py): Add `assert_type_on_paper_revealed_at_least_once`, `assert_compatibility_bonus_observed`.

---

## Acceptance criteria

- [ ] `make qa` green.
- [ ] `make test-llm` green.
- [ ] Each non-player islander has a non-default Big 5 score, attachment style, and Type on Paper at game start.
- [ ] `familiarity_with_player` increments on every conversation interaction.
- [ ] At familiarity 25 the player sees a notification revealing the NPC's physical_type.
- [ ] At familiarity 50 the personality_type reveals.
- [ ] At familiarity 75 the values reveal.
- [ ] At familiarity 100 the dealbreakers reveal.
- [ ] Compatibility bonus appears in the `ChanceBreakdown` for relevant intents (visible in the math block on the report).
- [ ] Dealbreaker penalty subtracts from chance when the player carries a dealbreaker tag.
- [ ] Attachment style affects relationship delta math per the table.
- [ ] Scenario fixture `type-on-paper-reveal.yaml` runs 20+ exchanges and locks a known final hash showing at least one reveal fired.
- [ ] Two new eval assertions pass on a real-LLM playthrough.

---

## Tests

### Engine unit tests (non-LLM)

- `tests/engine/test_compatibility.py`:
  - `test_compatibility_bonus_increases_with_matching_values`
  - `test_compatibility_bonus_capped_at_20`
  - `test_dealbreaker_penalty_applied_when_player_carries_tag`
  - `test_dealbreaker_penalty_not_double_counted`
  - `test_attachment_secure_no_modifier`
  - `test_attachment_anxious_amplifies_miss_trust_loss`
  - `test_attachment_avoidant_reduces_chemistry_growth`
  - `test_attachment_fearful_introduces_swing`
  - `test_familiarity_increments_on_player_conversation`
  - `test_familiarity_increments_on_visible_npc_conversation`
  - `test_familiarity_caps_at_100`
- `tests/engine/test_models.py`:
  - `test_big5_rejects_out_of_range_value`
  - `test_attachment_style_must_be_in_enum`
  - `test_type_on_paper_required_fields`
  - `test_new_game_assigns_personality_per_npc`
- `tests/engine/test_rules.py`:
  - `test_intent_success_chance_includes_compatibility_bonus`
  - `test_intent_success_chance_includes_dealbreaker_penalty`
  - `test_intent_delta_applies_attachment_modifier`

### Scenario fixtures (mock LLM)

- `tests/scenarios/fixtures/type-on-paper-reveal.yaml`: 25 player-NPC exchanges with Chloe; locked hash shows familiarity reaches 50 and personality_type reveals.

---

## Evals (new playthrough assertions)

- `assert_type_on_paper_revealed_at_least_once` — at least one NPC has reached familiarity ≥ 25 by trace end and has at least one Type on Paper bit revealed.
- `assert_compatibility_bonus_observed` — at least one mechanical_result.chance_breakdown.compatibility_bonus > 0 across the trace.

Aggregate stats: `revealed_preference_count` (count of bits revealed across all NPCs).

---

## Anti-goals

- ❌ No procedural NPC generation in H3. Cast personalities are hardcoded. Procedural arrives in a later phase if needed.
- ❌ No player Big 5. The player is the camera, not a character with measured personality.
- ❌ No "personality changes over the run." Big 5 is fixed once set per NPC.
- ❌ No new agents. Compatibility math is algorithmic.
- ❌ No prompt edits (R17). The Islander Voice context block extends; the prompt text does not.

---

## Done checklist for Codex

- [ ] Read [build-plan-H-index.md](build-plan-H-index.md) pre-flight
- [ ] Re-read [03-LLM-Architecture.md](../03-LLM-Architecture.md), [02-Core-Mechanics.md](../02-Core-Mechanics.md), [05-Interaction-System.md](../05-Interaction-System.md)
- [ ] Add `Big5`, `AttachmentStyle`, `TypeOnPaper` Pydantic models
- [ ] Extend `IslanderState` with personality + familiarity
- [ ] Bump `SCHEMA_VERSION`
- [ ] Set hardcoded personality per NPC in `new_game()`
- [ ] Write `engine/compatibility.py`
- [ ] Update `engine/rules.py` and `engine/chance.py` for new chance components
- [ ] Update `engine/turn.py` to increment familiarity correctly
- [ ] Update `agents/islander_voice.py` context block for new fields
- [ ] Update CLI and HTML rendering to surface familiarity and revealed Type on Paper
- [ ] Regenerate scenario fixtures
- [ ] Write the new tests
- [ ] Add scenario fixture `type-on-paper-reveal.yaml`
- [ ] Extend `eval/playthrough.py`
- [ ] Run `make qa`; fix root causes
- [ ] Run `make test-llm`
- [ ] Append to `docs/build-log.md`
- [ ] Commit: `Phase H3: NPC personality depth`
