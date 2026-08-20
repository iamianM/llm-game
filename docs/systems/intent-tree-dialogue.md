# Intent-Tree Dialogue System

**Status:** active spec.
**Owner:** Claude (implementing); Ian (signed off on design).
**Base commit:** `8d45f47` scene-dialogue: hydrate Live LLM toggle from localStorage post-mount.

This doc captures the locked design for how the player picks what to say in conversations. Read it with [scene-dialogue.md](scene-dialogue.md): the scene-dialogue system delivers the visuals, while this document defines the choice layer inside it.

---

## 0. One-paragraph product description

Across every conversation surface — Day-1 intros, free-time chats, in-conversation follow-ups — the player picks **intents** (categories of approach), not pre-written lines. The four top-level categories are **Friendly · Flirty · Deep · Banter**. As relationship strength grows, deeper categories and more specific sub-intents unlock. Categories the player hasn't unlocked yet still appear, dimmed, with a one-line hint of how to open them ("Get closer to her first"). After the player picks an intent, **two LLM calls fire in sequence**: a player-voice agent writes the player's line (anchored in memories + relationship history + the chosen intent), then an NPC-voice agent writes the reply (grounded in the exact player line that just landed). Each line surfaces as its own bubble, with a tap between, so the player reads what they actually said before the NPC reacts. Mock mode templates both for deterministic dev.

---

## 1. Decisions locked

| # | Decision | Value | Rationale |
|---|----------|-------|-----------|
| 1 | What the player picks | **Intents, not lines.** Engine receives an `intent_id`; UI never displays pre-written player text on the buttons. | Engine binds mechanical deltas (`affection +2`, `chemistry -1`) to intent IDs. Pre-written previews diverged from what the LLM actually wrote, breaking the player's expectation. |
| 2 | Top-level categories | **Friendly · Flirty · Deep · Banter.** Four, always rendered, no more. | Cognitive load. Maps cleanly to the affection-unlock progression already in `data/balance/intents.yaml`. |
| 3 | Locked-category UX | **Plan B: always visible, dimmed with hint.** Locked categories show a one-line unlock condition. | Visible-but-locked dial telegraphs the engagement loop ("more opens up if you keep going"). |
| 4 | Tree depth per context | Intros: flat (4 leaves). Free-time conversation start: 2 levels (category → sub-intent). In-conversation follow-ups: flat with category chips. Minigames: no tree (literal answers). | Intros are 4 dynamics that ARE the leaves. Free-time has 3-9 sub-intents grouped by category. In-conversation menus are already engine-pruned to 3-4. |
| 5 | Two-step bubble flow | Click intent → player bubble appears with generated line → tap → NPC bubble appears. | Lets the player read what they actually said before the reaction lands. Decouples player-voice and NPC-voice prompts so each has a focused job. |
| 6 | LLM call shape | **Two sequential agents per turn:** `player_voice` then `npc_voice`. NPC sees the verbatim player line. | Today's single `heartbreaker_voice` writes both lines from intent alone — NPC reply is grounded in intent, not in *what the player said*. Splitting fixes that. |
| 7 | Greetings | **Dynamic, parallel pre-gen.** New `npc_greeter` agent fires N concurrent calls (one per heartbreaker) at intros start. Mock mode keeps templates. | Static templates feel canned. Parallel generation puts wall-time at ~3-5s for 8 NPCs. |
| 8 | Cost in live mode | 2 LLM calls per conversation turn (was 1). Intros add 8 parallel greeter calls at start. Free-time and follow-ups the same. | Acceptable — live is opt-in, mock is unchanged. |

---

## 2. Intent vocabulary

### Top-level categories

| Category | Description | Unlock | Color in UI |
|----------|-------------|--------|-------------|
| Friendly | Warmth, support, casual chat. Low-risk. | Always | warm-cream |
| Flirty | Teasing, attraction, escalation. | Affection ≥ 20 | accent-coral |
| Deep | Vulnerability, life, future. | Affection ≥ 40 | gold-soft |
| Banter | Jokes, deflection, riffing. | Always | ink-on-dark |

The unlock thresholds live in `data/balance/intents.yaml` as `unlock_affection` per intent. The category's effective unlock = the lowest unlock_affection across its members.

### Sub-intents per category

Sourced from `data/balance/intents.yaml`. **Friendly** and **Banter** are always available; **Flirty** opens at affection 20; **Deep** opens at affection 40. Within a category, individual sub-intents have their own thresholds.

| Category | Sub-intent | unlock_affection |
|----------|-----------|------------------|
| Friendly | `friendly_ask_feelings` — "Ask how they're feeling" | 0 |
| Friendly | `friendly_chat_resort` — "Chat about the resort" | 0 |
| Friendly | `friendly_compliment_personality` — "Compliment their personality" | 0 |
| Flirty | `flirty_compliment_looks` — "Compliment their looks" | 20 |
| Flirty | `flirty_playful_teasing` — "Playful teasing" | 20 |
| Flirty | `flirty_intimate_eye_contact` — "Intimate eye contact" | 30 |
| Deep | `deep_ask_life` — "Ask about their life back home" | 40 |
| Deep | `deep_share_feelings` — "Share your feelings" | 40 |
| Deep | `deep_discuss_connection` — "Discuss your connection" | 50 |

### Intros (4 dynamics, no sub-tree)

| Intent ID | UI label |
|-----------|----------|
| `intro_friendly` | "Be friendly with {Name}" |
| `intro_flirty` | "Flirt with {Name}" (omitted same-gender) |
| `intro_deep` | "Get deep with {Name}" |
| `intro_banter` | "Banter with {Name}" |

### In-conversation follow-ups (flat with category chip)

From `OPTION_TEMPLATES` in `src/game/engine/option_defaults.py`. The engine prunes to 3-4 per turn based on NPC tone. UI tags each with its category chip.

| intent_kind | UI label | Category chip |
|-------------|----------|---------------|
| `honest_vulnerable` | Get honest and vulnerable | Deep |
| `escalate_flirt` | Push the flirt | Flirty |
| `deflect_with_humor` | Deflect with humor | Banter |
| `joke_back` | Tease back | Banter |
| `go_deeper` | Get deeper | Deep |
| `ask_about_topic` | Ask about it | Friendly |
| `apologize` | Apologize honestly | Friendly |
| `defend_self` | Hold your ground | Banter |
| `change_subject` | Change the subject | Banter |
| `supportive_listen` | Hold space | Friendly |
| `supportive_validate` | Validate them | Friendly |
| `end_softly` | End softly | Friendly (always shown, leaves convo) |
| `walk_away` | Walk away | Banter (always shown, leaves convo) |

### Locked-category hint copy

Shown beneath a dimmed category button when the player hasn't unlocked it.

| Category | Hint |
|----------|------|
| Friendly | (always unlocked, no hint) |
| Banter | (always unlocked, no hint) |
| Flirty | "Get to know them a little first." |
| Deep | "Build real trust first." |

---

## 3. Two-step LLM call shape

### Sequence per conversation turn

```
1. Player clicks intent button   (UI fires onChoose(action))
2. POST /session/turn             (engine + player_voice + npc_voice run)
3. Server runs player_voice       (1 LLM call in live mode)
4. Server runs npc_voice          (1 LLM call in live mode)
5. Response returns Exchange      (player_line, npc_reply, both populated)
6. UI plays player bubble         (camera focuses player)
7. User taps                      (advance beat)
8. UI plays npc bubble            (camera focuses NPC)
```

The two LLM calls happen **on the server in one HTTP roundtrip**. The UI then displays the two bubbles sequentially with a tap between, so the player reads their own line before the reaction. There is no second roundtrip per turn.

### player_voice agent

**Input fields:**
- `state.player.archetype_id`, `state.player.gender`, `state.player.name`, `state.player.known_facts[]`
- `target_id` and the target's HeartbreakerSummary (name, archetype, mood, recent affection/chemistry/trust)
- `intent_id` and the catalogued metadata (category, tags, stat_used)
- Last 3-5 exchanges between player and target (if any) — `state.npc_conversations[target_id]` tail
- Top 3 memories involving the target — `state.memories` filtered by subject_id/holder_id
- Active beat context — `state.audience_score`, day/phase, location_label

**Output:**
- `player_dialogue: str` — first-person, 1-2 sentences, voice-true to the player's archetype, tone-true to the intent.

**Prompt skeleton:**
> You write what the player says. Player is {name}, a {archetype} ({gender}). Talking to {target_name}, a {target_archetype}. Intent: {intent_label} ({category}). Recent memory: {memory_summary}. Relationship: chemistry {x}, trust {y}, day {d}. Write one or two lines, first-person, that land the intent. Reference shared moments when natural — don't force it.

### npc_voice agent

**Input fields:**
- Everything player_voice saw, PLUS:
- `player_line` (the line player_voice just produced, verbatim)
- The target's full TraitCard (persona, secret_engine, flavor_traits)
- The target's relationship-state with player (affection, chemistry, trust, friendship)
- The target's mood
- Trait-card facts the player has earned via familiarity (the target's `known_facts` from the player's perspective)

**Output:**
- `npc_dialogue: str` — first-person, 1-3 sentences, voice-true to the NPC's TraitCard.
- `npc_tone: str` — one of `flirty`/`vulnerable`/`warm`/`playful`/`amused`/`defensive`/`distant` (drives follow-up option generation).
- `audience_reaction: int` — -2..+2 (small per-turn audience delta on top of mechanical).

**Prompt skeleton:**
> You write {npc_name}'s reply. The player just said: "{player_line}". {npc_name} is a {archetype}; their secret engine is {secret_engine}. Affection toward player: {x}, trust: {y}. Mood: {mood}. Write 1-3 lines that respond to *what the player said*, in {npc_name}'s voice. Also produce: npc_tone (which of these vibes), audience_reaction (small audience swing).

### Mock fallbacks

Both agents have mock implementations that mirror today's `mock_heartbreaker_voice` templates. Demo mode never makes LLM calls. Templates live in:
- `src/game/agents/player_voice.py` → `mock_player_voice()`
- `src/game/agents/npc_voice.py` → `mock_npc_voice()`

---

## 4. Greetings

### npc_greeter agent

**Input fields:**
- `state.player.archetype_id`, `state.player.gender`, `state.player.name`
- The target's name, archetype, gender, mood
- The target's TraitCard.persona

**Output:**
- `greeting: str` — one short opening line, in the NPC's voice, addressed to the player on first meeting.

### Wiring

- Triggered once at intros start (right after `create_character`).
- Fires N parallel calls (8 heartbreakers by default) via `ThreadPoolExecutor`, like `trait_generator.generate_opening_cast`.
- Results populate a new state field: `state.intros.greetings: dict[str, str]`.
- The scene-dialogue stage reads this in `planIntroScene`. If the dict is empty (mock mode or pre-feature checkpoint), falls back to `greetingFor()` in `web/lib/intros.ts`.

### Mock fallback

Mock mode skips the agent entirely. `state.intros.greetings` stays empty. UI falls through to the existing template lookup.

---

## 5. UI shape

### Free-time CharacterMenu (the popover when you tap an NPC)

Two-level. Rendered as a card with 4 rows.

```
┌──────────────────────────────────────────┐
│ Talk to                                  │
│ CHLOE                                ✕   │
├──────────────────────────────────────────┤
│ ☆ Friendly                          ›    │
│ ★ Flirty                            ›    │
│ ☆ Deep        Build real trust first.    │  ← LOCKED, dimmed
│ ☆ Banter                            ›    │
└──────────────────────────────────────────┘
```

Click an unlocked category → menu replaces with sub-intent list:

```
┌──────────────────────────────────────────┐
│  Friendly                       ‹ Back   │
│ CHLOE                                ✕   │
├──────────────────────────────────────────┤
│  Ask how she's feeling                   │
│  Chat about the resort                   │
│  Compliment her personality              │
└──────────────────────────────────────────┘
```

Click a leaf → fires the action.

### Intros (flat, 4 buttons)

No tree. The four dynamics show as horizontal bubbles in the ChoiceFan, exactly like today, but with the new labels ("Be friendly with X", etc).

### In-conversation follow-up (flat, with category chip)

Bubble layout matches today, but each bubble shows a small category tag:

```
[Push the flirt        Flirty]
[Tease back            Banter]
[Get deeper            Deep]
[End softly            Friendly]
```

### Two-step bubble flow

Same SceneBeat queue as today, but the engine now returns BOTH `player_dialogue` and `npc_dialogue` (it already does — what changes is they always populate, in sequence). The director emits:

```
[camera: two_shot focus=target]
[speech: player bubble, text=player_dialogue]   ← tap to advance
[speech: npc bubble,    text=npc_dialogue]      ← tap to advance
```

The chevron pulses on each bubble; tapping anywhere advances.

---

## 6. Engine wiring

### New files

- `src/game/agents/player_voice.py` — protocol, live impl, mock impl.
- `src/game/agents/npc_voice.py` — protocol, live impl, mock impl.
- `src/game/agents/npc_greeter.py` — protocol, live impl, mock impl.
- `src/game/agents/prompts/player_voice.md` — system + user prompt template.
- `src/game/agents/prompts/npc_voice.md` — system + user prompt template.
- `src/game/agents/prompts/npc_greeter.md` — system + user prompt template.

### Modified files

- `src/game/state/event_models.py` — add `IntrosState` with `greetings: dict[str, str]`.
- `src/game/state/models.py` — add `intros: IntrosState | None = None` to `GameState`. Bump `SCHEMA_VERSION` 26 → 27.
- `src/game/engine/character_creation.py` — call greeter (live) and populate `state.intros.greetings`.
- `src/game/agents/heartbreaker_voice.py` — keep as a *thin* shim that runs player_voice + npc_voice in sequence and returns Exchange (so existing callers don't break during the rollout).
- `src/game/engine/turn.py` — already uses `heartbreaker_voice` callable, no further change.
- `src/api/app.py` — wire greeter into `AgentBundle.live()` and `AgentBundle.mock()`.
- `src/api/serializers.py` — refresh `action_label` for `introduce_to` to use new verb phrases.

### State additions

```python
class IntrosState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    greetings: dict[str, str] = Field(default_factory=dict)
```

`GameState.intros: IntrosState | None = None` — null until intros start, then populated.

### AgentBundle shape

```python
@dataclass(frozen=True)
class AgentBundle:
    heartbreaker_voice: HeartbreakerVoiceFn  # composed shim
    player_voice: PlayerVoiceFn           # new
    npc_voice: NpcVoiceFn                 # new
    npc_greeter: NpcGreeterFn             # new
    # ... existing fields
```

---

## 7. Evals

### New checks

Added to the scenario check vocabulary:

- `player_voice_grounded` — assert player_voice prompt input contained:
  - The chosen `intent_id`
  - At least one player known_fact about the target, OR an empty list for first-meeting turns
  - The last exchange snippet if conversation history exists
- `npc_voice_grounded` — assert npc_voice prompt input contained:
  - The verbatim `player_line` from the same turn
  - The chosen `intent_id`
  - The NPC's trait_card.persona
  - The NPC's affection toward player
- `intent_unlock_correct` — assert every action surfaced for the current turn has `intent_id` whose `unlock_affection` ≤ the target's affection_with_player

### Scenario refresh

- `day1-intro-round`: keep the 8 intros + First Spark Pairing. Its single thread-check rubric protects cast voice separation and the engine-owned opening choice.
- `interruption-accept`, `interruption-defer`, `interruption-ignore`: add `npc_voice_grounded` to assert NPC reply references the player line.
- `pull-success`, `pull-rejection`: same.

### Trace inspection

Each agent records its full prompt input + reasoning summary (if reasoning_effort != none) in `agent_traces`. Eval framework checks the prompt input dict for the required fields above.

---

## 8. Sequencing

1. **doc + agent skeletons** — this PR's first commit. Adds player_voice/npc_voice/npc_greeter modules with mock impls only; live impls stubbed.
2. **engine wiring** — `heartbreaker_voice` becomes the composed shim. `state.intros` field added. `character_creation` calls greeter (mock returns empty dict for now). Tests stay green.
3. **UI: intro labels + two-step beats** — drop the `responseFor()` preview text, surface intent labels via `action_label`, split Exchange into two SceneBeats. SceneDirector wires the new flow.
4. **UI: tree CharacterMenu** — categorized two-level expansion. Locked categories with hint copy.
5. **Live impls + prompts** — write the three live agent prompts. Wire `AgentBundle.live()`. Run mock evals to confirm shape unchanged.
6. **Run real-LLM evals + iterate prompts** — read reasoning traces, tune prompts where outputs go off-voice or skip memory grounding.
7. **Regenerate checkpoints** — `build_demo_checkpoints` now includes the new intros state. Re-bake all 12.
8. **Manual playtest** — pre-greetings, free-time chat with Chloe (drill into tree), in-conversation follow-up, full Day-1 walkthrough.

---

## 9. Success criteria

A PR is mergeable when:

- `uv run pytest tests/ --ignore=tests/agents` — 368+ tests pass.
- `cd web && npx tsc --noEmit` — clean.
- `uv run python -m src.game.cli verify --all` — all fixture hashes pass.
- `uv run python -m src.game.cli llm-eval --out review-packet/llm-eval-mock` — 0 failures in mock mode.
- Live-mode eval (`--real-llm`) — judged scenarios with the new grounded checks pass at the rate or better than the current pack baseline (16/24 pre-feature).
- Manual playtest matrix:
  - Day-1 intros: every NPC greets dynamically (live), or templated (mock); two-step bubble flow reads cleanly; auto-cycle to next NPC after NPC reply tap.
  - Free-time conversation with Chloe at affection 15: Friendly + Banter unlocked; Flirty + Deep dimmed with hint copy. Click Friendly → sub-options reveal. Click "Ask how she's feeling" → player bubble → tap → NPC bubble.
  - Same with Chloe at affection 30: Flirty unlocks; Deep still locked. Sub-intents show correctly.
  - In-conversation follow-ups: category chips visible on each bubble.
- Mobile viewport (390×844): CharacterMenu doesn't clip; tree expansion fits.
- Reduced-motion: tree-expand collapses to instant transition.

---

## 10. What's out of scope (this PR)

- Real-LLM cost optimisation (caching player_voice across re-renders, etc).
- New intent categories beyond Friendly/Flirty/Deep/Banter.
- Stat-check failure variants of player_voice (the line wins/loses).
- Visual themes per category (chip color is enough; full category-specific bubble styling is later).
- Sub-tree depth beyond level 2 (e.g. drilling into "Compliment looks" → "physical" vs "presence"). Defer.

---

## 11. Open questions (will resolve during build)

- Should `walk_away` and `end_softly` live as a separate "Exit" button outside the 4 categories, or stay inside Banter / Friendly respectively? Lean: outside. Confirm in playtest.
- When all sub-intents in a category are at the same unlock threshold (e.g. all 3 Friendly intents at 0), should clicking the category SKIP the sub-tree and fire the most-common one? Lean: no, always show the sub-tree so the player picks the specific texture. Confirm in playtest.
- Should `flirty_intimate_eye_contact` (unlock 30) hide from the sub-tree at affection 20-29, or show as locked? Lean: show as locked with the per-intent threshold as hint copy. Confirm in playtest.
