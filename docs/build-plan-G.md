# Build Plan: Phase G — Make It Feel Like A Game

> Historical build plan. This file is kept for implementation context only.
> Current planning lives in [current-plan.md](current-plan.md).

F3 built the conversation system but landed two design drifts: follow-up menus show full dialogue lines (should be short Sims-style labels), and follow-up choices have no mechanical consequence. Phase G fixes both, adds the memory + gossip layer the game has always needed, and ends with one real playthrough as the deliverable instead of three policy scripts and a 1000-seed sim.

Read [`ENGINEERING.md`](../ENGINEERING.md), [`docs/qa-strategy.md`](qa-strategy.md), and ADRs in [`docs/decisions/`](decisions/) before each sub-phase. Re-read [05-Interaction-System.md](../05-Interaction-System.md), [07-Gossip-And-Information.md](../07-Gossip-And-Information.md), and [09-Social-Dynamics.md](../09-Social-Dynamics.md) — they are the design source for G1-G5.

---

## Operating Contract

Same shape as [build-plan-F.md](build-plan-F.md). One commit per sub-phase. `make qa` green at each. Append to `docs/build-log.md`. Stop and report only if: 2+ sessions on one sub-phase, `make qa` red and can't fix, scope expansion, or model ID failure.

No mid-phase checkpoint. G is shorter than F and each sub-phase produces something the user can sit down and play with `make play`. The final review is the single playthrough produced in G6.

---

## Architectural Decisions

### Wheel shape (G1)

`FollowUpOption` changes:

```python
class FollowUpOption(BaseModel):
    label: str                                          # short Sims-style action label
    category: Literal["friendly", "flirty", "deep",
                      "banter", "gossip", "supportive", "exit"]
    intent_kind: str                                    # snake_case tag for math + IslanderVoice
    stat_used: Literal["charm","banter","eq","graft","loyalty"] | None
    risk: Literal["safe","low","medium","high"]
    tone: str
    unlock_threshold: dict[str, int] | None = None      # e.g. {"affection": 30}, optional
```

`text` is deleted. R3: one shape per concept.

The CLI renders the menu **nested by category**, lock-decorated, same shape as the top-level intent menu. Options whose `unlock_threshold` is unmet by the active conversation's target are filtered out before display (and not selectable).

### Tag→delta math (G2)

A `FOLLOW_UP_DELTA_TABLE` keyed on `intent_kind` lives in `src/game/engine/rules.py`. Each entry produces a `RelationshipDelta` for success and miss. `risk` scales magnitude (`high` doubles deltas, `safe` zeros them). Unknown `intent_kind` from the LLM falls back to a neutral entry and logs a warning — but does not silently absorb. **R2 fail-loud** if the table is missing a known intent_kind.

### Memory model (G3)

```python
class Memory(BaseModel):
    id: str                                              # deterministic, derived from RNG fork + turn
    holder_id: str                                       # who holds this memory ("chloe", "player", etc)
    subject_id: str                                      # who it's about
    content: str                                         # short prose
    source: Literal["direct", "witnessed", "told_by"]
    source_id: str | None                                # if told_by, the NPC who told them
    formed_on_day: int
    formed_on_turn: int
    emotional_weight: int = Field(ge=1, le=10)
    tags: list[str] = Field(default_factory=list)
    durable: bool = True
```

`IslanderState.memories: list[Memory] = Field(default_factory=list)` and `PlayerState.memories: list[Memory]`. Hash-included: `id`, `holder_id`, `subject_id`, `source`, `formed_on_day`, `formed_on_turn`, `emotional_weight`, `tags`, `durable`. Hash-excluded: `content` (LLM prose). Update `state_hash_payload()` accordingly. Add `test_memory_content_does_not_affect_hash`.

### Determinism via recorded agent commits

LLM agents (Villa Orchestrator, Background Dialogue, Conversation Curator) produce structured Pydantic outputs — `VillaUpdate`, `BackgroundExchange`, `MemoryBatch` — that are first-class state-commit producers, not invisible helpers. Every commit is recorded in the per-turn trace.

The deterministic contract is:

> **same seed + same player actions + same recorded agent commits → same final mechanical state hash.**

Live play calls real LLMs and writes each commit to the trace. Replay reads the recorded commits and applies them — no LLM calls. Scenario fixtures pin both the player action sequence and the expected agent commits per turn, alongside the expected final hash.

This is the steno pattern: agents commit typed intent, the runtime is a compiler/VM that applies the commits, and the trace is the audit log that makes replay possible. Without recorded commits, replay is impossible because Orchestrator's structural decisions (who moves, which convo ends) can change between runs.

Three operating modes:

- **Live** — real LLM agents, commits recorded. Default for `make play`.
- **Replay** — recorded commits replayed via a `RecordedAgents` shim. Single `--replay TRACE_PATH` flag. Used for verifying a recorded session reproduces, and for scenario fixtures that pin agent commits.
- **Mock** — empty/deterministic agent outputs (orchestrator returns empty `VillaUpdate`, dialogue returns a fixed stub, curator returns a deterministic single memory). Used for engine unit tests that need a player path without recording a real run.

Scenario YAML grows an optional `agent_commits` block per turn:

```yaml
actions:
  - kind: start_conversation
    target_id: chloe
    intent_id: friendly_chat_villa
    agent_commits:
      villa_update:
        npc_movements: []
        conversation_starts: [...]
        conversation_continues: []
        conversation_ends: []
      background_dialogues: []
      curator_batches: []
```

A scenario without `agent_commits` blocks runs in mock mode (empty outputs) — keeps existing fixtures working. A scenario with them runs in replay mode and asserts byte-identical reproduction.

---

### Gossip data flow (G5)

When player starts a conversation with NPC `X`, the wheel can include a `gossip` category. Each gossip option corresponds to one of `X`'s memories whose `subject_id != "player"` AND `emotional_weight >= 4`. Picking the gossip option:

1. Generates a normal exchange via IslanderVoice (NPC tells the gossip in their voice).
2. Adds a new `Memory` to the player with `source="told_by", source_id=X.id`.
3. Applies a small trust delta to X (sharing gossip is intimate).

The Contextual Options agent never invents gossip — it surfaces from the engine's view of `X.memories`. Code passes the eligible memory list as context; the agent's job is just to phrase the label ("Ask what happened with Maya at the kitchen").

### What we keep, what we drop (single-playthrough deliverable)

- **Drop** `make balance` from `make qa`. Keep the `balance` CLI command available for later — it just stops being part of the review packet.
- **Drop** the three policy scripts as the demo surface. Delete the policy YAMLs. Replace with one curated 6-day playthrough (real LLM, snapshot + trace + HTML).
- **Drop** `narration-quality/sample-20-turns.html` and `flagged.md`. Not useful at this scale.
- **Keep** the regenerated playthrough HTML as the single review artifact.

---

## Phase G1 — Wheel UX

**Design source:** [05-Interaction-System.md § Hybrid Menu System](../05-Interaction-System.md), [11-Conversation-Flow.md § Contextual Follow-up Generation](../11-Conversation-Flow.md).

**Scope.** Change the follow-up menu to show short labels grouped by category, with dynamic unlocking. IslanderVoice still writes the actual dialogue line after the player picks.

**Changes.**
- [`src/game/state/models.py`](../src/game/state/models.py): replace `FollowUpOption.text` with `FollowUpOption.label`, add `category`, add `unlock_threshold`. Bump `SCHEMA_VERSION` to 5; regenerate fixtures (R12).
- [`src/game/agents/prompts/contextual_options.md`](../src/game/agents/prompts/contextual_options.md): Claude rewrites this to produce short labels (3-6 words), categorized. Codex installs verbatim per R17.
- [`src/game/agents/contextual_options.py`](../src/game/agents/contextual_options.py): runtime validation enforces `len(label.split()) <= 6`, valid category, valid intent_kind, exactly one option with `category="exit"`.
- [`src/game/engine/actions.py`](../src/game/engine/actions.py): in `available_actions`, filter `state.active_conversation.pending_options.options` by `unlock_threshold` against the target's current relationship values. Locked options are silently dropped from the RESPOND_WITH list (so picking by index works on the visible list).
- [`src/game/cli/commands/play.py`](../src/game/cli/commands/play.py): render the menu nested by category, showing locked categories as `(locked: needs affection 30)`.
- [`src/game/reporting/html.py`](../src/game/reporting/html.py): update `_follow_up_block` to group options by category visually.
- [`src/game/agents/islander_voice.py`](../src/game/agents/islander_voice.py): no signature change. When called for RESPOND_WITH, `intent_id` is the option's `intent_kind` — agent already handles this.

**Acceptance criteria.**
- `make qa` green.
- `make test-llm` green: Contextual Options tests now assert label word count ≤ 6, category ∈ enum, exactly one exit, optional unlock_threshold valid.
- `make play`: when you start a conversation and the NPC responds, the follow-up menu shows short labels grouped by category. Locked categories show as locked. After you pick, IslanderVoice produces the full exchange.
- The contextual_options prompt produces labels like `"Tease back"`, `"Ask something deeper"`, `"End on a good note"` — never full dialogue lines.

**Anti-goals.** No mechanical changes (G2). No memory yet (G3). No gossip yet (G5). Just the menu shape.

---

## Phase G2 — Make Choices Matter

**Design source:** [02-Core-Mechanics.md § Relationship Application](../02-Core-Mechanics.md), [05-Interaction-System.md § Success Calculation Details](../05-Interaction-System.md).

**Scope.** Follow-up choices apply real relationship deltas. Picking `honest_vulnerable` vs `deflect_with_humor` produces different mechanical outcomes.

**Changes.**
- [`src/game/engine/rules.py`](../src/game/engine/rules.py): add `FOLLOW_UP_DELTA_TABLE: dict[str, IntentDeltaTable]` covering at minimum these intent_kinds: `honest_vulnerable, escalate_flirt, deflect_with_humor, joke_back, go_deeper, ask_about_topic, apologize, defend_self, change_subject, end_softly, walk_away`. Each has `success` and `miss` `RelationshipDelta` values.
- `_apply_follow_up`: look up the intent_kind, apply `risk` magnitude scaling (`safe → 0×`, `low → 0.75×`, `medium → 1×`, `high → 1.5×`, deltas rounded), apply on success or miss respectively. Unknown intent_kind raises (R2).
- Update `update_public_perception` to react to `intent_kind` (e.g. `honest_vulnerable → +1`, `escalate_flirt` when coupled → -1).

**Suggested table (Codex tunes during implementation):**

| intent_kind | success | miss |
|---|---|---|
| honest_vulnerable | trust +5, affection +2 | trust -2, affection +0 |
| escalate_flirt | chemistry +6, affection +1 | chemistry -3, trust -1 |
| deflect_with_humor | friendship +3, chemistry +1 | friendship +0 |
| joke_back | friendship +2 | friendship -1 |
| go_deeper | trust +4, affection +3 | trust -1, affection +0 |
| ask_about_topic | affection +2, trust +1 | affection +0 |
| apologize | trust +5 | trust +0 |
| defend_self | trust +2 if line was attacked, else trust -1 | trust -2 |
| change_subject | affection +0, friendship +1 | affection -1 |
| end_softly | no deltas | no deltas |
| walk_away | affection -1 | affection -1 |

**Acceptance criteria.**
- `make qa` green.
- New tests in `tests/engine/test_rules.py`: `test_follow_up_honest_vulnerable_builds_trust`, `test_follow_up_escalate_flirt_miss_drops_chemistry`, `test_follow_up_unknown_intent_raises`, `test_follow_up_high_risk_scales_deltas`.
- `make play`: picking `honest_vulnerable` visibly bumps trust in the next state. Picking `escalate_flirt` and missing visibly drops chemistry.
- The locked `conversation-multi-exchange.yaml` fixture's `expected_hash` regenerates (R12).

**Anti-goals.** No archetype-specific delta tuning. No mood propagation yet. No Big 5.

---

## Phase G3 — Memory Model + Conversation Curator

**Design source:** [07-Gossip-And-Information.md § The Gossip System](../07-Gossip-And-Information.md). Pattern reference: [steno-livekit-agent/src/runtime/memory.py](C:/Users/Mcian/projects/steno-livekit-agent/src/runtime/memory.py) and the Curator agent pattern that runs at frame close.

**Scope.** Add the structured memory layer to canonical state. Add the Conversation Curator agent — runs at `END_CONVERSATION` and produces LLM-authored memories from the conversation history. Memories carry character voice, not templated strings. They are the substrate gossip propagates over in G5.

**Changes.**

- [`src/game/state/models.py`](../src/game/state/models.py): add `Memory` Pydantic model per the Architectural Decisions section. Add `memories: list[Memory]` to both `IslanderState` and `PlayerState`. Bump `SCHEMA_VERSION` to 6.
- [`src/game/state/snapshot.py`](../src/game/state/snapshot.py): `state_hash_payload` strips `memories[*].content` (LLM prose, like dialogue text). Hash-included: `id`, `holder_id`, `subject_id`, `source`, `source_id`, `formed_on_day`, `formed_on_turn`, `emotional_weight`, `tags`, `durable`. Add `test_memory_content_does_not_affect_hash`.
- [`src/game/engine/memory.py`](../src/game/engine/memory.py) (new): `make_memory_id(holder_id, day, turn, rng_fork) -> str` (deterministic id from seeded RNG). `add_memory(state, memory)` writes to the right holder. `recent_memories_for(state, holder_id, limit=5)` for context lookups (used by gossip in G5).
- [`src/game/agents/conversation_curator.py`](../src/game/agents/conversation_curator.py) (new): `ConversationCuratorAgent` with model `gpt-4.1-mini`. Prompt at `src/game/agents/prompts/conversation_curator.md` (Claude writes; Codex installs verbatim per R17). Input: the closed `Conversation` with its `ExchangeRecord` list + both participants' profiles + final relationship state + day/location. Output: a `MemoryBatch` Pydantic model with 1-2 memories per participant. Mock curator (`mock_conversation_curator`) returns one deterministic memory per participant for non-LLM tests.
- [`src/game/engine/turn.py`](../src/game/engine/turn.py): on `END_CONVERSATION`, invoke the Curator. Add returned memories to player and target via `add_memory`. The mechanical state hash does not change because `content` is hash-excluded.
- Ceremony events (recoupling, bombshell, elimination) generate memories for participants and same-location bystanders. G3 keeps these algorithmic — one templated memory per ceremony per witness, low weight, tagged appropriately. G4 enriches drama events through Background Witness; ceremony memories stay algorithmic since the ceremony itself produces narrated prose already.

**Memory content shape.** Each memory's `content` is one sentence written in the holder's first-person voice. The Curator writes character-specific summaries the LLM can later cite when gossiping. Example outputs the Curator should produce from a deep conversation where the player asked Chloe about her past:

- Holder: `chloe`. Subject: `player`. Content: `"Player asked about my past and actually listened — that doesn't happen often here."` Weight 6. Tags: `["deep", "vulnerable", "trust_built"]`. Source: `direct`.
- Holder: `player`. Subject: `chloe`. Content: `"Chloe opened up about being afraid of being lied to. I want to be careful with her."` Weight 7. Tags: `["deep", "vulnerable", "she_trusts_me"]`. Source: `direct`.

**Acceptance criteria.**
- `make qa` green.
- `make test-llm` green: new `tests/agents/test_conversation_curator.py` with 3-5 parametrized scenarios. Each asserts structural contract: 1-2 memories per participant, correct `holder_id` and `subject_id`, non-empty content, weight in 1-10, no digits in content, source ∈ enum.
- After a played conversation in `make play`, both player and target have one or two LLM-authored memories about each other, visible via `/state --debug` or in the trace JSON.
- `test_memory_content_does_not_affect_hash` proves replay determinism: same seed + same action script → same state hash regardless of LLM memory content.

**Anti-goals.** No Background Witness yet (G4). No gossip transfer yet (G5). No memory-driven NPC action selection yet — memories exist but don't change NPC behavior until G5 wires gossip eligibility.

---

## Phase G4 — Villa Orchestrator + Background Conversations

**Design source:** [09-Social-Dynamics.md](../09-Social-Dynamics.md), [08-Daily-Loop.md § Off-screen progression](../08-Daily-Loop.md), [07-Gossip-And-Information.md](../07-Gossip-And-Information.md).

**Scope.** Off-screen NPC behavior is LLM-driven, every turn. A new **Villa Orchestrator** agent runs after each player action and decides who moves, what conversations start, what conversations continue, what conversations end. Background NPC-NPC conversations are **persistent state** that span turns. The villa feels alive because every turn, someone moves, someone starts a chat, someone ends one. The deterministic `simulate_off_screen` algorithm goes away.

**Architecture.**

```
player turn flow:
  player_action -> MechanicalResult
  -> VillaOrchestrator.decide(state)  -> VillaUpdate
  -> validate + apply movements
  -> for each new conversation in update:
       BackgroundDialogue.generate(participants, topic) -> exchange
  -> for each continuing conversation:
       BackgroundDialogue.generate(participants, topic, nudge) -> next exchange
  -> for each ending conversation:
       ConversationCurator.curate(conv, witnesses) -> memories
  -> IslanderVoice.generate(...) -> player's exchange (existing flow)
  -> TurnResult includes VillaUpdate + applied changes for trace visibility
```

**Changes.**

- **State.** New Pydantic models in `state/models.py`:
  ```python
  class BackgroundExchangeRecord(BaseModel):
      turn_index: int
      speaker_a_id: str
      speaker_b_id: str
      speaker_a_line: str
      speaker_b_line: str
      tone: str

  class NPCNPCConversation(BaseModel):
      id: str                                    # deterministic via RNG fork
      participants: list[str]                    # exactly two NPC ids
      location_id: Location
      topic: str
      started_on_turn: int
      exchanges: list[BackgroundExchangeRecord]
      status: Literal["active", "ending", "closed"]
  ```
  Add `npc_conversations: list[NPCNPCConversation] = []` to `GameState`. Bump `SCHEMA_VERSION` to 7.

- **Hash payload.** `state_hash_payload` excludes `npc_conversations[*].exchanges[*].speaker_a_line`, `speaker_b_line`, and `topic`. Hash-included: `id`, `participants`, `location_id`, `started_on_turn`, exchange count, `status`. Add `test_background_dialogue_does_not_affect_hash`.

- **`src/game/agents/villa_orchestrator.py`** (new): `VillaOrchestratorAgent` with model `gpt-5.4-mini`, `reasoning_effort: "low"`. Prompt at `src/game/agents/prompts/villa_orchestrator.md` (Claude wrote it; install verbatim per R17). Input: villa state summary (every non-eliminated NPC with location/mood/top-3-memories/relationship-with-player, active NPC-NPC conversations with id/participants/topic/exchange-count, player's location and active conversation status, recent player actions, upcoming ceremonies). Output: `VillaUpdate` Pydantic model with `npc_movements`, `conversation_starts`, `conversation_continues`, `conversation_ends`.

- **`src/game/engine/villa.py`** (new): pure validation + apply layer. `validate_villa_update(state, update) -> None` enforces: only known NPC ids, no eliminated NPCs, player not in NPC conversations, no continue-and-end on same conv, start participants will be co-located after movements apply, no NPC in two new conversations simultaneously, no convo continued after ending. Failures raise (R2). Then `apply_villa_update(state, update, dialogue_agent, curator_agent, rng) -> AppliedVillaChanges` mutates state and returns the list of memories created.

- **`src/game/agents/background_dialogue.py`** (new): `BackgroundDialogueAgent` with model `gpt-4.1-mini`. Prompt at `src/game/agents/prompts/background_dialogue.md`. Input: both participants' profiles, location, topic, nudge (optional), conversation history so far, bystanders, recent memories per participant. Output: `BackgroundExchange` (speaker_a_line, speaker_b_line, tone). Runtime validation: combined word count 20-120, no digits, third-person body language only.

- **Conversation Curator** (from G3) now handles NPC-NPC conversations on `conversation_ends`. The prompt is already general. Bystanders at the conversation's location are passed in; they get `source="witnessed"` memories. Player can be a bystander too if they're at the same location (witnessing NPCs gossip nearby).

- **`src/game/engine/turn.py`**: `run_turn` accepts optional `villa_orchestrator: VillaOrchestratorFn` and `background_dialogue: BackgroundDialogueFn`. After MechanicalResult applies, before player's IslanderVoice exchange: orchestrator runs, update validates, movements apply, background dialogue and curator fire as appropriate. `TurnResult.villa_update: VillaUpdate | None` and `TurnResult.background_memories: list[Memory]` give trace visibility.

- **Delete `simulate_off_screen` and `ArchetypeBehavior`** from `engine/simulation.py`. The module either gets deleted entirely or stripped to a single function for ceremony-adjacent helpers. R3: no parallel mechanisms.

- **Three agent modes (per the Architectural Decisions section).**
  - **Live mode.** `OpenAIVillaOrchestrator`, `OpenAIBackgroundDialogue`, `OpenAIConversationCurator`. Real LLM calls. Each commit is written to the per-turn trace under `agent_commits`.
  - **Replay mode.** `RecordedVillaOrchestrator`, `RecordedBackgroundDialogue`, `RecordedConversationCurator` read from a trace file and return the recorded commits in order. Engine validation still runs — recorded commits must still pass validation against current state. The `--replay TRACE_PATH` CLI flag swaps all agents to recorded shims for that session.
  - **Mock mode.** `mock_villa_orchestrator(state) -> VillaUpdate` returns an empty update. `mock_background_dialogue(...)` returns a fixed deterministic exchange. `mock_conversation_curator(...)` returns one deterministic memory per participant. Used for unit tests that need a player path without recording a real run, and for scenario fixtures without `agent_commits` blocks.

- **Trace shape.** `TurnTrace` (the per-turn record written to the trace file) gains:
  ```python
  class AgentCommits(BaseModel):
      villa_update: VillaUpdate | None = None
      background_dialogues: list[BackgroundExchange] = []
      curator_batches: list[MemoryBatch] = []

  class TurnTrace(BaseModel):
      ...                                              # existing fields
      agent_commits: AgentCommits = AgentCommits()
  ```
  The HTML report shows agent_commits in a per-turn sidebar so reviewers can see what the world did.

- **Scenario YAML extension.** Each action entry can carry an optional `agent_commits` block per the Architectural Decisions section. Fixtures without the block run in mock mode (backward-compatible). Fixtures with the block run in replay mode and assert exact reproduction. The runner detects which mode to use per-scenario from the YAML shape.

**Acceptance criteria.**

- `make qa` green.
- `make test-llm` green with new tests:
  - `tests/agents/test_villa_orchestrator.py`: 4-5 parametrized scenarios (empty villa, drama brewing, ceremony imminent, gossip-laden NPCs, player in active conversation). Each asserts `VillaUpdate` structural validity.
  - `tests/agents/test_background_dialogue.py`: 4 parametrized scenarios. Word count, no digits, third-person body language, in-voice.
- `make play`: every turn, the TurnResult shows `villa_update` with movements and conversation changes. Reading the trace, NPC-NPC conversations span multiple turns and close with extracted memories.
- After a full 6-day session in `make play`, NPCs have 15-30 LLM-authored memories each — a mix of direct (their own conversations), witnessed (conversations they overheard), and player-conversation memories.
- New engine tests in `tests/engine/test_villa.py`:
  - `test_villa_update_rejects_eliminated_npc`
  - `test_villa_update_rejects_player_in_npc_conv`
  - `test_villa_update_rejects_start_at_wrong_location`
  - `test_villa_update_rejects_end_and_continue_same_conv`
  - `test_npc_conversation_close_invokes_curator`
  - `test_apply_movements_updates_locations`
- Mock-mode replay of the existing `conversation-multi-exchange.yaml` fixture produces the same hash as before (since mock returns empty updates).
- A new `conversation-multi-exchange-with-background.yaml` fixture pins recorded agent commits and asserts byte-identical reproduction in replay mode.
- `make play --record TRACE_PATH` writes a full trace including agent commits. `make play --replay TRACE_PATH` reproduces the same session byte-identically without LLM calls.

**Anti-goals.**

- No Producer AI / event scheduler beyond what ceremonies already do. The orchestrator handles NPC-NPC convos; ceremonies remain on their fixed schedule.
- No "high-stakes filter." Every NPC-NPC conversation runs through the agent pipeline. The Orchestrator decides what's worth having happen; we don't second-guess with a filter.
- No algorithmic NPC movement table. Movement is Orchestrator-driven.
- No player-visible prose for off-screen exchanges directly in the main flow — the player encounters them through gossip in G5. The trace shows them for debugging; the HTML report shows them in a sidebar so reviewers can see what was happening off-screen.
- No NPC-NPC conversations involving the player. The player has their own conversation lane.
- No cost optimization. Every turn calls the orchestrator. Every active background conversation produces one Background Dialogue call per turn. Cost is not the constraint.

---

## Phase G5 — Gossip

**Design source:** [07-Gossip-And-Information.md](../07-Gossip-And-Information.md), [05-Interaction-System.md § Gossip category](../05-Interaction-System.md).

**Scope.** Memories spread. Gossip options appear in the wheel when the player's target has memories worth sharing. Picking gossip transfers the memory to the player and triggers an in-character exchange.

**Changes.**
- [`src/game/engine/conversation.py`](../src/game/engine/conversation.py): when starting a conversation with NPC `X`, compute `gossip_eligible = [m for m in X.memories if m.subject_id != "player" and m.emotional_weight >= 4 and m not in player.memories.via_source(X)]`. Pass this list as `Conversation.gossip_offers`.
- [`src/game/agents/contextual_options.py`](../src/game/agents/contextual_options.py): context now includes the target's `gossip_offers`. Each becomes an option with `category="gossip"`. Label format: `"Ask about {subject_name}"` or LLM-generated short label. `intent_kind="ask_gossip:{memory_id}"`.
- [`src/game/engine/rules.py`](../src/game/engine/rules.py): `_apply_follow_up` recognizes `ask_gossip:{memory_id}` intents. On success: add the memory to the player with `source="told_by"`, apply trust +2 to the gossip source (intimacy bonus), small chemistry -1 to the gossip *subject* if player ever later talks to them and brings it up (deferred to G6 polish).
- [`src/game/agents/islander_voice.py`](../src/game/agents/islander_voice.py): when intent_kind starts with `ask_gossip:`, the context passes the relevant memory's content + emotional weight + tags so the LLM can speak about it in voice. The NPC reveals the gossip in their dialogue.
- The wheel's `gossip` category appears in the CLI render. Lock threshold: target's affection ≥ 25 (NPCs share gossip with people they like enough).

**Acceptance criteria.**
- `make qa` green.
- `make play`: after a few days of off-screen events, talking to an NPC with affection ≥ 25 surfaces real gossip options like "Ask about Maya" (because that NPC witnessed Maya's flirt with Liam). Picking the gossip option produces in-voice dialogue revealing the memory.
- Player's memory list grows as gossip is heard.
- New test: `test_gossip_appears_when_target_has_witnessed_memory`, `test_gossip_pick_transfers_memory_to_player`, `test_gossip_locked_below_affection_threshold`.

**Anti-goals.** No "confront the subject" mechanic yet — the player can hear gossip but cannot weaponize it against the subject in dialogue this phase. No memory decay/forgetting. No NPC sees-through-lies based on memory contradiction. These are future depth.

---

## Phase G6 — One Real Playthrough

**Scope.** Replace the policy-scripts-and-balance-sim packet with one curated 6-day playthrough. This is what the user reviews.

**Changes.**
- Delete `scripts/fixtures/policy-loyal.yaml`, `policy-chaotic.yaml`, `policy-strategic.yaml`. Delete `_run_session` policy loop in `report.py`. Delete the `balance` and `narration-quality` packet subdirectories from the default packet build.
- Keep the `balance` CLI command available (`python -m src.game.cli report balance`) but it's no longer wired into `packet` or `make qa`.
- Add `python -m src.game.cli play --record FILE`: an interactive `make play` session that also writes a full trace + snapshot to disk as the player plays. Each turn writes a record matching what `_run_session` produces.
- Add `python -m src.game.cli report from-trace TRACE_PATH --out PATH`: renders the recorded trace as a session HTML, identical shape to the policy session pages.
- Replace `review-packet/` build: `python -m src.game.cli report packet --trace PATH` takes a recorded session and renders the packet structure as:
  ```
  review-packet/
    index.html                # links to the session, notes, how-to-reproduce
    session.html              # the full playthrough rendered as turn cards
    artifacts/
      session.json            # final state with all memories visible
      session-trace.json
    notes.md                  # Codex writes one page of what they observed
    how-to-reproduce.md
  ```

**Acceptance criteria.**
- `make qa` green.
- The user can `make play --record .game_traces/manual-session.json` and play a 6-day session with real LLM through the CLI.
- `python -m src.game.cli report packet --trace .game_traces/manual-session.json` produces a self-contained `review-packet/` from that single session.
- The `session.html` shows: every conversation as turn cards with categorized follow-up menus, real exchange dialogue, mechanical deltas, gossip moments highlighted, ceremony narrations, and a sidebar/summary of memories per NPC at run end.
- `make balance` still runs the 1000-seed sim if invoked manually but is no longer part of the standard build.

**Anti-goals.** No automated policy playthroughs. No multi-session packets. The artifact is one session the user actually played (or that Codex played as a demo) — the variability and judgment lives in the playing, not in synthetic policies.

---

## Prompts

The prompts are user-owned per ENGINEERING R17. Living in:

- [`src/game/agents/prompts/islander_voice.md`](../src/game/agents/prompts/islander_voice.md) — already installed.
- [`src/game/agents/prompts/event_narrator.md`](../src/game/agents/prompts/event_narrator.md) — already installed.
- [`src/game/agents/prompts/contextual_options.md`](../src/game/agents/prompts/contextual_options.md) — rewritten by Claude for G1 (short labels, categories, unlock thresholds). Install verbatim.
- [`src/game/agents/prompts/conversation_curator.md`](../src/game/agents/prompts/conversation_curator.md) — **G3.** Generalized to handle player+NPC, NPC+NPC, and bystander witnesses. Already written.
- [`src/game/agents/prompts/villa_orchestrator.md`](../src/game/agents/prompts/villa_orchestrator.md) — **G4.** The world brain. Decides movements, conversation starts/continues/ends. Already written.
- [`src/game/agents/prompts/background_dialogue.md`](../src/game/agents/prompts/background_dialogue.md) — **G4.** Writes NPC-NPC dialogue exchanges. Already written.

Gossip dialogue in G5 reuses IslanderVoice — the existing prompt handles in-character delivery of memory content when the IslanderVoice context includes a `gossip_about` memory. No new prompt needed for G5.

---

## Global Anti-Goals (Phase G-specific)

Hold these across all sub-phases:

- ❌ No cost-saving filters on memory or background dialogue generation. The Orchestrator decides what happens; every conversation it spawns runs through Background Dialogue and the Curator. No "high-stakes only" gates.
- ❌ No Producer AI. Event scheduling stays deterministic.
- ❌ No new content authoring beyond what each phase needs. Cast stays at 3 + Aisha bombshell.
- ❌ No Vite UI. CLI remains the surface.
- ❌ No Big 5, attachment styles, Type on Paper preferences. Phase H or later.
- ❌ No prompt modifications by Codex. R17.
- ❌ No `# type: ignore`, no `--no-verify`. R5.
- ❌ No backwards-compat for old fixtures. Bump SCHEMA_VERSION each time models change. R12.
- ❌ No reviving the policy scripts or balance sim as default packet. They live only as opt-in tools.

---

## Done Definition

Phase G is done when:

1. Commits G1, G2, G3, G4, G5, G6 each exist with `make qa` green.
2. `docs/build-log.md` has an entry per sub-phase.
3. `make play --record FILE` plays an interactive 6-day session with real LLM, real wheel, real memories, real gossip surfacing.
4. `report packet --trace FILE` produces the curated single-session packet at `review-packet/`.
5. Reading the session HTML feels like a Love Island game: short menus, real dialogue per pick, mechanical deltas that vary by choice, NPCs that remember things, gossip that shows up at the right moments.
6. User plays at least one full session through the CLI and confirms it feels right.

After that, the question is **Phase H**: deeper depth (Curator agent, Orchestrator agent, Big 5, Type on Paper, win condition, character creation) or the **Vite UI** wrap. We pick based on what one real playthrough reveals.
