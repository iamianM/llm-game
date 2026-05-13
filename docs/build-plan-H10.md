# Build Plan: Phase H10 — Engine Architecture Refresh

H1–H9 built the full game and fixed game feel. H10 cleans up the agent architecture that's been quietly costing us quality and money. Four targeted refactors: native chat-history continuity for in-conversation calls, a three-output Curator, model routing rebalance plus parallel background calls, and a three-source options model that shifts most option generation to code with a thin LLM contextual layer.

No new gameplay surface. Same six agents, smarter wiring.

**Design sources:** [03-LLM-Architecture.md](../03-LLM-Architecture.md), [05-Interaction-System.md](../05-Interaction-System.md), [07-Gossip-And-Information.md](../07-Gossip-And-Information.md), [11-Conversation-Flow.md](../11-Conversation-Flow.md).

**Operating contract:** See [build-plan-H-index.md](build-plan-H-index.md). Four sub-phases. Each commits independently with `make qa` green. User records one short manual session after H10.4 to validate.

---

## Architectural Decisions

### Native conversation chains for Islander Voice (H10.1)

Today: every Islander Voice call rebuilds the conversation context as a text block injected into the user message ("Recent exchange history: ..."). This wastes tokens, doesn't use the model's native attention over prior turns, and forces us to make a "how many exchanges do we include" decision.

After H10.1: Islander Voice calls within a single player conversation pass the **full prior exchanges as a real OpenAI messages array** (alternating user/assistant turns). The system prompt stays static. Each new turn's user message contains only what's *new*: the intent the player picked, the resolved mechanical outcome, the scene context for this exchange.

**Implementation:** client-side messages array (not server-side `previous_response_id`). This keeps the recording/replay model clean — the trace already stores every exchange, so we can rebuild the messages array on replay from trace data without OpenAI server state.

```python
def build_voice_messages(
    state: GameState,
    conversation: Conversation,
    new_turn_context: NewTurnContext,
) -> list[dict[str, str]]:
    """Build the message array for the next Islander Voice call.

    First message is a 'scene set' user message describing the conversation
    opening. Subsequent messages alternate user (engine sets the next turn's
    context) and assistant (the Exchange JSON from each prior exchange).
    Final message is the new turn's user context.
    """
    messages = [_scene_setup_message(state, conversation)]
    for record in conversation.exchanges:
        messages.append(_turn_user_message(record))
        messages.append(_exchange_assistant_message(record))
    messages.append(_render_new_turn_context(new_turn_context))
    return messages
```

The Exchange JSON serialized as the assistant message lets the model see what it produced before — natural continuity.

**Conversation close cleans up nothing in the API sense** (it's stateless on our side anyway). The Curator runs as today.

**Replay determinism:** `RecordedIslanderVoice` replays from trace records as today — the message-array shape doesn't change the recorded Exchange contract.

### Three-output Conversation Curator (H10.2)

The Curator becomes the single source for three structured outputs at every conversation close:

```python
class CuratorOutput(BaseModel):
    memories: list[Memory]                   # existing — per-participant first-person
    summary: str                              # NEW — third-person paragraph for recaps
    gossip_seeds: list[GossipSeed]            # NEW — explicit "worth telling" moments

class GossipSeed(BaseModel):
    subject_id: str                           # who the gossip is about
    gist: str                                 # one-line, third-person, repeatable
    holder_id: str                            # who can spread it
    spreadable_to: list[str]                  # NPCs likely to be interested
    emotional_weight: int                     # 1-10
```

**Summary** is what the daily "While you were busy" recap reads (H9.6 added that recap pulling from background dialogues; H10.2 enriches it from player conversations too). One paragraph, narrative, third-person.

**Gossip seeds** are the explicit "this is gossip-worthy" extraction. The Curator decides what counts — a confession, a flirt the player wasn't supposed to see, a betrayal, a vulnerability. Routine warmth is not a seed.

**Engine post-processing** for gossip spread in background NPC-NPC conversations: when the Curator returns gossip seeds from a closed conversation, the engine checks each seed against the other participant's interests (chemistry with subject, alliance with holder, etc.). If interested, the engine creates a `source=told_by` memory on the listener.

This is engine logic, not LLM logic — once the Curator emits seeds, the engine handles the propagation deterministically.

**Memory deduplication:** if a gossip seed essentially repeats a memory's content (same holder, same subject, overlapping prose), the engine prefers the memory and discards the seed. The prompt instructs the Curator to skip seeds that duplicate memories.

### Model routing rebalance (H10.3)

| Agent | Today | After H10.3 | Why |
|---|---|---|---|
| Islander Voice | gpt-4.1-mini | gpt-4.1-mini (keep) | Player reads every word; prose quality matters most |
| Event Narrator | gpt-4.1-mini | gpt-4.1-mini (keep) | Reality TV narrator voice; player reads it |
| **Conversation Curator** | gpt-4.1-mini | **gpt-5.4-mini (low reasoning)** | Multi-output structured task with judgment (memory vs summary vs gossip); benefits from reasoning |
| Contextual Options | gpt-5.4-mini | gpt-4.1-mini (after H10.4 shrinks scope) | Now produces only 1-2 bespoke options; prose-leaning |
| Villa Orchestrator | gpt-5.4-mini | gpt-5.4-mini (keep) | Structured world-state planning |
| **Background Dialogue** | gpt-4.1-mini | **gpt-4.1-nano** | Off-screen, summarized for player; speed and cost matter |
| **Player Autopilot** | gpt-4.1-mini | **gpt-4.1-nano** | Testing tool, not player-facing |

All model IDs hardcoded module constants. No abstraction layer (R6).

### Parallel background calls (H10.3)

Today, multiple Background Dialogue calls fire sequentially within `apply_villa_update`. If the Villa Orchestrator says three NPC convos continue + one starts, that's four sequential API calls (~4-8 sec). Same for Curator runs on multiple convos closing in one turn.

After H10.3: parallel via `asyncio.gather`. The OpenAI client supports async. The bottleneck on player turn latency drops meaningfully.

**Engine async refactor:**
- `run_turn` gets an async sibling `run_turn_async` that the CLI invokes via `asyncio.run`.
- Background Dialogue agent gets an async method `generate_async`.
- Conversation Curator agent gets an async method `curate_async`.
- `apply_villa_update` becomes async and uses `asyncio.gather` for parallel calls.
- Sync wrapper preserved for tests that don't care about parallelism.

**Replay determinism preserved:** recorded agent commits replay in order from the trace. Parallel execution only matters during live runs.

### Three-source options model (H10.4)

Today: Contextual Options is a single LLM call producing 2-4 options. Slow, expensive per option, and the LLM sometimes picks bland or repetitive labels.

After H10.4: the wheel is built from three sources, merged by the engine:

**1. Code-default options** (always run, no LLM):

A new module `engine/option_defaults.py` produces 4-6 options based on:
- Always include exactly one **Exit** (`end_softly` after warm exchanges, `walk_away` after cold ones).
- If last exchange was a **miss** with the NPC defensive/cold: include **Apologize** (`apologize`) and **Defend** (`defend_self`).
- If last exchange was a **success** and target affection ≥ 25: include **Escalate** options matching the conversation category (Flirty → `escalate_flirt`; Deep → `go_deeper`).
- If player has a **gossip-eligible memory** about a third party: include a `share_gossip_about_X` option (new intent kind in H9.3 gossip system).
- If target has a **gossip seed** matching player interest: include `ask_about_X` option (per H5 gossip flow).
- Always include a **Banter** fallback (`joke_back`) when the conversation has a chance to lighten.

These options are template-driven; no LLM call. ~30 lines of Python.

**2. Tone-reaction options** (always run, no LLM):

A small dict mapping NPC tone after the last exchange to suggested follow-up intents:

```python
TONE_REACTIONS = {
    "suspicious": ["defend_self", "honest_vulnerable", "change_subject"],
    "defensive": ["apologize", "change_subject", "end_softly"],
    "cold": ["apologize", "end_softly"],
    "vulnerable": ["go_deeper", "supportive_listen", "supportive_validate"],
    "flirty": ["escalate_flirt", "joke_back"],
    "warm": ["go_deeper", "joke_back", "ask_about_topic"],
    "playful": ["joke_back", "escalate_flirt", "deflect_with_humor"],
    "amused": ["joke_back", "ask_about_topic"],
}
```

Adds 1-2 tone-appropriate options. Code looks up by `last_exchange.npc_tone`.

**3. Contextual LLM options** (1-2 only, via the slimmer Contextual Options agent):

The Contextual Options call is now scoped to filling 1-2 bespoke slots. Its prompt is updated to:
- Receive the `default_options_already_present` list
- Not duplicate any intent_kind already in defaults
- Produce only options that reference *specific* context (a backstory bit, a recent line, a moment from earlier in the conversation)

Engine merges all three sources:

```python
def build_follow_up_menu(state, conversation, last_exchange) -> FollowUpMenu:
    defaults = default_options(state, conversation, last_exchange)
    tone_options = tone_reaction_options(last_exchange.npc_tone, state)
    bespoke = contextual_options_agent.generate(
        state, last_exchange,
        already_present=[o.intent_kind for o in defaults + tone_options],
    )
    merged = merge_dedupe_cap(defaults + tone_options + bespoke, max_total=5)
    return FollowUpMenu(options=merged, npc_will_leave=..., npc_exit_line=...)
```

Net effect: wheel feels richer (specific bespoke options) and more reliable (code-guaranteed exits, apologize, escalate when contextually right).

`npc_will_leave` decision stays with the LLM (it's the part that needs context judgment). The contextual options agent's output now includes only `options + npc_will_leave + npc_exit_line` (no full menu structure).

---

## Phase H10.1 — Native Conversation Chains for Islander Voice

**Scope.** Replace the in-prompt "Recent history" text block with a real OpenAI messages array carrying alternating user/assistant turns from the conversation's prior exchanges.

### Changes

**Agent (`agents/islander_voice.py`):**
- New `build_voice_messages(state, conversation, new_turn_context) -> list[dict]` helper.
- `OpenAIIslanderVoice.generate` calls `responses.parse` with `input=messages` (list) instead of `input=rendered_text_block`.
- The system prompt loads from disk as today (unchanged).
- `NewTurnContext` is a small Pydantic struct: chosen intent, outcome (success/miss), mechanical change summary, scene context for *this* turn (location, others present).
- The new turn's user message is a single concise prompt: "The player chose [intent]. Mechanical outcome: [success/miss]. Location: [loc]. Others present: [list]. Write the exchange."
- Per-exchange assistant message is the Exchange JSON serialized via `model_dump_json()`.

**State (`state/models.py`):**
- No new fields. The `Conversation.exchanges` list already records everything needed to rebuild the messages array.

**Engine (`engine/turn.py`):**
- Where Islander Voice is invoked for `START_CONVERSATION` and `RESPOND_WITH`, passes the conversation + new turn context. No more in-prompt history serialization.

**Recorded agent (`engine/recorded_agents.py`):**
- `RecordedIslanderVoice` continues to read recorded Exchanges from trace. Messages array is irrelevant for replay; the recorded Exchange IS the output.

**Mock agent:**
- `mock_islander_voice` unchanged — it's a deterministic stub.

**Prompt:**
- [`islander_voice.md`](../src/game/agents/prompts/islander_voice.md) keeps its `## Context` section but removes the "Recent exchange history" line (because the LLM now sees actual prior turns as messages, not as a context block). Claude updates this; Codex installs verbatim per R17.

### Tests

- `tests/agents/test_islander_voice_chain.py`:
  - `test_build_voice_messages_first_exchange_has_one_scene_and_one_turn_user_message`
  - `test_build_voice_messages_includes_prior_exchanges_as_alternating_messages`
  - `test_assistant_message_for_prior_exchange_is_valid_exchange_json`
  - `test_new_turn_user_message_includes_intent_and_outcome`
  - `test_replay_preserves_exchange_outputs`

### Acceptance criteria

- [ ] `make qa` green.
- [ ] `make test-llm` green.
- [ ] Islander Voice API requests contain a messages array, not a single context block.
- [ ] Mid-conversation calls include all prior exchanges as alternating user/assistant messages.
- [ ] Conversation closes cleanly — no leftover state on the agent side.
- [ ] Replay via `play --replay TRACE` produces byte-identical state hash.
- [ ] Existing scenario fixtures pass without regeneration (this is a structural change, not a mechanical one).

### Anti-goals

- No use of OpenAI's `previous_response_id` chain (we use client-side messages array for replay friendliness).
- No persistent state on agent objects (Islander Voice stays stateless across conversations).
- No prompt edits Codex authors (R17).

---

## Phase H10.2 — Three-Output Curator + Gossip Spread

**Scope.** Curator emits memories + summary + gossip_seeds. Engine post-processes gossip_seeds to propagate memories between participants and bystanders.

### Changes

**Agent (`agents/conversation_curator.py`):**
- Output schema becomes `CuratorOutput { memories, summary, gossip_seeds }`.
- New `GossipSeed` Pydantic model.
- Prompt updated to describe the three outputs and when to emit each.

**Prompt:**
- [`conversation_curator.md`](../src/game/agents/prompts/conversation_curator.md) gets a new `## Three outputs` section (Claude writes; install verbatim). Pre-written below.

**State (`state/models.py`):**
- `Conversation` gains `summary: str | None = None` — set when the conversation closes.
- `Memory` already supports `source` and `source_id` for gossip propagation (no schema change).
- Bump `SCHEMA_VERSION`.

**Engine (`engine/memory.py`):**
- New `propagate_gossip_seeds(state, conversation, seeds) -> list[Memory]`:
  - For each seed, compute the listener (the conversation participant who didn't hold the seed) or matching bystanders.
  - For each listener whose `relationship.affection` with the seed's `subject_id` is non-zero, or whose recent memory tags include the subject, create a memory:
    - `holder_id` = listener
    - `subject_id` = seed.subject_id
    - `content` = seed.gist
    - `source` = "told_by"
    - `source_id` = seed.holder_id
    - `emotional_weight` = max(2, seed.emotional_weight - 2) — secondhand attenuates
    - `tags` = ["told_by", "gossip_spread"] + any tags carried by the seed
- Dedupe: if a seed essentially matches an existing memory (same subject, overlapping prose by simple token match), skip.

**Engine (`engine/turn.py`):**
- After the Curator runs for a closed conversation, apply memories, store summary on `state.active_conversation.summary` (before it's cleared), and call `propagate_gossip_seeds`.

**Daily recap (H9.6):**
- The daily recap renderer now pulls from both background dialogue summaries AND player conversation summaries authored by the Curator. Strictly better signal for "what happened that day."

**Eval:**
- `eval/playthrough.py` adds:
  - `assert_curator_emits_summaries` — at least 50% of closed conversations have a non-empty summary.
  - `assert_gossip_seeds_observed` — at least one gossip seed emitted across the trace.
  - `assert_gossip_propagated` — at least one memory with `source=told_by, source_id=<npc>` (not just player-shared gossip).

### Tests

- `tests/agents/test_curator_three_outputs.py` (mark llm):
  - `test_curator_returns_memories_summary_seeds`
  - `test_summary_is_third_person_paragraph`
  - `test_gossip_seeds_have_subject_id_and_gist`
  - `test_routine_warmth_does_not_produce_gossip_seed`
  - `test_seed_skipped_when_matches_existing_memory`
- `tests/engine/test_gossip_propagation.py`:
  - `test_propagate_gossip_seeds_creates_told_by_memory_on_listener`
  - `test_propagation_attenuates_weight`
  - `test_propagation_skips_when_no_interest`
  - `test_propagation_dedupes_against_existing_memories`

### Acceptance criteria

- [ ] `make qa` green.
- [ ] `make test-llm` green.
- [ ] After a closed player conversation, `state.active_conversation.summary` (or the trace record's curator output) contains a non-empty paragraph.
- [ ] After a closed NPC-NPC conversation with gossip-worthy content, at least one `source=told_by` memory appears on the listener.
- [ ] Daily recap (H9.6) pulls from both background and player conversation summaries.
- [ ] Three new eval assertions pass on a real-LLM playthrough.

### Anti-goals

- No LLM-driven gossip propagation. Propagation is engine logic; the LLM only emits seeds.
- No re-Curator on already-closed conversations.
- No gossip seeds for the player as subject (the player's actions are visible; gossip about the player happens elsewhere via the existing memory system).
- No prompt edits Codex authors (R17).

---

## Phase H10.3 — Model Routing + Parallel Background Calls

**Scope.** Update model constants. Refactor background dialogue + curator paths to async. Use `asyncio.gather` for parallelism.

### Changes

**Model constants (each agent module):**
- `ISLANDER_VOICE_MODEL = "gpt-4.1-mini"` (unchanged)
- `EVENT_NARRATOR_MODEL = "gpt-4.1-mini"` (unchanged)
- `CONVERSATION_CURATOR_MODEL = "gpt-5.4-mini"` (was gpt-4.1-mini)
- `CONTEXTUAL_OPTIONS_MODEL = "gpt-4.1-mini"` (was gpt-5.4-mini, scope shrunk in H10.4)
- `VILLA_ORCHESTRATOR_MODEL = "gpt-5.4-mini"` (unchanged)
- `BACKGROUND_DIALOGUE_MODEL = "gpt-4.1-nano"` (was gpt-4.1-mini)
- `PLAYER_AUTOPILOT_MODEL = "gpt-4.1-nano"` (was gpt-4.1-mini)

**Curator (gpt-5.4-mini):** add `reasoning={"effort": "low"}` to the call params, same pattern as Villa Orchestrator.

**Async agents:**
- `OpenAIBackgroundDialogue.generate_async(state, ...) -> BackgroundExchange` — awaitable wrapper using `AsyncOpenAI`.
- `OpenAIConversationCurator.curate_async(state, ...) -> CuratorOutput` — same.
- Sync versions of both remain as `generate` and `curate` that internally use `asyncio.run` (for tests and mock paths). Document that production code uses the async versions inside async `run_turn`.

**Engine (`engine/villa.py`, `engine/turn.py`):**
- `apply_villa_update_async(state, update, agents, rng)` becomes async.
- All Background Dialogue calls fire in parallel via `asyncio.gather`.
- All Curator calls for conversations closing in this turn fire in parallel via `asyncio.gather`.
- Engine `run_turn_async` is the new entry point; `run_turn` is a sync shim calling `asyncio.run(run_turn_async(...))`.

**CLI (`cli/commands/play.py`):**
- Live play continues to call sync `run_turn`. Internally async. No change to user experience.

**Replay:**
- `RecordedAgents` shims remain sync — replay reads from disk, no API calls, no parallelism needed.

**Eval:**
- `eval/playthrough.py` aggregate stats gain `agent_calls_total_estimated` (rough count from records — `len(records) * agents_per_turn`). Useful signal but not asserted.

### Tests

- `tests/agents/test_background_dialogue_async.py`:
  - `test_async_generate_returns_valid_exchange`
  - `test_sync_wrapper_works`
  - `test_parallel_calls_complete_independently`
- `tests/engine/test_turn_async.py`:
  - `test_run_turn_async_matches_sync_for_same_inputs`
  - `test_apply_villa_update_parallel_preserves_hash`
- `tests/agents/test_curator_async.py`:
  - `test_async_curate_returns_valid_output`
  - `test_curator_model_constant_is_gpt_5_4_mini`

### Acceptance criteria

- [ ] `make qa` green.
- [ ] `make test-llm` green.
- [ ] All seven model constants match the table above.
- [ ] `make play` shows live turns completing faster when multiple background conversations are active (eyeball: 2-3x speedup vs pre-H10.3).
- [ ] Replay via `play --replay TRACE` produces byte-identical state hash.
- [ ] No regression in any scenario fixture hash.

### Anti-goals

- No general async-everywhere migration. Only the agent call layer goes async.
- No new dependencies beyond `httpx` and `AsyncOpenAI` (both already transitively present).
- No retry-on-failure logic added. Fail loud (R2).

---

## Phase H10.4 — Three-Source Options Model

**Scope.** Replace the single Contextual Options call with code defaults + tone-reaction templates + 1-2 LLM bespoke options.

### Changes

**New module (`engine/option_defaults.py`):**
- `default_options(state, conversation, last_exchange) -> list[FollowUpOption]` produces 4-6 base options per the rules in Architectural Decisions above.
- `TONE_REACTIONS: dict[str, list[str]]` constant.
- `tone_reaction_options(state, last_exchange) -> list[FollowUpOption]` returns 1-2 tone-appropriate options.

**Agent (`agents/contextual_options.py`):**
- `ContextualOptionsAgent.generate` now receives an `already_present: list[str]` argument (the intent_kinds already in code defaults).
- Output schema slimmed: `ContextualBespoke { options: list[FollowUpOption] (1-2), npc_will_leave: bool, npc_exit_line: str | None }`.
- Model changes to `gpt-4.1-mini` (prose-leaning since labels are prose).

**Engine (`engine/conversation.py` or new helper):**
- `build_follow_up_menu(state, conversation, last_exchange, bespoke_options, npc_will_leave, npc_exit_line) -> FollowUpMenu`:
  - Combine defaults + tone-reactions + bespoke.
  - Dedupe by `intent_kind`.
  - Ensure exactly one `category=exit` (drop or add).
  - Cap at 5 total options.
  - Return assembled FollowUpMenu.

**Engine (`engine/turn.py`):**
- After Islander Voice generates an Exchange and the engine knows the conversation is open:
  1. Compute defaults via code.
  2. Compute tone-reactions via code.
  3. Call Contextual Options agent for bespoke + leave-judgment.
  4. Call `build_follow_up_menu` to assemble.
  5. Store on conversation's `pending_options`.

**Prompt:**
- [`contextual_options.md`](../src/game/agents/prompts/contextual_options.md) substantially rewritten by Claude — pre-written below. Scope explicitly shrunk: agent adds 1-2 bespoke options, judges NPC departure, that's it. Does not produce the full wheel anymore.

**Validation:**
- `validate_follow_up_menu` continues to enforce the full-wheel contract (2-4 options, exactly one exit, no digits, valid intent_kinds). This still applies to the assembled wheel; the bespoke agent's output is unmerged.

**Replay:**
- Trace records the *assembled* `FollowUpMenu` per turn (same shape as today). The bespoke + defaults split is engine-internal.

**Eval:**
- New aggregate stat: `bespoke_options_per_turn` (median count of bespoke options per turn that had a wheel).

### Tests

- `tests/engine/test_option_defaults.py`:
  - `test_default_options_always_includes_one_exit`
  - `test_default_options_includes_apologize_after_miss`
  - `test_default_options_includes_escalate_at_high_affection_opposite_sex`
  - `test_default_options_includes_share_gossip_when_player_holds_memory`
  - `test_default_options_includes_ask_about_when_target_holds_gossip_seed`
  - `test_default_options_respects_gender_pair_filter`
- `tests/engine/test_tone_reactions.py`:
  - `test_tone_reaction_includes_apologize_for_defensive`
  - `test_tone_reaction_includes_escalate_for_flirty`
  - `test_tone_reaction_empty_for_unknown_tone`
- `tests/engine/test_follow_up_menu_assembly.py`:
  - `test_assemble_dedupes_by_intent_kind`
  - `test_assemble_ensures_exactly_one_exit`
  - `test_assemble_caps_at_five`
  - `test_assemble_validates_final_menu`
- `tests/agents/test_contextual_options_slim.py` (mark llm):
  - `test_bespoke_returns_at_most_2_options`
  - `test_bespoke_does_not_duplicate_already_present`
  - `test_bespoke_npc_will_leave_judgment_present`

### Acceptance criteria

- [ ] `make qa` green.
- [ ] `make test-llm` green.
- [ ] Wheel labels in a real-LLM play session show a clear mix of: stat/situation defaults ("Apologize"), tone reactions ("Defend yourself" after suspicious), and bespoke moment-specific labels ("Ask about her sister's pregnancy").
- [ ] Wheel always includes exactly one exit option.
- [ ] Wheel respects gender pair filtering (no Flirty between same-sex pairs).
- [ ] When player holds a gossip-shareable memory, a `share_gossip_about_X` option appears.

### Anti-goals

- No removing Contextual Options entirely — the bespoke layer is real value.
- No code-only wheel (LLM still adds the specific options that code can't write).
- No more than 5 visible options.
- No prompt edits Codex authors (R17).

---

## Prompt updates Claude owns (pre-written here)

### Update for `islander_voice.md` (H10.1) — remove the recent-history context line

Replace the line in `## Context`:

> - Recent exchange history in this conversation.

with:

> - Prior exchanges in this conversation appear as preceding messages in this conversation thread, not as a context block.

(Other context lines unchanged.)

### Update for `islander_voice.md` (H10.2) — gossip drop section

Add after the existing `## Gender pair voice` section (or wherever the existing prompt has the natural insertion point):

```markdown
## Gossip you hold

The user message may include `gossip_eligible_memories` — memories you (the Islander) hold about people other than the player. If a player line, the conversation topic, or the current scene naturally invites bringing one up, work it into your reply. Don't force it, don't drop everything at once — one well-placed mention per exchange when it lands.

Natural drops:
- Player asks about your day → reference something you witnessed off-screen.
- Player mentions another islander by name → share what you know if relevant.
- Player asks a deep question → answer with a story that involves another islander.

If no gossip fits the moment, don't add any. Forcing gossip into a wrong moment reads as awkward; the player notices.
```

### Update for `conversation_curator.md` (H10.2) — three outputs section

Replace the existing `## Output` section with:

```markdown
## Output

You produce three things from a closed conversation:

### Memories

Per-participant first-person memories. Existing rules apply — what each person felt, in their voice, with weight 1-10 and tags. At least one per participant. Optionally bystander memories tagged as `witnessed`.

### Summary

One paragraph, third-person, narrative. What happened in the conversation, in order, with the emotional shape. Two to four sentences. This is what the daily recap pulls from.

Example: "Player and Chloe spent the morning at the pool. Chloe opened up about her sister's pregnancy weighing on her, and Player asked thoughtful questions instead of deflecting. The mood softened over the conversation."

### Gossip seeds

Explicit "this is worth telling someone else" moments. Each seed:

- `subject_id` — who the gossip is about. Must be an islander mentioned in the conversation (not necessarily a participant).
- `gist` — one short line, third-person, that the holder could repeat aloud.
- `holder_id` — who can spread it (one of the conversation participants or a listed bystander).
- `spreadable_to` — list of islander ids likely to be interested (high chemistry with subject, alliance with holder, recent drama). Can be empty.
- `emotional_weight` — 1-10.

Only flag a moment as a gossip seed if it's genuinely worth talking about — a confession, a flirt revealed, a betrayal seen, a vulnerable confession. Routine warmth is not a gossip seed.

If a gossip seed would essentially repeat content already captured in a memory, just include the memory and skip the seed. Don't duplicate.
```

### Update for `contextual_options.md` (H10.4) — slim scope rewrite

Replace the existing `## Output` section with:

```markdown
## Output

You add 1-2 *bespoke* follow-up options to a partially-built wheel. The engine already added 4-6 default and tone-reaction options. Your job is the specific, moment-aware layer.

Return a `ContextualBespoke`:

- `options` — 1 or 2 `FollowUpOption` items, each with: `label` (short, specific), `category`, `intent_kind` (from the enumerated set), `stat_used`, `risk`, `tone`, `unlock_threshold` (or null).
- `npc_will_leave` — true if the NPC would naturally walk away now. The user message includes a `departure_probability` hint.
- `npc_exit_line` — if leaving, one short in-character line. Otherwise null.

The user message includes `already_present: list[str]` — intent_kinds the engine already added. **Do not produce options whose intent_kind is in this list.** Your slot is for moment-specific options the engine couldn't write.
```

And after the `## Hard rules` section, replace the `## Honoring the last exchange` content with:

```markdown
## What counts as a bespoke option

A bespoke option references something specific. Generic intents (apologize, escalate_flirt, end_softly) are handled by code defaults. Your options reference:

- A topic from the last NPC line ("Push her on the Marcus thing")
- A backstory bit the NPC revealed ("Ask about her sister's pregnancy")
- A memory the NPC holds about a third party ("Bring up what she saw at the kitchen")
- A specific moment from earlier in this conversation ("Circle back to the loyalty question")

**Wrong (generic — code adds these):** "Apologize", "Push the flirt", "End on a high note", "Tease back".
**Right (specific — code can't write these):** "Ask about Liam's accent again", "Circle back to her ex", "Bring up the bombshell tension", "Tell her you saw her watching Marcus".
```

### Update for `villa_orchestrator.md` (H10.2) — gossip spread note

Add at the end of `## How to decide`:

```markdown
- **NPCs spread gossip naturally.** When you continue or end an NPC-NPC conversation where one participant holds a high-weight memory about a third party that the other participant cares about, the engine automatically creates a "told_by" memory chain. You don't need to do anything special — keep the conversation going. The Curator handles the spread on close.
```

---

## Done checklist for Codex

### H10.1 — Native Conversation Chains
- [ ] Wait for Claude's updated `islander_voice.md` (recent-history line replacement only)
- [ ] Install verbatim per R17
- [ ] Write `build_voice_messages` helper in `agents/islander_voice.py`
- [ ] Refactor `OpenAIIslanderVoice.generate` to pass messages array to `responses.parse`
- [ ] Add `NewTurnContext` Pydantic model with intent, outcome, scene fields
- [ ] Tests for message-array construction
- [ ] Run `make qa`, `make test-llm`
- [ ] Verify replay determinism on existing scenario fixtures
- [ ] Append build log
- [ ] Commit: `Phase H10.1: native conversation chains for Islander Voice`

### H10.2 — Three-Output Curator + Gossip Spread
- [ ] Wait for Claude's updated `conversation_curator.md` and `islander_voice.md` (gossip drop section) and `villa_orchestrator.md` (gossip spread note)
- [ ] Install all three updates verbatim per R17
- [ ] Add `GossipSeed`, update `CuratorOutput` schema
- [ ] Add `summary` field to `Conversation`
- [ ] Bump `SCHEMA_VERSION`
- [ ] Write `propagate_gossip_seeds` in `engine/memory.py`
- [ ] Wire into `engine/turn.py` after Curator runs
- [ ] Update daily recap to pull from player conversation summaries too
- [ ] Tests for three-output Curator and gossip propagation
- [ ] Three new eval assertions
- [ ] Regenerate scenario fixtures
- [ ] Run `make qa`, `make test-llm`
- [ ] Append build log
- [ ] Commit: `Phase H10.2: three-output Curator and gossip spread`

### H10.3 — Model Routing + Parallel Background Calls
- [ ] Update model constants in all seven agent modules per the table
- [ ] Add `reasoning={"effort": "low"}` to Curator calls (now gpt-5.4-mini)
- [ ] Add `generate_async` to Background Dialogue
- [ ] Add `curate_async` to Conversation Curator
- [ ] Add `run_turn_async` to `engine/turn.py`
- [ ] Refactor `apply_villa_update` to async with `asyncio.gather`
- [ ] Sync `run_turn` wraps async via `asyncio.run`
- [ ] Tests for async correctness and parallel hash preservation
- [ ] Verify replay determinism
- [ ] Run `make qa`, `make test-llm`
- [ ] Append build log
- [ ] Commit: `Phase H10.3: model routing and parallel background calls`

### H10.4 — Three-Source Options Model
- [ ] Wait for Claude's rewrite of `contextual_options.md` (slim scope)
- [ ] Install verbatim per R17
- [ ] Write `engine/option_defaults.py` with `default_options` and `tone_reaction_options`
- [ ] Slim down `ContextualOptionsAgent` to bespoke output only
- [ ] Update model constant to `gpt-4.1-mini`
- [ ] Write `build_follow_up_menu` assembly logic
- [ ] Wire into `engine/turn.py`
- [ ] Tests for defaults, tone reactions, assembly, slimmed agent
- [ ] Verify wheel rendering in `make play` shows mixed sources
- [ ] Verify gender pair filtering still applies
- [ ] Verify `share_gossip_about_X` option appears when player holds shareable memory
- [ ] Run `make qa`, `make test-llm`
- [ ] Append build log
- [ ] Commit: `Phase H10.4: three-source options model`

### After all four commit

- [ ] Run one real-LLM autopilot session each persona, seed 42: loyal + chaotic
- [ ] User records one manual session
- [ ] Generate packets for all three
- [ ] User reviews all three; Claude reads the same packets and writes a qualitative review

---

## Global anti-goals (H10-specific)

- ❌ No new agents.
- ❌ No new gameplay surface — H10 is plumbing only.
- ❌ No removing existing Contextual Options agent. Scope shrinks; agent stays.
- ❌ No `previous_response_id` chain (client-side messages array for replay friendliness).
- ❌ No retry-on-failure logic — fail loud (R2).
- ❌ No prompt edits Codex authors (R17). Claude owns all updates listed above.
- ❌ No reducing test coverage. Async tests and parallel tests are additive.

---

## What this phase produces

After H10 commits:

1. Islander Voice has natural conversation memory across exchanges — model attention works as intended; no re-templated context per turn.
2. Curator's outputs make daily recaps meaningful, gossip propagation explicit, and conversation history queryable through structured summaries.
3. Live turns are visibly faster — multiple background conversations and curator calls run in parallel.
4. Wheel labels feel rich and varied — code-guaranteed defaults plus bespoke moment-specific options from a leaner LLM call.
5. Cost per turn drops meaningfully (nano for background + autopilot, parallelism reduces latency, slimmer Contextual Options scope).

The game does what it did before but with smarter wiring. Foundation for Phase I (UI) or Phase J (procedural/depth) becomes cleaner.
