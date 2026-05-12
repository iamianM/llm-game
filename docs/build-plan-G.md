# Build Plan: Phase G — Make It Feel Like A Game

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

## Phase G3 — Memory Model

**Design source:** [07-Gossip-And-Information.md § The Gossip System](../07-Gossip-And-Information.md). Pattern reference: [steno-livekit-agent/src/runtime/memory.py](C:/Users/Mcian/projects/steno-livekit-agent/src/runtime/memory.py).

**Scope.** Add the structured memory layer to canonical state. Conversations and ceremonies create memories. No gossip transfer yet (G5).

**Changes.**
- [`src/game/state/models.py`](../src/game/state/models.py): add `Memory` Pydantic model per the Architectural Decisions section. Add `memories: list[Memory]` to both `IslanderState` and `PlayerState`. Bump `SCHEMA_VERSION` to 6.
- [`src/game/state/snapshot.py`](../src/game/state/snapshot.py): `state_hash_payload` strips `memories[*].content` (LLM prose, like dialogue). Add `test_memory_content_does_not_affect_hash`.
- [`src/game/engine/memory.py`](../src/game/engine/memory.py) (new): `create_memory(holder_id, subject_id, source, day, turn, weight, tags, content) -> Memory` with deterministic id generation via `rng.fork(f"memory-{holder}-{day}-{turn}")`. `add_memory(state, memory)` writes to the right holder.
- [`src/game/engine/turn.py`](../src/game/engine/turn.py): on `END_CONVERSATION`, derive one or two memories per participant from the closed conversation's exchanges. Algorithmic for now — content is templated: `"{player} {category}-talked with me at the {location} on day {day}"`. Tags include the conversation's accumulated_tags. Emotional weight = `min(10, max(1, accumulated_affection_delta // 2 + 3))`.
- Ceremony events generate memories for participants (witnessed) and bystanders at the same location (direct via spectator).

**Acceptance criteria.**
- `make qa` green.
- After a played conversation, both player and NPC have a memory of it in `state.player.memories` and `state.islanders[i].memories`.
- New tests in `tests/engine/test_memory.py`: `test_conversation_close_creates_memories`, `test_memory_id_deterministic_from_seed`, `test_memory_hash_excludes_content`.

**Anti-goals.** No Curator LLM agent yet — keep memory content templated, deterministic. No gossip transfer yet. No memory-driven NPC behavior yet (G5 wires that).

---

## Phase G4 — Background Villa Life

**Design source:** [09-Social-Dynamics.md](../09-Social-Dynamics.md), [08-Daily-Loop.md § Off-screen progression](../08-Daily-Loop.md).

**Scope.** NPCs autonomously interact off-screen during phase advances. Each interaction produces memories for both participants. Algorithmic. No LLM cost.

**Changes.**
- [`src/game/engine/simulation.py`](../src/game/engine/simulation.py): keep deterministic NPC movement. Pairwise NPC-NPC events now produce a `Memory` for both participants (algorithmic content: `"{actor} {kind}-chatted with me at the {location} on day {day}"`). Event kinds expand: `chat`, `flirt`, `argue`, `bond`. Each kind has fixed tags and weight.
- Drama threshold: when two NPCs both roll above 80 on their interaction, mark the event `kind="drama"` (e.g. a real kiss off-screen) — these memories get weight 7-9 and are eligible for gossip in G5.
- Movement: NPCs can move *to* the player's location (drawn in by chemistry with player), making encounters more likely. Currently they move randomly; G4 makes movement weighted by relationship + archetype.
- Public perception: NPCs who witness a flirt or drama event update their own public_perception of the subject.

**Acceptance criteria.**
- `make qa` green.
- After advancing 5 phases on an empty CLI session (no player conversations), NPCs have 5-15 memories each from off-screen interactions.
- The 6-day full-run fixture has visible NPC memory accumulation by day 6.
- New tests: `test_off_screen_chat_creates_memories_for_both`, `test_drama_events_have_high_weight`, `test_npcs_move_toward_chemistry_partners`.

**Anti-goals.** No LLM in background sim — purely algorithmic. No Orchestrator agent. No player-visible prose for off-screen events (player learns through gossip in G5).

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
- [`src/game/agents/prompts/contextual_options.md`](../src/game/agents/prompts/contextual_options.md) — **Claude rewrites for G1** so options return short labels with category metadata. Codex installs verbatim once delivered.

No new prompts in G2-G6. Memory generation in G3 and G4 is templated/algorithmic — no LLM cost, no prompt. Gossip dialogue in G5 reuses IslanderVoice (the existing prompt handles in-character delivery of memory content). The Curator agent and Orchestrator agent are explicitly deferred beyond G.

---

## Global Anti-Goals (Phase G-specific)

Hold these across all sub-phases:

- ❌ No Curator LLM agent. Memory content is templated in G3-G4.
- ❌ No Orchestrator LLM agent. NPC off-screen behavior is algorithmic in G4.
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
