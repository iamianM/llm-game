# Build Plan: Phase H9 — Game Feel Pass

> Historical build plan. This file is kept for implementation context only.
> Current planning lives in [current-plan.md](current-plan.md).

H1–H8 built the game's full skeleton: arc, content, autonomy, pacing. The first real playthrough surfaced twelve game-feel issues. H9 is the focused pass that turns the working game into a *fun* game.

This phase is mostly **prompt refinement, context enrichment, and a handful of state/engine changes**. No new agents. No new architectural patterns. The substrate exists; H9 makes the substrate produce better output.

**Player feedback summary** (drives every sub-phase):
- Dialogue options feel categorical, not specific
- NPC responses talk about talking instead of about anything concrete
- Background NPC chats sound more interesting than the player's chats
- Gossip is surface-level
- Villa feels small and static (4 people, no movement)
- No gender awareness — flirting with same-sex NPC felt wrong
- Pull-for-chat retry has no cooldown
- Ignored interruption doesn't actually walk away
- Producer texts and ceremonies don't change what the player is doing

**Design sources:** [00-Game-Start-And-Setup.md](../00-Game-Start-And-Setup.md), [05-Interaction-System.md](../05-Interaction-System.md), [07-Gossip-And-Information.md](../07-Gossip-And-Information.md), [09-Social-Dynamics.md](../09-Social-Dynamics.md), [11-Conversation-Flow.md](../11-Conversation-Flow.md), AGENTS.md.

**Operating contract:** See [build-plan-H-index.md](build-plan-H-index.md). Seven sub-phases. Each commits independently with `make qa` green and a build log entry. The user records one short manual session after H9.7 to validate game feel.

---

## Architectural Decisions

### Gender as canonical state

`Gender` is a new enum with values `MAN`, `WOMAN`. Modeled per the show's convention (heterosexual coupling) without endorsing exclusivity — a v1 phase can open to bi/gay characters by removing the same-sex FLIRT gate.

```python
class Gender(StrEnum):
    MAN = "man"
    WOMAN = "woman"

class PlayerState(BaseModel):
    ...
    gender: Gender

class IslanderState(BaseModel):
    ...
    gender: Gender
```

Bump `SCHEMA_VERSION`. The Gender enum is hash-included; all scenario fixtures regenerate.

Character creation prompts the player to pick gender after archetype. The default archetype-to-gender mapping is symmetric (all three archetypes available to both genders).

### Same-sex vs opposite-sex dialogue categories

`IntentCategory` gains two new values: `BROMANCE` (men-with-men only) and `GOSSIP_RING` (women-with-women only — distinct from the existing `gossip` category which is about *other people's* gossip and remains gender-agnostic). The existing `FLIRTY` category gates by opposite-sex pair only.

Filter logic in `available_intents_for(state, target)`:
- If player and target are opposite sex: Friendly, Flirty, Deep, Banter, Gossip available (unlock-gated per existing rules).
- If player and target are same sex AND both men: Friendly, Bromance, Deep, Banter, Gossip available. Flirty hidden.
- If player and target are same sex AND both women: Friendly, Gossip Ring, Deep, Banter, Gossip available. Flirty hidden.

New intents to author for the two new categories:

**Bromance** (men-with-men):
- `bromance_rib` — friendly roast, banter-coded
- `bromance_check_in` — sincere "how you holding up", eq-coded
- `bromance_share_strategy` — "who you eyeing?", loyalty-coded
- `bromance_solidarity` — "I got your back", loyalty-coded

**Gossip Ring** (women-with-women):
- `gossip_ring_dish_about_him` — talk about a specific man, banter-coded
- `gossip_ring_vent` — emotional, vulnerable, eq-coded
- `gossip_ring_strategize` — "what should I do about Marcus?", graft-coded
- `gossip_ring_alliance` — "we have each other's backs", loyalty-coded

Each authored in `content/intents.yaml` with category, stat_used, tags, unlock_threshold, success/miss deltas (same shape as existing intents).

### NPC backstory as a context field

Each NPC gains a `backstory: str` field (3-5 sentences) — concrete life details the Islander Voice can pull from. Examples:

- Chloe: "Twenty-six, primary school teacher from Liverpool. Living with her older sister since her ex moved out six months ago. Sister's pregnant and Chloe's been thinking a lot about whether she wants kids before thirty."
- Marcus: "Twenty-eight, personal trainer from Manchester. Used to be a semi-pro footballer until a knee injury at twenty-three. Has a four-year-old nephew he's incredibly close to. Worried this show makes him look shallow."

Stored per islander in `state.islanders[i].backstory`. Set at `new_game` per the existing hardcoded cast table. Hash-included.

Backstory is passed into Islander Voice context. The voice can reference it naturally ("My ex moved out and now my sister's pregnant — I keep thinking about whether I'm ready for that").

### Pull retry cooldown

`Conversation` and `IslanderState` get a `pull_attempts_this_phase: dict[str, int]` field on the player — keyed by target_id, incremented on every START_CONVERSATION pull attempt during the current phase, reset on phase advance.

`pull_chance` math extends:
```
pull_chance = base
  + ...
  - (15 × pull_attempts_this_phase[target_id])    # cumulative clingy penalty
```

So a 2nd pull is -15, 3rd is -30, etc. Combined with the clamp at 10, three failed pulls in a row is near-impossible.

Plus a memory effect: at `pull_attempts_this_phase[target_id] ≥ 2`, the target forms a memory tagged `player_kept_pulling`, weight 6. Surfaces as gossip later: "Player kept trying to pull me away from Liam — felt a bit much."

### Ignored interrupter walks away

In `_apply_interruption_response` for `ignore_interruption`, after clearing pending_interruption and applying -4 affection + `ignored_in_public` memory, the engine triggers a movement: interrupter moves to a different location (deterministic from RNG fork). This is engine-driven, not orchestrator-driven, so it fires immediately rather than waiting a turn.

Trace records the movement: `{actor: "maya", kind: "walks_away_after_snub", target: kitchen}`.

### Gather events

Producer texts and ceremonies become **gather events**. When a gather event fires:

1. Any active player conversation closes with reason `gather_event`. Curator runs on the closed conversation.
2. Any active NPC-NPC conversations close with reason `gather_event`. Curator runs on each.
3. All islanders (including player) move to a designated `gather_location` (firepit for producer texts and ceremonies; specific for some events like Hideaway).
4. The event plays out — Event Narrator writes the gather prose, the event resolves mechanically.
5. After the event resolves, time advances by the event's `time_cost` and the phase clock continues.

New state field on `GameState`: `pending_gather: PendingGather | None`. When the orchestrator/engine schedules a gather, this is set; the next turn the gather fires.

```python
class PendingGather(BaseModel):
    kind: Literal["producer_text", "ceremony", "challenge", "casa_announce"]
    event_id: str
    gather_location: Location
    fires_on_turn: int
```

New action kind: `JOIN_GATHER`. Auto-injected as the only valid action when a gather is pending. Player picks it; the gather resolves.

Note: the "firepit" location is new. Add `FIREPIT` to the `Location` enum.

### Background dialogue visibility

The HTML report already includes background_dialogues per turn but truncates display. Two changes:

1. HTML stylish renderer expands each background dialogue inline by default (the per-turn card shows speaker A line + speaker B line in full, italicized in a muted color).
2. CLI gains a slash command `/background` that prints the last 3 background dialogue exchanges with location and topic.
3. Each day's end auto-prints a "While you were busy" summary listing the day's notable background exchanges (drama-tagged ones, kissed-coded ones).

### Movement liveliness

The Villa Orchestrator prompt currently says "Most turns, most Islanders stay put. A turn with four movements should be unusual." This is too cautious for the small cast. Update to encourage 1-2 movements per turn on average. Plus the per-archetype drift weights become more aggressive:

- Joker / extraverts: 50% movement chance per turn
- Sweetheart / friend / introverts: 25% movement chance per turn

These are now suggestions in the prompt, not hard constraints. The orchestrator decides based on context.

---

## Phase H9.1 — Gender + Same-Sex Dynamics

**Scope.** Add gender to canonical state. Character creation picks it. Filter intent categories by same/opposite sex. New BROMANCE and GOSSIP_RING categories with eight new intents.

### Changes

**State (`state/models.py`):**
- Add `Gender` enum (`MAN`, `WOMAN`).
- Add `gender: Gender` to `PlayerState` and `IslanderState`.
- Bump `SCHEMA_VERSION`.
- Hardcoded cast gender table at `new_game()`: Chloe/Maya/Sophie/Nia/Zara women; Liam/Marcus/Blake/Jordan men. Aisha (bombshell) woman.

**Intent catalog (`content/intents.yaml`):**
- Extend `IntentCategory` enum with `BROMANCE` and `GOSSIP_RING`.
- Add 8 new intents: `bromance_rib`, `bromance_check_in`, `bromance_share_strategy`, `bromance_solidarity`, `gossip_ring_dish_about_him`, `gossip_ring_vent`, `gossip_ring_strategize`, `gossip_ring_alliance`.

**Engine (`engine/intents.py`):**
- `available_intents_for(state, target_id)` filters by gender pair:
  - Opposite sex: include FLIRTY, exclude BROMANCE/GOSSIP_RING.
  - Same sex men: include BROMANCE, exclude FLIRTY/GOSSIP_RING.
  - Same sex women: include GOSSIP_RING, exclude FLIRTY/BROMANCE.

**Character creation (`engine/character_creation.py`, `cli/commands/play.py`):**
- After archetype selection, prompt for gender. Two options: Man / Woman.
- Trace records gender choice as part of character_creation commit.

**Prompts:**
- Claude updates [`islander_voice.md`](../src/game/agents/prompts/islander_voice.md) — the context block already accepts arbitrary fields; the prompt gains a new section "## Gender pair voice":
  - Opposite sex pairs: romantic possibility on the table; tone shifts with category.
  - Same sex same gender (men): bromance — banter, mutual support, scheming about women, occasional ribbing. Avoid romantic subtext.
  - Same sex same gender (women): gossip-y, more emotionally direct, alliance-building, conversations about men in the villa.

### Tests
- `test_gender_required_in_character_creation`
- `test_intent_filter_blocks_flirty_on_same_sex_pair`
- `test_intent_filter_blocks_bromance_on_opposite_sex_pair`
- `test_intent_filter_blocks_gossip_ring_on_men`
- `test_bromance_intent_applies_friendship_delta`
- `test_gossip_ring_intent_applies_trust_delta`
- `test_new_game_assigns_canonical_gender_per_islander`

### Acceptance
- [ ] `make qa` green.
- [ ] `make test-llm` green with the updated islander_voice prompt.
- [ ] `make play` asks for gender during character creation.
- [ ] A man-player talking to Liam never sees FLIRTY options; sees BROMANCE options.
- [ ] A woman-player talking to Chloe sees GOSSIP_RING options instead of FLIRTY.
- [ ] LLM-mark test: with persona=loyal woman-player talking to Maya, the voice produces a gossip-y tone (asserted by tag in the contextual options output).

### Anti-goals
- No removing FLIRTY entirely — opposite-sex flirty stays.
- No procedural gender assignment for cast (hardcoded for v0).
- No bi/gay characters in v0 (future phase).
- No prompt edits Codex authors (R17).

---

## Phase H9.2 — Cast Expansion to 8 Starters

**Scope.** Author 4 new starting islanders (2 men, 2 women). Update `new_game()` to instantiate the full 4-couple cast. Adjust recoupling and audience math for 4 couples.

### Changes

**Content (`content/archetypes/`):**
- 4 existing archetypes (sweetheart, joker, friend, plus add a new `alpha` for ambitious/competitive types).

**Cast (hardcoded in `state/models.py` `new_game()`):**
- Existing: Chloe (sweetheart, woman), Maya (joker, woman), Liam (friend, man), Aisha (bombshell, woman).
- New starters: Sophie (alpha, woman), Nia (sweetheart, woman), Marcus (alpha, man), Blake (friend, man).
- Total starting cast: 4 women + 4 men = 8 islanders. Aisha remains the bombshell that arrives via Casa Amor flow.

Each new islander gets full personality state: Big 5, attachment, Type on Paper, backstory (H9.3 below), archetype prose, gender.

**Engine (`engine/ceremonies.py`):**
- Initial recoupling at Day 1 morning — players pair up. Player picks their initial couple from one of the 4 opposite-sex islanders.
- Audience math scales to 4 couples: ranking is 1/4, 2/4, 3/4, 4/4.

**Casa Amor (`engine/casa_amor.py`):**
- 6 Casa Amor islanders still split 3 men / 3 women. Casting unchanged.

### Tests
- `test_new_game_has_8_starting_islanders`
- `test_new_game_gender_balance_4_men_4_women`
- `test_day1_initial_coupling_offered_to_player`
- `test_recoupling_handles_4_couples`
- `test_audience_ranking_displays_1_of_4`

### Acceptance
- [ ] `make qa` green.
- [ ] `make play` opens with 8 islanders visible across the villa.
- [ ] Initial Day 1 morning includes a coupling ceremony where player picks first.
- [ ] Final vote ranks 4 couples.
- [ ] Scenario fixtures regenerated for the new cast size.

### Anti-goals
- No procedural cast generation. Cast is hardcoded.
- No adjusting Casa Amor cast size (stays at 6).
- No new archetype proliferation. One new (`alpha`) is enough.

---

## Phase H9.3 — Dialogue Specificity

**Scope.** Tighten prompts so dialogue options and NPC responses reference concrete context. Add NPC backstory as a context field.

### Changes

**State (`state/models.py`):**
- Add `backstory: str` to `IslanderState`. Hash-included.
- Hardcoded backstories per islander in `new_game()`.

**Backstory content** (in `state/models.py` factory or moved to `content/backstories.yaml` for editability):

Authored as a YAML catalog `content/backstories.yaml`:
```yaml
backstories:
  chloe: "Twenty-six, primary school teacher from Liverpool..."
  maya: "Twenty-four, content creator from London..."
  liam: "Twenty-seven, carpenter from Cardiff..."
  ...
```

Loaded by `content/loader.py`. Lint validates one backstory per islander.

**Prompts (Claude rewrites):**

1. [`contextual_options.md`](../src/game/agents/prompts/contextual_options.md) — tighten label specificity:
   - Add new hard rule: "Labels must reference something specific from the last NPC line, the conversation history, the islander's revealed Type on Paper, or their backstory. Generic labels ('Ask something deeper', 'Tell a joke') are wrong. Specific labels ('Ask why she really came on the show', 'Joke about his Cardiff accent') are right."
   - Add example block showing 4 good vs 4 bad labels.

2. [`islander_voice.md`](../src/game/agents/prompts/islander_voice.md) — forbid meta-conversation:
   - Add new hard rule: "Do not write meta-conversational dialogue. 'I'm enjoying our chat' or 'It's nice talking to you' are wrong. Talk about specific things: your backstory, the villa, other islanders, plans, doubts, opinions about people."
   - Add: "Pull from the provided backstory — reference one concrete detail per exchange when natural."

**Context (`agents/islander_voice.py`):**
- `IslanderVoiceContext` gains `npc_backstory: str` and `recent_exchange_topics: list[str]` (extracted from the conversation's accumulated_tags).
- Builder passes both into the rendered context.

### Tests
- `test_islander_voice_context_includes_backstory`
- `test_backstory_loaded_per_islander`
- LLM (mark llm):
  - `test_islander_voice_avoids_meta_talk` — assert dialogue does not contain phrases like "our conversation", "talking with you", "this chat"
  - `test_contextual_options_labels_are_specific` — assert labels are not in a blocklist of generic phrases

### Acceptance
- [ ] `make qa` green.
- [ ] `make test-llm` green; new specificity assertions pass.
- [ ] Hand-eyeball check: 10 sampled labels from a recorded session are all specific (reference an islander, a backstory bit, a recent moment, or a current decision).
- [ ] Hand-eyeball check: 10 sampled exchanges contain at least one concrete topic from the NPC's backstory or the villa.

### Anti-goals
- No automated dialogue grading via LLM judge. Manual sampling is the check.
- No procedural backstory generation. Hardcoded per islander.
- No prompt edits Codex authors (R17). Claude rewrites both prompts.

---

## Phase H9.4 — Pull Cooldown + Interruption Walkaway

**Scope.** Failed pulls compound retry penalty. Ignored interrupters move to a different location immediately.

### Changes

**State (`state/models.py`):**
- Add `pull_attempts_this_phase: dict[str, int]` to `PlayerState`. Reset on phase advance.

**Engine (`engine/pull.py`):**
- `pull_chance` subtracts `15 × pull_attempts_this_phase.get(target_id, 0)`.
- After a pull attempt resolves (hit or miss), increment `pull_attempts_this_phase[target_id]`.
- After 2 failed pull attempts on the same target, generate a memory on the target: holder=target_id, subject=player, content="Player kept pulling me away today — felt a bit much", weight=6, tags=["player_kept_pulling"]. Algorithmic memory; no LLM call.

**Engine (`engine/phases.py`):**
- On `advance_phase`, reset `state.player.pull_attempts_this_phase = {}`.

**Engine (`engine/interruptions.py`):**
- `_apply_interruption_response` for `ignore_interruption`: after applying -4 affection and the `ignored_in_public` memory, immediately move the interrupter to a random other location. Uses `rng.choice([loc for loc in Location if loc != interrupter.location_id])`.
- Trace records the movement as part of the interruption resolution.

### Tests
- `test_pull_chance_drops_with_repeated_attempts`
- `test_three_failed_pulls_clamped_near_minimum`
- `test_pull_attempts_reset_on_phase_advance`
- `test_repeated_pull_creates_clingy_memory`
- `test_ignore_interruption_moves_interrupter_away`
- `test_ignore_interruption_trace_records_movement`

### Acceptance
- [ ] `make qa` green.
- [ ] After failing a pull, the second pull on same target shows a visibly lower chance in the math breakdown.
- [ ] Three failed pulls in same phase generates a `player_kept_pulling` memory on the target.
- [ ] After ignoring an interruption, the interrupter's location is different in the next turn's villa snapshot.

### Anti-goals
- No "pull harder" stat-buy mechanic. The cooldown is structural.
- No removing the existing pull math. The cooldown extends it.

---

## Phase H9.5 — Gather Events

**Scope.** Producer texts and ceremonies force-close all active conversations and move everyone to a designated gather location. Player must engage with the event (no opt-out).

### Changes

**State (`state/models.py`):**
- Add `FIREPIT` to `Location` enum.
- Add `PendingGather` Pydantic model.
- Add `pending_gather: PendingGather | None` to `GameState`.

**Engine (`engine/actions.py`):**
- Add `JOIN_GATHER` action kind.
- `available_actions(state)`: when `pending_gather is not None`, the only valid action is `JOIN_GATHER`.

**Engine (`engine/turn.py`):**
- On producer text fire (existing producer_events.py logic): set `state.pending_gather = PendingGather(kind="producer_text", event_id=..., gather_location=FIREPIT, fires_on_turn=current_turn+1)`.
- On ceremony fire (recoupling, bombshell, final vote, Casa Amor): same — set `pending_gather`.
- On `JOIN_GATHER` action:
  - Close all active conversations (player and NPC-NPC) with reason `gather_event`. Curator runs on each.
  - Move all islanders + player to `gather_location`.
  - Trigger the actual event (Event Narrator narration, mechanical resolution).
  - Clear `pending_gather`.
  - Deduct the event's time_cost from `phase_clock`.

**Engine (`engine/producer_events.py`):**
- Replace direct producer text firing with `set_pending_gather` calls.

**Engine (`engine/ceremonies.py`):**
- Same — ceremonies set pending_gather instead of firing inline.

**CLI (`cli/commands/play.py`):**
- When `pending_gather is not None`, the action menu shows only `JOIN_GATHER` with a label like `"Everyone gathers at the firepit"`. No other options.
- Player presses it; the event narrates, then play resumes.

**HTML (`reporting/html_blocks.py`):**
- Gather turns get a distinct card style (full-width, dramatic) showing the gather location, the event narration, and "Everyone moved to the firepit."

### Tests
- `test_producer_text_sets_pending_gather`
- `test_ceremony_sets_pending_gather`
- `test_pending_gather_locks_other_actions`
- `test_join_gather_closes_active_player_conversation`
- `test_join_gather_closes_active_npc_npc_conversations`
- `test_join_gather_moves_everyone_to_gather_location`
- `test_join_gather_resolves_event_and_clears_pending`
- `test_join_gather_advances_phase_clock`

### Acceptance
- [ ] `make qa` green.
- [ ] In `make play`, when a producer text fires while in conversation, the conversation closes and the next action menu shows only `Join gather at the firepit`.
- [ ] After joining the gather, all islanders are at the firepit in the visible state.
- [ ] After the event resolves, play continues normally.
- [ ] Ceremonies (recoupling, bombshell, final vote) all gather everyone before firing.

### Anti-goals
- No skipping gather events. Player cannot decline.
- No partial gather (some islanders stay behind). Everyone moves.
- No gather lasting multiple phases. Resolves in one turn.

---

## Phase H9.6 — Background Visibility

**Scope.** Background dialogue fully visible in HTML report. CLI slash command `/background`. Daily "what you missed" summary.

### Changes

**HTML (`reporting/stylish/timeline.py`):**
- Each turn card with background_dialogues expands the dialogues inline by default. Render speaker A and speaker B lines in full, italicized in muted gray with location and topic.

**CLI (`cli/commands/play.py`):**
- New slash command `/background` — prints the last 3 background exchanges from the trace history with location, participants, and topic.

**Engine (`engine/turn.py`):**
- At each day rollover (phase wraps to morning of next day), generate a `daily_recap: DailyRecap` containing the day's notable background exchanges (top 5 by emotional weight from associated memories). Store on `GameState.daily_recaps: list[DailyRecap]`.
- Hash-included structurally; content (the prose lines) hash-excluded.

**CLI (`cli/commands/play_render.py`):**
- At day rollover, print the daily recap automatically: "While you were busy yesterday: Maya and Liam shared a moment at the pool. Aisha was telling Marcus about her ex..."

**HTML (`reporting/stylish/timeline.py`):**
- Each day's section starts with the daily recap as a dedicated panel.

### Tests
- `test_background_dialogues_render_full_text_in_html`
- `test_cli_background_command_prints_last_three`
- `test_daily_recap_generated_at_day_rollover`
- `test_daily_recap_picks_top_5_by_weight`

### Acceptance
- [ ] `make qa` green.
- [ ] HTML report shows background dialogue full text per turn.
- [ ] `/background` slash command works in `make play`.
- [ ] At each day rollover, a "While you were busy" recap prints in CLI and renders in HTML.

### Anti-goals
- No live-streaming background dialogue between turns. Players see it as part of the turn render.
- No interactive expansion of background dialogue from the player.

---

## Phase H9.7 — Movement Liveliness

**Scope.** Update villa_orchestrator prompt for more frequent movement. Tune archetype drift weights.

### Changes

**Prompt (Claude rewrites):**
- [`villa_orchestrator.md`](../src/game/agents/prompts/villa_orchestrator.md): Update the "How to decide → Movement" guidance:
  - Replace "Most turns, most Islanders stay put. A turn with four movements should be unusual." with: "Movement should feel like a living villa. On most turns, expect 1-2 islanders to move based on chemistry, drama, or restlessness. Extraverts (Big 5 E ≥ 7, jokers, alphas) drift roughly every other turn. Introverts (Big 5 E ≤ 5, friends) drift less. Islanders mid-conversation rarely move (only if pulled or summoned)."
- Add: "An empty villa is dead. If the player has been alone in a location for two consecutive turns, gently pull an islander toward them based on chemistry."

**State (`state/models.py`):**
- No state changes; movement is orchestrator-driven.

**Engine (`engine/villa.py`):**
- Add validation that movements still respect existing constraints (not during ceremonies, not for eliminated islanders).

### Tests
- LLM (mark llm):
  - `test_orchestrator_produces_at_least_one_movement_per_two_turns_avg` — across 6 mock-context calls, average movements per turn is ≥ 0.5.
  - `test_orchestrator_draws_npc_toward_isolated_player` — when player has been alone for 2+ turns, output includes a movement toward player's location.

### Acceptance
- [ ] `make qa` green.
- [ ] `make test-llm` green; movement frequency assertions pass.
- [ ] In a real-LLM playthrough, the trace shows averaged ≥ 1 movement per turn across a 6-day run.
- [ ] Hand-eyeball: in `make play`, the villa map shifts visibly each turn.

### Anti-goals
- No forced movement. The orchestrator decides; we just guide its priors.
- No removing the existing 4-movement cap per turn. Pacing matters.

---

## Prompt updates Claude owns (pre-written here)

### Update for `contextual_options.md` (H9.3)

Insert after the existing "Hard rules" block:

```markdown
## Specificity

Generic labels are wrong. Labels must reference something concrete:

- The Islander's last line ("Ask what she means about her ex")
- A topic from earlier in the conversation ("Push the Marcus question further")
- A revealed Type on Paper bit ("Compliment her ambition")
- A villa event the Islander has memories about ("Bring up the kitchen drama")
- The Islander's backstory if it's been referenced ("Ask about the carpentry job")

**Wrong:** "Ask something deeper", "Tell a joke", "Be supportive", "Get vulnerable".
**Right:** "Ask why she really came on the show", "Joke about his Cardiff accent", "Tell her you saw her at the kitchen", "Open up about your own ex".
```

### Update for `islander_voice.md` (H9.3)

Insert after the existing "Honoring the outcome" block:

```markdown
## What to talk about

Talk about specific things from the Islander's life and the villa, not about the conversation itself.

**Pull from:**
- The Islander's backstory (provided in context).
- Other islanders by name — relationships, drama, alliances, opinions.
- Villa events that just happened — the recoupling, the bombshell, the challenge.
- Plans, doubts, hopes, opinions.
- Body language and reactions to specific moments.

**Don't write:**
- "I'm enjoying our chat", "It's nice talking to you", "I really like our conversations" — meta-conversational dialogue.
- "What are you thinking?", "How do you feel about us?" — vague check-ins. If you ask, ask about something concrete.

Reference one specific backstory detail per Islander reply when it fits naturally. The player's character should feel like they're learning who this person is.
```

### Update for `villa_orchestrator.md` (H9.7)

Replace the "Movement" bullet under "How to decide" with:

```markdown
- **Movement.** A living villa drifts. On most turns, 1-2 islanders move based on chemistry pull, drama, restlessness, or seeking quiet. Extraverts (Big 5 extraversion ≥ 7, archetypes joker and alpha) drift roughly every other turn. Introverts (extraversion ≤ 5, archetypes friend and sweetheart) drift less. Islanders in active conversations rarely move unless summoned. If the player has been alone in a location for two consecutive turns, gently pull an islander toward them based on chemistry.
```

### Update for `islander_voice.md` (H9.1) — gender pair voice

Insert before "## Context":

```markdown
## Gender pair voice

The user message tells you the Islander's gender and the player's gender. Adjust the voice:

- **Opposite-sex pair (man↔woman).** Romantic possibility is on the table. Flirty intents carry weight. Tone shifts noticeably between Friendly (warm, neutral), Flirty (charged), Deep (vulnerable, intimate), Banter (playful).
- **Same-sex men.** Bromance dynamic — banter-heavy, mutually supportive, occasional ribbing, sometimes scheming about the women in the villa. Avoid romantic subtext. Lines like "I got you" and "she's into you, mate" feel right.
- **Same-sex women.** Gossip-y, emotionally direct, alliance-building, conversations about the men in the villa, the bombshells, who's playing who. Vulnerability without romantic weight. Lines like "I have to tell you what Marcus said" feel right.

Stay in the Islander's archetype voice within these patterns — Chloe gossips warmly, Maya gossips with edge, Sophie gossips strategically.
```

---

## Done checklist for Codex

### H9.1 — Gender + Same-Sex Dynamics
- [ ] Wait for Claude's prompt update for islander_voice (gender pair voice section)
- [ ] Install verbatim per R17
- [ ] Add `Gender` enum, `gender` field to PlayerState and IslanderState
- [ ] Bump `SCHEMA_VERSION`
- [ ] Add 8 new intents to `content/intents.yaml`
- [ ] Extend `IntentCategory` with BROMANCE and GOSSIP_RING
- [ ] Update `available_intents_for` with gender-pair filtering
- [ ] Wire gender pick into character creation
- [ ] Regenerate all scenario fixtures
- [ ] Write tests listed above
- [ ] Run `make qa`, `make test-llm`
- [ ] Append build log
- [ ] Commit: `Phase H9.1: gender and same-sex dynamics`

### H9.2 — Cast Expansion
- [ ] Author 4 new islanders (Sophie, Nia, Marcus, Blake)
- [ ] Add `alpha` archetype content file
- [ ] Update `new_game()` cast
- [ ] Add Day 1 initial coupling ceremony
- [ ] Adjust audience ranking for 4 couples
- [ ] Update Casa Amor cast accordingly (still 6 split 3/3)
- [ ] Regenerate scenario fixtures
- [ ] Tests
- [ ] Run `make qa`, `make test-llm`
- [ ] Commit: `Phase H9.2: cast expansion to 8 starters`

### H9.3 — Dialogue Specificity
- [ ] Wait for Claude's updated contextual_options and islander_voice prompts (specificity sections)
- [ ] Install verbatim per R17
- [ ] Add `backstory: str` to IslanderState
- [ ] Author `content/backstories.yaml` with 9 backstories (8 starters + Aisha)
- [ ] Extend content loader and lint
- [ ] Extend IslanderVoiceContext with `npc_backstory`
- [ ] Tests including LLM-marked meta-talk assertions
- [ ] Run `make qa`, `make test-llm`
- [ ] Commit: `Phase H9.3: dialogue specificity and NPC backstory`

### H9.4 — Pull Cooldown + Interruption Walkaway
- [ ] Add `pull_attempts_this_phase` to PlayerState
- [ ] Extend pull_chance math
- [ ] Reset on phase advance
- [ ] Generate clingy memory on 2+ failed pulls
- [ ] Update interruption ignore to move interrupter
- [ ] Tests
- [ ] Run `make qa`, `make test-llm`
- [ ] Commit: `Phase H9.4: pull cooldown and interruption walkaway`

### H9.5 — Gather Events
- [ ] Add FIREPIT location
- [ ] Add PendingGather model
- [ ] Add JOIN_GATHER action kind
- [ ] Wire producer texts and ceremonies through pending_gather
- [ ] Update CLI menu to lock to JOIN_GATHER when pending
- [ ] Move everyone to gather_location on join
- [ ] Update HTML for gather card style
- [ ] Tests
- [ ] Run `make qa`, `make test-llm`
- [ ] Commit: `Phase H9.5: gather events`

### H9.6 — Background Visibility
- [ ] HTML expands background dialogue inline
- [ ] CLI `/background` slash command
- [ ] Daily recap at day rollover
- [ ] Tests
- [ ] Run `make qa`, `make test-llm`
- [ ] Commit: `Phase H9.6: background visibility`

### H9.7 — Movement Liveliness
- [ ] Wait for Claude's villa_orchestrator prompt update (movement section)
- [ ] Install verbatim per R17
- [ ] LLM tests for movement frequency
- [ ] Run `make qa`, `make test-llm`
- [ ] Commit: `Phase H9.7: movement liveliness`

### After all seven commit

- [ ] Run one real-LLM autopilot session each persona, seed 42: loyal + chaotic
- [ ] Run one real-LLM manual session by user
- [ ] Generate packets for all three
- [ ] User reviews all three packets
- [ ] Claude reads the same packets and writes a qualitative review

---

## Global anti-goals (H9-specific)

- ❌ No procedural NPC generation. Cast is hardcoded.
- ❌ No bi/gay characters in v0 (future phase).
- ❌ No automated LLM dialogue grading. Manual sampling + structural assertions.
- ❌ No new agents.
- ❌ No prompt edits Codex authors (R17). Claude owns all prompt updates listed above.
- ❌ No deviating from the per-sub-phase commits — each is independently reviewable.

---

## What this phase produces

After H9 commits:

1. The villa feels populated (8 islanders, drift every turn, multiple ongoing background convos visible).
2. Same-sex dynamics work — flirting with the wrong gender is impossible by design, bromance/gossip-ring categories give same-sex pairs their own voice.
3. Dialogue references specific things (backstories, prior moments, other islanders, villa events). Meta-talk is suppressed by prompt.
4. Pull-for-chat doesn't reward spam. Interruptions actually walk away when ignored.
5. Events break the loop — when a producer text or ceremony fires, conversations close and everyone gathers at the firepit. Player must engage.
6. Background visibility lets the player see the rest of the villa's life through HTML, slash commands, and daily recaps.

This is the phase where the game stops being a tech demo and becomes a thing you'd play through twice.
