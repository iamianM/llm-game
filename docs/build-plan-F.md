# Build Plan: Phase F — The Conversation System

> Historical build plan. This file is kept for implementation context only.
> Current planning lives in [current-plan.md](current-plan.md).

This is the corrective plan that builds the actual game described in [05-Interaction-System.md](../05-Interaction-System.md), [11-Conversation-Flow.md](../11-Conversation-Flow.md), and [03-LLM-Architecture.md](../03-LLM-Architecture.md). The deterministic engine from A2-E is the substrate; this phase builds the conversational layer that sits on top of it — the layer the player actually experiences.

Read [`ENGINEERING.md`](../ENGINEERING.md), [`docs/qa-strategy.md`](qa-strategy.md), and every ADR in [`docs/decisions/`](decisions/) before each sub-phase. Also re-read the three design docs cited above.

---

## Operating Contract

Same as [build-plan-A2-E.md](build-plan-A2-E.md), with one change.

1. **Read first.** Before each sub-phase: re-read `ENGINEERING.md`, the ADR index, this plan, and the design docs cited.
2. **Smallest complete change.** Make the change. Add tests. Run `make qa`. If anything fails, fix root cause (R5).
3. **Commit at sub-phase end.** One commit per sub-phase, message `Phase F<N>: <one-line summary>`. Append a 5-line entry to `docs/build-log.md`.
4. **Continue without permission.** If a sub-phase's acceptance criteria are met, proceed to the next. Stop and report only if:
   - A sub-phase takes more than 2 sessions.
   - `make qa` is red and you cannot fix it.
   - A model ID does not work with the available API key.
   - Scope would expand beyond what this plan authorizes.
5. **Mid-phase checkpoint after F2.** Generate a single HTML page rendering ~10 single-exchange conversations across the four core categories (Friendly/Flirty/Deep/Banter) with the real Islander Voice agent. Save as `review-packet-preview/session-phaseF2.html` and post the path to the user. **Do not continue to F3 without explicit user approval.** This is the voice-quality gate — F3 amplifies whatever voice F2 establishes, so verify it first.
6. **Final report.** End of F3: regenerate the full review packet (real multi-exchange conversations across the 3 policy scripts). Post the path.

---

## Architectural Decisions

These are the questions Codex will hit on day one. Settle them up front.

### 1. Where conversation state lives

A new `Conversation` Pydantic model in [`src/game/state/models.py`](../src/game/state/models.py):

```python
class ExchangeRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    turn_index: int
    intent_id: str
    player_dialogue: str
    npc_dialogue: str
    npc_tone: str
    npc_mood_after: Mood
    success: bool
    tags: list[str]

class Conversation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_id: str
    started_on_turn: int
    started_on_day: int
    exchanges: list[ExchangeRecord]
    accumulated_tags: list[str]
    status: Literal["open", "closing", "closed"]
    departure_probability_last: int = 0  # last computed value, debugging
```

`GameState.active_conversation: Conversation | None`. Only one open conversation at a time. Closed conversations are not retained in `GameState` — they live in trace artifacts.

### 2. Action vocabulary extension

`ActionKind` gets three new top-level values:

- `START_CONVERSATION` — opens a `Conversation` with `target_id`. Requires no active conversation.
- `RESPOND_WITH` — submits a follow-up option index inside an active conversation. Requires active conversation.
- `END_CONVERSATION` — player-initiated exit. Requires active conversation.

Existing `ActionKind` values (`ADVANCE_PHASE`, `MOVE`, `LEAVE`, etc.) remain top-level. The flat `TALK / FLIRT / LISTEN / BOLD_FLIRT` action kinds are **deleted** and replaced by per-intent specifics inside `START_CONVERSATION` and `RESPOND_WITH`. R3: one shape per concept.

`PlayerAction` gains:
- `intent_id: str | None = None` — only set for `START_CONVERSATION` (the initial intent) and `RESPOND_WITH` (the chosen follow-up intent_kind).
- `option_index: int | None = None` — only set for `RESPOND_WITH` during live play; replay uses `intent_id` and option ordering.

### 3. Determinism contract

The mechanical state hash continues to ignore LLM-generated prose. It hashes:
- All `GameState` fields except `active_conversation.exchanges[*].player_dialogue` and `npc_dialogue`.
- `accumulated_tags` and `success` flags within exchanges ARE hashed — those are mechanical outcomes.

This means: same seed + same action script → same hash, regardless of which words the LLM picked. Replay tests assert on the hash. They do not assert on dialogue text.

Implementation: add `state_hash_payload(state)` to `src/game/state/snapshot.py` that strips dialogue fields before hashing. Test `test_dialogue_does_not_affect_hash` proves it.

### 4. Multi-exchange replay

Action scripts record the chosen `intent_id` (the structured field), not the option index from the live menu. During replay:

- The `ContextualOptions` LLM call still runs to produce the option set (so we exercise the agent).
- The runtime matches the recorded `intent_id` against the freshly-generated option list. If a match exists, use that option's index. If no match, fail loud (R2) — the replay is broken.
- For deterministic CI runs without LLM, `--mock-llm` substitutes a fixed-output mock that always produces options matching the recorded `intent_id`.

This means real LLM is required to fully replay a real session, but mock LLM is sufficient for engine/scenario tests.

---

## Model Routing

| Agent | Model | Reasoning effort | Why |
|---|---|---|---|
| **Islander Voice** | `gpt-4.1-mini` | n/a | Natural dialogue prose. Voice quality dominant. |
| **Contextual Options** | `gpt-5.4-mini` | low | Structured JSON with intent/stat/risk metadata. Tool-call shape. |
| **Event Narrator** | `gpt-4.1-mini` | n/a | Reality TV narrator prose. |

Hardcoded in module constants. No abstraction layer. If a model ID is invalid for the available API key, **fail loud and stop**. Do not silently substitute. See [twins/tony-robbins-rri/config.yaml](C:/Users/Mcian/projects/steno-livekit-agent/twins/tony-robbins-rri/config.yaml) for the steno precedent on `gpt-5.4-mini`.

No per-call budget cap, no spend tracking, no `LLM_BUDGET_USD` env var. Cost is not a constraint for v0 — game feel is. Do not add a budget enforcement layer.

---

## Phase F1: Tiered Intent Menu

**Design source:** [05-Interaction-System.md § Hybrid Menu System](../05-Interaction-System.md), [02-Core-Mechanics.md § Interaction Success Formula](../02-Core-Mechanics.md).

**Scope.** Replace flat `ActionKind` (TALK/FLIRT/LISTEN/BOLD_FLIRT/LEAVE) with a tiered intent system. Still no LLM dialogue — single mechanical exchange like today, but the *vocabulary* is now what the design specifies. F1 is the engine prep for F2.

**Changes.**

- Add `Mood` enum to [`src/game/state/models.py`](../src/game/state/models.py): `HAPPY, FLIRTY, UPSET, ANXIOUS, ANGRY, CONTENT`. Default `CONTENT`. Add `mood: Mood = Mood.CONTENT` to `IslanderState`.
- New file `content/intents.yaml` with this shape (full catalog inline below):
  ```yaml
  intents:
    - id: friendly_ask_feelings
      category: friendly
      label: "Ask how she's feeling"
      stat_used: eq
      tags: [supportive, sincere]
      unlock_affection: 0
      relationship_deltas:
        success: {affection: 2, trust: 2}
        miss: {affection: 0, trust: 0}
    - id: friendly_chat_villa
      category: friendly
      label: "Chat about the villa"
      stat_used: banter
      tags: [casual, friendly]
      unlock_affection: 0
      relationship_deltas:
        success: {affection: 2, friendship: 1}
        miss: {affection: 0, friendship: 0}
    - id: friendly_compliment_personality
      category: friendly
      label: "Compliment her personality"
      stat_used: charm
      tags: [warm, sincere]
      unlock_affection: 0
      relationship_deltas:
        success: {affection: 3, trust: 1}
        miss: {affection: 0, trust: -1}
    - id: flirty_compliment_looks
      category: flirty
      label: "Compliment her looks"
      stat_used: charm
      tags: [flirty, surface]
      unlock_affection: 20
      relationship_deltas:
        success: {chemistry: 5, affection: 2}
        miss: {chemistry: -1, affection: 0}
    - id: flirty_playful_teasing
      category: flirty
      label: "Playful teasing"
      stat_used: banter
      tags: [flirty, playful]
      unlock_affection: 20
      relationship_deltas:
        success: {chemistry: 4, affection: 2}
        miss: {chemistry: -2, affection: -1}
    - id: flirty_intimate_eye_contact
      category: flirty
      label: "Intimate eye contact"
      stat_used: graft
      tags: [flirty, intense]
      unlock_affection: 30
      relationship_deltas:
        success: {chemistry: 6, affection: 1}
        miss: {chemistry: -2, affection: -2}
    - id: deep_ask_life
      category: deep
      label: "Ask about her life back home"
      stat_used: eq
      tags: [deep, vulnerable]
      unlock_affection: 40
      relationship_deltas:
        success: {trust: 5, affection: 3}
        miss: {trust: -1, affection: 0}
    - id: deep_share_feelings
      category: deep
      label: "Share your feelings"
      stat_used: eq
      tags: [deep, vulnerable]
      unlock_affection: 40
      relationship_deltas:
        success: {trust: 5, affection: 4, chemistry: 2}
        miss: {trust: -2, affection: -1}
    - id: deep_discuss_connection
      category: deep
      label: "Discuss your connection"
      stat_used: loyalty
      tags: [deep, committed]
      unlock_affection: 50
      relationship_deltas:
        success: {trust: 4, affection: 5, chemistry: 3}
        miss: {trust: -3, affection: -2}
    - id: banter_tell_joke
      category: banter
      label: "Tell a joke"
      stat_used: banter
      tags: [funny, light]
      unlock_affection: 0
      relationship_deltas:
        success: {affection: 2, friendship: 2}
        miss: {affection: 0, friendship: 0}
    - id: banter_playful_roast
      category: banter
      label: "Playful roasting"
      stat_used: banter
      tags: [funny, edgy]
      unlock_affection: 10
      relationship_deltas:
        success: {chemistry: 2, friendship: 2}
        miss: {affection: -2, friendship: -1}
    - id: banter_funny_story
      category: banter
      label: "Tell a funny story"
      stat_used: charm
      tags: [funny, charming]
      unlock_affection: 0
      relationship_deltas:
        success: {affection: 2, friendship: 1}
        miss: {affection: 0}
  ```
- New module [`src/game/engine/intents.py`](../src/game/engine/intents.py): `Intent` Pydantic model, `IntentCategory` enum, `load_intents()` reads `content/intents.yaml`, `available_intents_for(state, target_id)` returns categorized list filtering by `unlock_affection`.
- Rewrite [`src/game/engine/actions.py`](../src/game/engine/actions.py):
  - Delete `TALK`, `FLIRT`, `LISTEN`, `BOLD_FLIRT`, `LEAVE` from `ActionKind` (R3 — no parallel shapes).
  - Add `START_CONVERSATION`, `RESPOND_WITH`, `END_CONVERSATION`.
  - `available_actions(state)` returns `START_CONVERSATION` per visible-and-not-eliminated islander when no `active_conversation`, otherwise returns conversation-aware options (built in F3; for F1 it's just `END_CONVERSATION` + structurally similar to today).
- Rewrite [`src/game/engine/rules.py`](../src/game/engine/rules.py):
  - Delete `_apply_talk`, `_apply_flirt`, `_apply_listen`, `_apply_bold_flirt`.
  - Add `_apply_intent(state, intent, target, rng) -> MechanicalResult` that computes success per the formula in [02-Core-Mechanics.md § Success Calculation Details](../02-Core-Mechanics.md) and applies deltas from the intent's `relationship_deltas` table.
  - For F1: simplified success formula — `chance = 50 + stat*5 + affection//4 + mood_modifier`. Full formula (compatibility, attachment style, etc.) lands incrementally; F1 just gets the structure right.
- Rewrite [`src/game/cli/commands/play.py`](../src/game/cli/commands/play.py) to render the tiered menu:
  ```
  Talk to Chloe
    Friendly:
      1. Ask how she's feeling (EQ)
      2. Chat about the villa (Banter)
      3. Compliment her personality (Charm)
    Flirty: (locked, requires affection 20)
    Deep: (locked, requires affection 40)
    Banter:
      4. Tell a joke (Banter)
      5. Playful roasting (Banter)
      6. Funny story (Charm)
    Or: 7. Leave
  ```
- Update `content/lint.py` to validate `content/intents.yaml` schema and assert all `stat_used` values are valid stats.
- New tests:
  - `tests/engine/test_intents.py` — load intents, category filtering, unlock thresholds.
  - `tests/engine/test_intent_rules.py` — at least 3 intents have correct success math and deltas.
- Update all existing scenario YAML fixtures to use the new action shape. Bump `SCHEMA_VERSION` to 4. Regenerate `expected_hash` values.
- Update policy YAMLs (`scripts/fixtures/policy-*.yaml`) to use intent-based actions. We'll regenerate them properly in the F3 wrap-up; for F1 just make them syntactically valid.

**Acceptance criteria.**
- `make qa` green. mypy strict passes on changed engine modules.
- `make play` shows a categorized menu with locked categories visible-but-disabled.
- Intent unlocks work: starting a fresh game, Flirty/Deep are locked. Talking up affection to 20 unlocks Flirty.
- Every intent in `content/intents.yaml` has a corresponding code path that doesn't crash. Test asserts coverage.
- `make content-lint` now validates intent frontmatter.

**Anti-goals.**
- No LLM dialogue yet. Mechanical results print as terse one-liners like today.
- No multi-exchange. F1 ends each conversation immediately after one intent.
- No `ContextualOptions` work yet.
- No mood-driven NPC behavior beyond the default `CONTENT` for now.

---

## Phase F2: The Islander Voice Agent

**Design source:** [11-Conversation-Flow.md § Single Exchange Generation](../11-Conversation-Flow.md), [03-LLM-Architecture.md § Dialogue AI](../03-LLM-Architecture.md).

**Scope.** Wire the real Islander Voice agent. After F1's mechanics resolve, the agent generates both the player's actual dialogue line and the NPC's response in their voice. Still single-exchange — F3 adds multi-exchange.

**Changes.**

- Rename `src/game/agents/narrator.py` → `src/game/agents/islander_voice.py`. The existing `mock_narration` becomes `mock_islander_voice` (returns a fixed `Exchange` model, not a string).
- New Pydantic models in `islander_voice.py`:
  ```python
  class Exchange(BaseModel):
      model_config = ConfigDict(extra="forbid")
      player_dialogue: str
      npc_dialogue: str
      npc_tone: Literal["warm", "flirty", "suspicious", "amused", "cold", "vulnerable", "playful", "defensive"]
      npc_mood_after: Mood
  ```
- `IslanderVoiceContext` Pydantic model built from `(state, intent, target, mechanical_result)`. Includes archetype prose from `content/archetypes/`, location flavor from `content/locations/`, last 0-2 exchanges from the active conversation (none for the first exchange).
- New `IslanderVoiceAgent` class:
  - Model: `gpt-4.1-mini` (hardcoded constant).
  - Prompt: rendered from `src/game/agents/prompts/islander_voice.md` (provided below) with context substitution.
  - Output: structured `Exchange`. Use the OpenAI `responses.create()` API with `response_format` constraining to the `Exchange` schema. If structured-output isn't available on `gpt-4.1-mini`, fall back to instructed JSON + Pydantic validation. **Fail loud on parse failure.**
  - Runtime validation enforces (in this order, all R2 — raise on violation):
    - `player_dialogue` and `npc_dialogue` together 20-150 words.
    - No digits in either dialogue field.
    - No name of any eliminated or off-scene islander appears in `npc_dialogue`.
    - `npc_mood_after` is in the `Mood` enum.
- Move the prompt to `src/game/agents/prompts/islander_voice.md`. Use the text from the **Prompts** section below verbatim. Prompts are user-owned (ENGINEERING R17).
- Modify [`src/game/engine/turn.py`](../src/game/engine/turn.py):
  - `TurnResult.narration: str` is replaced with:
    - `exchange: Exchange | None` — set for `START_CONVERSATION` and `RESPOND_WITH`.
    - `event_narration: str | None` — set for ceremony events (Event Narrator agent — see below).
  - `run_turn` invokes `IslanderVoiceAgent` for conversation actions, calls `EventNarratorAgent` for ceremony triggers.
- New `EventNarratorAgent` in `src/game/agents/event_narrator.py`:
  - Model: `gpt-4.1-mini`.
  - Prompt: `src/game/agents/prompts/event_narrator.md` (provided below).
  - Output: structured `EventNarration { prose: str }`.
  - Called when `TurnResult.ceremony_events` is non-empty.
- Add `ceremony_events: list[CeremonyEvent]` to `TurnResult` (from E.1 work — assume that fix lands first).
- Update [`src/game/cli/commands/play.py`](../src/game/cli/commands/play.py) to render exchanges:
  ```
  You: "You look incredible tonight."
  Chloe: *bites her lip* "You're going to give me a big head with all these compliments."

  ✨ Charm check: SUCCESS  💕 Chemistry +5, Affection +2
  hash: 8c2f...
  ```
- Update HTML rendering in [`src/game/reporting/html.py`](../src/game/reporting/html.py) to render exchanges as dialogue blocks with speaker tags, not as paragraph narration.
- New `tests/agents/test_islander_voice.py` (marked `@pytest.mark.llm`):
  - 12 parametrized tests, one per intent in `content/intents.yaml`.
  - Each asserts the runtime contract: word count, no digits, no off-scene names, `npc_mood_after` valid.
  - Smoke: each successfully returns a parseable `Exchange`.
- New `tests/agents/test_event_narrator.py` (marked `@pytest.mark.llm`):
  - 3 parametrized tests: bombshell arrival, recoupling, elimination.
  - Assert prose is 2-4 sentences, references named participants, no digits.
- `make test-llm` runs both.

**Mid-phase checkpoint.** After F2 commits, generate `review-packet-preview/session-phaseF2.html`:
- Use seed 42, fixed player stats, fixed cast (Chloe, Maya, Liam).
- Render 10 single-exchange interactions across all 4 categories (Friendly/Flirty/Deep/Banter), 2-3 per category, mixing success and miss outcomes. Some at different affection levels so Flirty and Deep are unlocked.
- HTML shows each exchange with player line, NPC line, mechanical outcome, hash.
- **Post path to user and stop.** Do not begin F3 until user approves voice quality.

**Acceptance criteria.**
- `make qa` green (no LLM in default).
- `make test-llm` green: 15+ tests (12 islander voice + 3 event narrator) pass.
- `make play` produces real dialogue from `gpt-4.1-mini`. One exchange per turn for now.
- Determinism preserved: replaying a scenario fixture produces the same hash even though dialogue varies. The new `test_dialogue_does_not_affect_hash` proves it.
- Mid-phase HTML preview generated and path posted.

**Anti-goals.**
- No follow-up options yet. After each exchange the conversation ends.
- No conversation history beyond 0-2 prior exchanges (since multi-exchange isn't wired).
- No personality system beyond archetype + mood. Big 5 and attachment style remain placeholders.
- No `--snapshot` loading in play (still scoped out per F1).

---

## Phase F3: Contextual Options, Multi-Exchange, Organic Endings

**Design source:** [11-Conversation-Flow.md § Contextual Follow-up Generation](../11-Conversation-Flow.md), [11-Conversation-Flow.md § Organic Conversation Endings](../11-Conversation-Flow.md).

**Scope.** Make conversations multi-exchange. After each exchange, the Contextual Options agent generates 2-4 dynamic follow-up options based on what the NPC said. The player picks one; that becomes the next intent. Hybrid algorithm + LLM judge decides when the NPC organically leaves.

**Changes.**

- New `Conversation` model and `GameState.active_conversation: Conversation | None` (per Architectural Decision #1 above).
- New module [`src/game/engine/conversation.py`](../src/game/engine/conversation.py):
  - `start_conversation(state, target_id, turn_index) -> Conversation` — initializes with `status="open"`.
  - `append_exchange(conversation, exchange_record)` — appends, capped at last 8 retained.
  - `close_conversation(state, reason: Literal["player_exit", "npc_left", "phase_end"])` — sets `status="closed"`, then sets `state.active_conversation = None`.
  - `departure_probability(conversation, state) -> int` — algorithm per [11-Conversation-Flow.md:172](../11-Conversation-Flow.md). Returns 0-100. **Pure function, no LLM.**
- New Pydantic models in `src/game/agents/contextual_options.py`:
  ```python
  class FollowUpOption(BaseModel):
      model_config = ConfigDict(extra="forbid")
      text: str
      intent_kind: str  # snake_case tag like "deflect_with_humor"
      stat_used: Literal["charm", "banter", "eq", "graft", "loyalty"] | None
      risk: Literal["safe", "low", "medium", "high"]
      tone: str

  class FollowUpMenu(BaseModel):
      model_config = ConfigDict(extra="forbid")
      options: list[FollowUpOption]  # 2-4 items
      npc_will_leave: bool
      npc_exit_line: str | None
  ```
- New `ContextualOptionsAgent` class:
  - Model: `gpt-5.4-mini` with `reasoning_effort: low`.
  - Prompt: `src/game/agents/prompts/contextual_options.md` (provided below).
  - Output: `FollowUpMenu`. Structured output / response_format.
  - Runtime validation (R2):
    - 2 ≤ `len(options)` ≤ 4.
    - At least one option must have `intent_kind` that is exit-flavored (e.g. `end_softly`, `walk_away`, `change_subject_and_drift`). Validate by tag set.
    - If `npc_will_leave` is true, `npc_exit_line` must be non-empty and ≤ 40 words.
    - No option text contains digits.
- Extend [`src/game/engine/actions.py`](../src/game/engine/actions.py):
  - `available_actions(state)` returns:
    - When `active_conversation` is None: `START_CONVERSATION` per visible islander + `MOVE` + `ADVANCE_PHASE`.
    - When `active_conversation` is open: `RESPOND_WITH(option_index)` for each option in the latest computed `FollowUpMenu` + `END_CONVERSATION`. The follow-up menu is computed lazily, after the NPC's most recent exchange, and stored in `state.active_conversation.pending_options` (new field).
  - `validate_action(state, action)` enforces conversation invariants: can't `START_CONVERSATION` while one is open; can't `RESPOND_WITH` while closed.
- Extend [`src/game/engine/turn.py`](../src/game/engine/turn.py):
  - Handle `START_CONVERSATION`: create conversation, compute initial mechanical result, invoke Islander Voice, store exchange, then invoke Contextual Options to populate next menu.
  - Handle `RESPOND_WITH`: validate option_index against pending_options, look up the chosen option's `intent_kind` and map it through a code-side `intent_resolver` (resolves natural-language intent_kinds to concrete `Intent` rows by category + stat — fallback to a generic "freeform" intent with neutral deltas). Then same flow as `START_CONVERSATION` for the new exchange.
  - After each exchange, compute `departure_probability`. Pass to Contextual Options. If the agent returns `npc_will_leave=true`, set conversation status to "closing" — the player still sees the exit line in the next exchange render, then the conversation closes automatically.
  - Handle `END_CONVERSATION`: close conversation cleanly.
- Update [`src/game/cli/commands/play.py`](../src/game/cli/commands/play.py):
  - After an exchange renders, if conversation is open, show the Contextual Options menu:
    ```
    Chloe: "Thanks... though I heard you say that to Aisha earlier."

    How do you respond?
      1. "That's not true — where'd you hear that?"   (DENY, Charm, high risk)
      2. "Jealous already? I like it."                 (DEFLECT, Banter, medium risk)
      3. "You're right. I'm sorry. You're the one I want."  (HONEST, EQ, low risk)
      4. "Let's talk about this later."                (END, safe)
    ```
  - If `npc_will_leave`, render the exit line and close cleanly.
- Update action script schema in `src/game/engine/scenario.py`:
  - Add `RESPOND_WITH` support with `intent_id` field (the recorded intent kind from live play).
  - Replay path: when the `ContextualOptions` agent returns its menu, find the option with matching `intent_kind`. If absent, fail loud.
  - Add `--mock-llm` mode that provides deterministic mock menus matching scenario script's `intent_id` values.
- New test file `tests/engine/test_conversation.py`:
  - Lifecycle: start → append → close.
  - `departure_probability` boundary cases.
  - Validation: can't start two conversations, can't respond when closed.
- New test file `tests/scenarios/fixtures/conversation-multi-exchange.yaml`:
  - A 5-exchange conversation with mocked LLM, locked `expected_hash`. Verifies multi-exchange replay determinism.
- Add `tests/agents/test_contextual_options.py` (marked `@pytest.mark.llm`):
  - 5 parametrized contexts varying in `departure_probability` (0, 30, 70, 100) and last NPC tone.
  - Assert: option count 2-4, exit option present, no digits, departure logic respects probability hint.
- **Rewrite the three policy scripts** to use real multi-exchange conversations:
  - `policy-loyal.yaml`: 4 days of TALK-heavy single-target conversations with Chloe, mixing Friendly/Deep, including Day 5 recoupling.
  - `policy-chaotic.yaml`: Multi-target chasing — flirt aggressively with Maya, then bombshell Aisha when she arrives, including a high-risk denial follow-up.
  - `policy-strategic.yaml`: Long Friendly buildup with Liam, escalate to Deep on Day 3, balanced FLIRT-with-Chloe and friendship-with-Liam.
  - Each script: 8-15 conversation entries (each entry = 3-6 exchanges via `RESPOND_WITH`), plus phase advances, plus ceremony triggers.
- **Regenerate the review packet** as the final F3 deliverable. Each session HTML renders conversations as dialogue blocks. Index page shows seed, day, conversation count, exchange count.
- Balance simulation: rewrite [`src/game/reporting/balance.py`](../src/game/reporting/balance.py) to actually vary actions: for each seed, run a policy where at each decision point an `rng.choice` picks from `available_actions`. Mock LLM. Report:
  - Outcome distribution (player survived / eliminated / partner stolen at recoupling)
  - Average final affection per islander
  - Action category frequency
  - Conversation length distribution

**Acceptance criteria.**
- `make qa` green.
- `make test-llm` green: 25+ tests pass (12 islander voice + 3 event narrator + 5 contextual options + 5 conversation contract).
- `make play` plays multi-exchange conversations end-to-end. A full 6-day session yields 8-20 conversations, each 2-6 exchanges.
- A new fixture `conversation-multi-exchange.yaml` is verified by `make determinism` (mock LLM).
- The regenerated review packet shows real multi-exchange conversations across 3 policy scripts.
- `balance/distribution.html` shows meaningful aggregate stats (not the previous "complete: 1000" stub).

**Anti-goals.**
- No prompt-caching infrastructure — Sonnet/OpenAI auto-caching is fine.
- No mood propagation between NPCs.
- No Big 5 personality scores yet (placeholder fields exist but unused in prompts; archetype text is still the personality vehicle).
- No Type-on-Paper preference matching.
- No conversation interruptions or group conversations.
- No Producer AI.

---

## Prompts

The prompts are user-owned per ENGINEERING R17. They live in the repo at:

- [`src/game/agents/prompts/islander_voice.md`](../src/game/agents/prompts/islander_voice.md) — Islander voice for single-exchange dialogue (F2).
- [`src/game/agents/prompts/event_narrator.md`](../src/game/agents/prompts/event_narrator.md) — Reality TV narrator for ceremonies (F2).
- [`src/game/agents/prompts/contextual_options.md`](../src/game/agents/prompts/contextual_options.md) — Follow-up menu generator (F3).

Codex installs them by reading these files at runtime. Codex does not modify them in source or in code. If a prompt produces poor output, flag the problem and propose an edit to the user; do not soften, shorten, or restructure on Codex's own initiative.


---

## QA Gate Updates

`make qa` after F1: same six targets as today.

`make qa` after F2: add `make test` to validate the new mock-LLM modes work end-to-end. Update `make smoke` to use a Phase F1-shaped scenario fixture that exercises one START_CONVERSATION + one mechanical outcome with mock LLM.

`make qa` after F3: `make smoke` plays a multi-exchange conversation via mock LLM end-to-end. `make determinism` extends to the new `conversation-multi-exchange.yaml` fixture.

`make test-llm` after F3: 25+ tests covering Islander Voice, Contextual Options, Event Narrator.

---

## Global Anti-Goals (Phase F-specific additions)

In addition to the [build-plan-A2-E.md global anti-goals](build-plan-A2-E.md):

- ❌ **No new ADRs for incremental code changes.** This plan IS the architectural commitment for F1-F3. Only write an ADR if a genuinely new architectural decision arises mid-phase.
- ❌ **No Vite UI** — still Phase G or later. CLI + HTML report packet remain the review surface.
- ❌ **No mood propagation, Big 5 mechanics, Type on Paper preferences, group conversations, gossip propagation, Producer AI, Curator agent, Islander Generator agent.** All deferred.
- ❌ **No conversation interruptions** — single-target single-conversation only.
- ❌ **No prompt caching infrastructure** — provider defaults are fine.
- ❌ **No model abstraction layer.** `gpt-4.1-mini` and `gpt-5.4-mini` are hardcoded module constants. If the user wants a different model later, that's a single-line change.
- ❌ **No `# type: ignore`, no `--no-verify`, no silent fallbacks** (R5).
- ❌ **No retention of A2-E action vocabulary alongside the new one.** TALK/FLIRT/LISTEN/BOLD_FLIRT are deleted, not aliased (R3).

---

## Cost Stance

There is no per-call budget cap, no spend tracker, no `LLM_BUDGET_USD` env var, no cost telemetry. Cost is not a constraint for v0. Game feel is the binding constraint. Do not add a budget enforcement layer in any phase.

---

## Done Definition

The Phase F effort is done when all of the following are true:

1. Commits F1, F2, F3 exist with `make qa` green at each.
2. `docs/build-log.md` has one entry per sub-phase.
3. `make test-llm` passes ≥ 25 tests covering all three new agents.
4. `make play` plays multi-exchange conversations end-to-end with real LLM and produces a coherent transcript.
5. The regenerated `review-packet/` shows three sessions with real multi-exchange conversations, balance distribution shows meaningful aggregate stats, narration-quality sample is curated across real exchanges.
6. `tests/scenarios/fixtures/conversation-multi-exchange.yaml` is locked with `expected_hash` and verifies under `make determinism`.
7. User confirms receipt of the regenerated packet path.

After this, the next decision is Phase G: either continue building game-design depth (Big 5 personalities, group conversations, Producer AI), or jump to Phase H (Vite UI on top of the working conversation engine). Choice depends on what the F3 packet reveals about game feel.
