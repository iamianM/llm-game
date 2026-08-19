# Engine Issues — Review-Packet Findings (H11 Loyal Run)

Historical playtest note. This file preserves the findings from the H11 loyal
run review, but it is not the active backlog. Use
[current-plan.md](current-plan.md) for current priorities and update the owning
system docs when a behavior changes. If a detail here conflicts with present
code or current docs, present code/current docs win.

A pass over `.game_traces/h11-loyal.json` rendered in the redesigned review packet
surfaced behaviors that are correct-per-spec but visibly wrong in play. This is a
working list for the next engine iteration. Each item is grouped by area, with
**Observation** (what the trace shows), **Root cause** (where in the engine), and
**Proposed fix** (suggested approach — open to discussion).

The renderer was deliberately straightened out first so these gaps are now visible
rather than hidden by UI fictions. Where the renderer was *compensating* for an
engine bug, that's noted too.

---

## Codex sequencing

Decisions confirmed with the project owner. Phase 1 is the foundation, Phase 2
adds the steal/spark drama mechanics that depend on Phase 1 state existing.

### Phase 1 (foundation — build in this order)

1. **Remove `advance_phase`, add ambient actions** — §9b
2. **NPC couples in state + Day-1 matching algorithm** — §4
3. **Curator runs at conversation end (any end trigger)** — §3
4. **Day-1 intros segment** — §6
5. **Audience signaling (3-way hints + post-action chips)** — §11 + §12 + new §13
6. **Producer/narrator prompt richness** — §7 + §10 (slot in opportunistically; low blocking)

### Compatibility policy

**No backwards compatibility required.** Confirmed with the project owner:

- Bump `SCHEMA_VERSION` freely as state shapes change.
- All `tests/scenarios/fixtures/*.yaml` get regenerated with each PR; the
  `make verify` hash baseline moves alongside.
- All `.game_traces/*.json` are throwaway. Existing traces will not replay
  after schema changes; regenerate fresh ones as part of each PR's review
  packet.
- `ActionKind` values can be deleted (e.g. `ADVANCE_PHASE`) without alias
  shims. CLI flags, prompts, and content can drop references in the same PR.
- Deprecated code paths can be removed wholesale; no transition period.

### Phase 2 (drama mechanics — after Phase 1 lands)

7. **Player-initiated Pairing Ceremony proposal** — new §14
8. **NPC-initiated Pairing Ceremony proposal** — new §14
9. **Singles handling** (no auto-pair after a steal; organic drift via background) — new §14

### Phase 3+ (polish, defer until core feels right)

10. Challenge minigames — §8 (big)
11. Finale structure — §11
12. Audience trajectory analytics — §12 extras
13. Day-1 ceremony renamed in engine — §1 (currently renderer-only)
14. Phase anchors as engine config — §2

---

## 1. Day-1 ceremony is named "Pairing Ceremony"

**Observation.** The first ceremony on Day 1, turn 1, fires with
`ceremony_events: [{kind: "pairing", message: "Pairing Ceremony completed."}]`.
On the show, Day 1 is the **opening coupling** — first pairings from a lineup, not
a re-pairing. The renderer translates the label for Day 1 only, but the engine
event kind is the same as later ceremonies.

**Root cause.** `src/game/engine/ceremonies/` reuses the `pairing` event kind
for both first coupling and subsequent Pairing Ceremonies. Downstream code (audience
weighting, drama generation, narrator prompt) treats them identically.

**Proposed fix.** Introduce a distinct `opening_coupling` ceremony kind used on
Day 1 only. Lets the narrator prompt and audience weighting differ ("everyone is
meeting for the first time" vs "people are breaking established couples").

---

## 2. Phase budgets exist but anchor times don't

**Observation.** `phase_clock.elapsed_minutes` is real engine data (e.g. T5
afternoon elapsed=20 after a 20-min `start_conversation`). The renderer can
compute readable clocks using documented anchor times (morning=09:00,
afternoon=14:00, text=18:00, evening=20:00). But the engine has no canonical
anchor — the renderer picked them.

**Root cause.** `engine/phases.py` and `engine/time_budget.py` only track
*elapsed within a phase* and a *budget*, not a wall-clock anchor.

**Proposed fix.** Add `phase_anchor_minutes` to the `Phase` enum or a sibling
config and have `phase_clock` expose `wall_clock(minutes)` as engine API.
Renderer drops its anchor constants. Cleaner story for NPC behavior too —
"it's late and people are tired" becomes a real signal.

**Side note.** The phase budgets (120/0/120/30/60 = 5h30) don't tile a 24h day.
Gaps between phases (11:00→14:00, 16:00→18:00, 18:30→20:00) are unmodeled day
time. This is fine for a roguelite, but should be acknowledged: the UI shows
these gaps honestly rather than smoothing them over.

---

## 3. Curator runs on every turn, not at conversation end

**Observation.** Every turn's `agent_commits.curator_batches` contains 1–2
batches. Turn 5 (a player `start_conversation`) has a batch for a *background*
Chloe/Jordan pool chat that ended that turn. Turn 7 (the player's `end_softly`)
has the player batch *plus* a background Marcus/Blake batch. Memories get
emitted continuously instead of at conversation boundaries.

**Root cause.** `engine/turn.py` lines around 226 and 287–365: the curator is
called per-turn for any conversation that has ended that turn (player or
background). The agent runs every turn that has an `end_conversation` action OR
that has background dialogue that wrapped — but the per-turn cadence creates the
volume.

**Decision.** Curator fires once per conversation, at *any* end trigger:

| Trigger | Source |
|---|---|
| Player picks an exit intent (end_softly / walk_away) | `apply_action` resolves exit kind |
| NPC ends the conversation themselves | heartbreaker_voice signals `npc_departure` |
| NPC interrupted away by orchestrator | `resort_update.npc_summoned_elsewhere` includes the active conversation's target |
| Conversation cut by event (gather scheduled, ceremony fires) | phase/ceremony resolver closes active conversation |
| Phase budget expires mid-conversation | `auto_advance` closes any open conversation |

In all cases, the curator gets a single batch's worth of input (the full
conversation transcript + state at end) and emits one batch.

**Implementation.**
- Move the curator call out of per-turn `run_turn` into the conversation-end
  resolver(s).
- For background conversations, fire the curator when a specific
  `conversation_ends` event lands in `resort_update`, scoped to that one
  conversation.
- Single batch per conversation. No more "two batches in one turn's commits"
  cases — each batch corresponds to one closed conversation.

**Renderer cleanup once fixed.** The renderer's "is_player_batch via direct
source + holder/subject == player" filter (`scene_renderers._is_player_batch`)
can be replaced with a simple `batch.kind == "player"` check.

---

## 4. NPC↔NPC couples are not in state

**Observation.** `final_state.couples` only contains the player couple.
`audience_snapshot.entries` at end of game has a single entry. The Marcus↔Zara,
Liam↔Sophie, etc. couples that *exist conceptually* (the show requires everyone
be coupled) aren't represented as data.

**Root cause.** The `couples` model in `src/game/state/models.py` (or wherever
`Couple` lives) is populated only by player `pair` actions. NPC pairings
formed by the Producer/Pairing Ceremony aren't materialized.

### Day-1 opening coupling flow

1. Player picks first from all opposite-gender (or as-configured) non-partner
   heartbreakers. Existing `PAIR` action handles this.
2. After the player's pick is locked, the engine runs **greedy
   compatibility-based matching** for the remaining 6 NPCs:

   ```
   def match_remaining_npcs(state) -> list[Couple]:
       remaining = [npcs not yet coupled]
       scored = []
       for (a, b) in opposite_gender_pairs(remaining):
           score = compatibility_score(a, b)
           # compatibility_score combines:
           #   - Type-on-Paper match (each NPC scores the other against their TOP)
           #   - Big-5 personality compatibility (esp. extraversion / agreeableness)
           #   - Tiny seeded jitter so identical-stat NPCs don't always pair the same way
           scored.append(((a, b), score))
       scored.sort(by=score, descending=True)
       couples = []
       paired = set()
       for (a, b), score in scored:
           if a.id in paired or b.id in paired:
               continue
           couples.append(Couple(a, b, formed_on_day=state.day))
           paired |= {a.id, b.id}
       return couples
   ```

3. All NPC couples written to `state.couples` alongside the player couple.

### Subsequent Pairing Ceremonies

For Day-3+ forced Pairing Ceremonies, the same algorithm runs but with relationship
state mixed in:

```
score = (
    0.20 * type_on_paper_match
  + 0.20 * personality_compatibility
  + 0.40 * chemistry(a, b)          # accumulated state matters more by now
  + 0.20 * affection(a, b)
)
```

Player picks first (as today). Then the algorithm pairs the rest.

### Singles after a player-initiated steal (Phase 2)

When the player triggers a Pairing Ceremony proposal (§14) and steals a partner,
the two left-behind NPCs become **single** — they do NOT auto-pair. This is
deliberate and show-accurate. See §14 for how singles drift.

### Schema

```python
class Couple:
    partner_a_id: str
    partner_b_id: str
    formed_on_day: int
    formed_via: Literal["opening", "ceremony", "flush_return", "proposal"]
    has_used_private_suite: bool = False
    rebound: bool = False  # True if formed after a steal (lower base appeal)
```

Add to heartbreakers:

```python
class Heartbreaker:
    ...
    coupled: bool   # derived from state.couples membership; or a couple_id field
```

### Why this matters

Required to unblock:
- Audience ranking of all couples (issue #12, §13)
- Flush of Hearts partner-swapping with real consequences
- Dumping stakes ("lowest-ranked couple is at risk" needs all couples ranked)
- Right-rail Couples panel showing the whole field
- Pairing Ceremony proposal (§14) — you can't steal what isn't there

---

## 5. Autopilot coasts on `friendly_ask_feelings → end_softly`

**Observation.** 18 of 75 turns are `start_conversation` and 12 of those target
Chloe. The loyal autopilot uses `friendly_ask_feelings` to open and `end_softly`
to close, almost every conversation. The player never has substantive
interactions with Liam, Sophie, Jordan, Marcus, Blake, Zara, or Nia until Flush of Hearts
Amor (which is forced).

**Root cause.** The autopilot's persona heuristic in
`src/game/agents/player_autopilot.py` (or similar) weighs partner-target very
heavily for the "loyal" persona, with no diversity counter.

**Proposed fix.** Add a per-day quota to all personas: "must talk to ≥ N
distinct heartbreakers before defaulting to partner" (N=3 day 1, N=2 days 2-3, N=1
later). Persona still flavors which option to pick *once* the target is
selected.

**Renderer note.** This is the most "this game has a problem" issue the user
hit. Right-rail Cast panel now makes it obvious that 6 of 8 heartbreakers are
unfamiliar by Day 3.

---

## 6. No Day-1 onboarding / introductions

**Observation.** Day 1 flow: opening coupling → 1 pull (failed) → compatibility
quiz → 3-turn chat with Chloe → producer text → evening chat. Player only meets
Chloe before challenges begin. In the show, Day 1 is mostly mingling.

**Root cause.** No scripted "introduction round" in `engine/phases.py` or
elsewhere. After coupling, the phase clock starts and the player is left to
their own devices.

### Day-1 intros segment — final spec

**When.** Triggered automatically after Day-1 opening coupling completes,
before the first challenge phase begins. Forced — player cannot skip.

**Mechanic.** The action menu becomes a constrained list:

```
Introduce yourself to:
  1. Liam (flame_deck)
  2. Marcus (kitchen)
  3. Jordan (pool)
  4. Sophie (terrace)
  5. Maya (bedroom)
  6. Nia (kitchen)
  7. Blake (pool)
```

Player picks them in any order. Each pick opens a **mini-conversation**:

- **Player picks dynamic** from a small no-fail menu:
  - **Friendly** — warm, safe opener
  - **Flirty** — playful, suggestive
  - **Deep** — vulnerable, sincere
  - **Banter** — jokes, teasing
- Heartbreaker Voice agent generates the NPC's response, flavored by their
  personality + the chosen dynamic
- One more exchange (player picks a follow-up dynamic, NPC responds)
- **NPC ends the conversation** after the second exchange ("Cool — catch you
  later") and the engine advances to the next intro slot

**No fail state.** These intros can't miss; they're foundation-setting, not
skill checks.

**What they set.**
- `familiarity[player→npc]` jumps from 0 to ~25 (unlocks Type-on-Paper
  physical_type reveal in the cast popout)
- The chosen dynamic locks in a **baseline relationship dimension**: choosing
  "Flirty" with Maya bumps her chemistry by 10–15 and tags the relationship
  as "flirty-leaning"; "Deep" bumps trust + affection; etc.
- The autopilot's future contextual options for that NPC will favor the
  dynamic the player established (e.g. flirty openers if the foundation was
  flirty)

**Cost.** Each mini-conversation = 1 turn (20 min for the opener + 5 min for
the second exchange ≈ 25 min total). Seven intros ≈ 3 hours. Sits in Day-1
afternoon with budget headroom.

**Curator.** One batch fires at the **end of the entire intros segment**, not
per-mini-conversation. Emits one memory per NPC (capturing the dynamic the
player chose). Tests the new conversation-end curator pattern from §3 at small
scale.

**Implementation.**
1. New phase value: `Phase.INTROS` or sub-phase flag. Triggered after
   `Phase.MORNING` Day-1 ceremony completes (instead of going to
   `Phase.CHALLENGE`).
2. Action menu while in intros phase: only the seven `INTRODUCE_TO` options,
   no `MOVE`, no ambient, no other actions.
3. Each intro = a constrained `start_conversation` with a special intent
   category (4 dynamics, all `risk=low`, all `cannot_fail=True`).
4. Hard 2-exchange cap. NPC ends with a fixed closing.
5. After all 7 done, phase advances to `Phase.CHALLENGE`.

**Renderer impact.** The intros segment renders as a single "Day 1 — meeting
everyone" scene with all 7 mini-conversations stacked. Or as 7 small
sub-scenes within a parent. Pick whichever reads better; the data structure
supports either.

---

## 7. Narrator prose is one-sentence and generic

**Observation.** Day 1 opening coupling narration: *"The heartbreakers gather by the
pool, the tension thick as the first Pairing Ceremony unfolds. Without a
single name called…"* — one sentence, doesn't say who picked whom, no specific
reactions, no setup for the next beat.

**Root cause.** The Event Narrator agent prompt in `src/game/agents/` produces
a single `prose` string with no structural requirement.

**Proposed fix.** Restructure the narrator output to a schema:
```python
class EventNarration:
    setup: str           # "Everyone gathered around the flame_deck at dusk..."
    beats: list[str]     # who chose whom, with reactions ("Marcus stepped forward and picked Zara...")
    reactions: dict[str, str]  # per-heartbreaker notable reactions
    hook: str            # closing line that sets up the next phase
```
The renderer can lay each section out with appropriate prominence.

---

## 8. Challenges are single dice rolls, no minigame

**Observation.** All six challenge kinds (compatibility quiz, heart rate, Mr &
Mrs, lie detector, kiss/wed/pass, final couples) resolve as
`MechanicalResult` with a single roll vs target chance. No questions, no
ranking, no per-NPC reveals.

**Root cause.** `engine/challenges.py` (or similar) treats the challenge as a
stat check.

**Proposed fix.** Out of scope for v0 but worth flagging. Each challenge kind
should produce reveals (compatibility quiz: NPCs' Type on Paper inferences;
heart rate: who set whose heart racing — reveals chemistry deltas; The Couples Quiz:
exposes how well couples know each other → affects couple strength).

---

## 9. `auto_advance` is recorded but always False in the trace

**Observation.** Every record has `auto_advance: False`. The autopilot is
explicitly calling `advance_phase` to skip the rest of phase budgets, never
running them out. See also issue #9b below — this is a symptom of #9b.

**Root cause.** Either the time budget logic isn't being hit (autopilot too
fast) or the field is only set in some path.

**Proposed fix.** Verify `check_auto_advance` is being called and the result
captured. With #9b applied, `auto_advance` should fire on most phase
transitions.

---

## 9b. Replace `advance_phase` with location-aware ambient actions

**Observation.** `advance_phase` fires 29 times in 75 turns of the loyal trace
— literally every phase transition. The autopilot ends afternoon at 30/120 min
(after one conversation), skips the remaining 90 min for zero cost, jumps to
text phase. This is why the player only meets Chloe and never has time to find
other heartbreakers.

**Root cause.** `engine/actions.py:197` unconditionally appends
`ADVANCE_PHASE` to `available_actions()`. Cost in `engine/time_budget.py:21`
is 0. Both autopilot and humans can pick it; the autopilot uses it as a
default exit.

### Decision: remove `advance_phase` entirely; replace with ambient actions

Phases advance only via:
- The phase time budget expiring (`auto_advance` already implemented)
- A forced ceremony event (producer text, Pairing Ceremony, etc.)
- (Safety net) After N consecutive turns where the player has zero
  meaningful options available — engine auto-advances to avoid soft-lock

A real player should never need to skip a phase. They should always have
something to *do*, even if it's not a conversation. That's what ambient
actions are for.

### Ambient action design

When the player is not in an active conversation, the action menu includes
**location-specific ambient options** alongside the existing options (start
conversation, move, join gather if pending, etc.). These let the player burn
phase time meaningfully when they don't want to start a chat.

**Schema.** New `ActionKind.AMBIENT`. Action carries `target_id = ambient_id`.
Each ambient option lives in content (e.g. `content/ambient.py`) and has:

```python
class AmbientOption:
    id: str                        # e.g. "pool_swim"
    location_id: Location          # which location it's available in
    label: str                     # "Swim in the pool"
    category: str                  # "relax" | "fitness" | "appearance" | "kitchen" | "reflect"
    time_cost: int                 # minutes consumed from phase clock
    mood_effect: str | None        # "relaxed" | "energized" | "anxious" | None
    stat_trickle: dict[str, int]   # {"charm": 1} — small bumps
    npc_encounter_boost: int       # 0–30, added to resort orchestrator's
                                   # P(NPC initiates chat with player) for this turn
```

**Per-location defaults** (illustrative — needs balancing):

| Location | Option | Cost | Mood | Stat | Encounter |
|---|---|---|---|---|---|
| Pool | Swim | 20m | energized | +1 charm | +15 |
| Pool | Sunbathe | 30m | relaxed | +1 charm | +20 |
| Pool | Listen to music | 15m | chill | — | +5 |
| Kitchen | Make a snack | 15m | nourished | — | +15 |
| Kitchen | Tidy up | 20m | content | — | +10 |
| Terrace | Sit and think | 20m | reflective | — | +5 |
| Terrace | Stretch | 15m | energized | +1 spark | +10 |
| Bedroom | Get ready | 30m | confident | +1 charm | +5 |
| Bedroom | Nap | 60m | rested | — | 0 |
| Flame Deck | Sit by the fire | 25m | reflective | — | +20 |
| Flame Deck | Watch the stars | 15m | reflective | — | +10 |
| Gym (if added) | Work out | 30m | energized | +1 spark | +15 |
| Gym | Stretch | 15m | energized | +1 spark | +5 |

### Mechanics integration

1. **Time costs use the chat cost model** — `start_ambient` = 20 min (same as
   `start_conversation`), `stay_in_ambient` = 5 min (same as `respond_with`).
   This means the first turn of an ambient action burns a real chunk, and
   subsequent "stay in" turns are cheap. Pattern:
   - T1: "Go in the pool" → 20 min, mood/stat applied, encounter chance rolled
   - T2: "Stay in the pool" → 5 min, smaller mood reinforce
   - T3: "Stay in the pool" or switch to "Get out and dry off" (free action
     that ends the ambient context)
   - Player can also start a new ambient or leave to another location

2. **Mood/stat effects** are small per-action and rate-limited (max +1 per
   stat per phase, max one mood update per turn).

3. **NPC encounter** — `npc_encounter_boost` is consumed by Sunset Bay
   orchestrator on the same turn. The orchestrator already decides NPC
   movements; with the boost, it weighs "NPC walks over and starts a chat with
   the player" higher. Selection of *which* NPC favors:
   - High chemistry/affection with player
   - Extraverted personality
   - Not currently in another conversation
   - Activity affinity (gym-lover at the gym, foodie in the kitchen)

4. **NPC approach response — player can decline.** When the orchestrator
   triggers an approach, the next player turn surfaces:
   - **Engage** — turn flips to a normal `start_conversation` (NPC-initiated)
   - **Wave them off politely** — small affection hit on the NPC's side,
     tiny audience penalty (mild snub)
   - **Wave them off firmly** — bigger affection hit, gossip seed ("X
     blanked me"), bigger audience penalty
   - **Pretend not to notice** (player keeps swimming) — neutral; NPC drifts
     away on their own; small affection hit if they really tried
   The decline options are similar in flavor to the existing pull-away
   mechanic.

5. **Audience appeal penalty** — consecutive ambient actions without a chat
   drop public perception slightly ("not sparking"). Soft signal — three in a
   row before a real interaction is fine, six in a row drops appeal by ~5.

6. **Autopilot policy** — personas pick ambient when:
   - Phase clock has >30m remaining
   - No high-priority chat target available (already chatted with everyone
     today, or no compatible target nearby)
   - Mood-aligned: anxious autopilot picks "sit and think", confident picks
     "swim", etc.

### Implementation plan

1. **Content** (`src/game/content/ambient.py`, new): define `AmbientOption`
   model and the default per-location set above.
2. **Action kind**: add `ActionKind.AMBIENT` in `engine/actions.py`. Add
   `available_ambient_options(state)` returning options for the player's
   current location.
3. **Rules** (`engine/rules.py` / `apply_action`): handle `AMBIENT` —
   deduct `time_cost`, apply mood/stat, log boost for the orchestrator.
4. **Orchestrator hint**: pass `npc_encounter_boost` into Sunset Bay
   orchestrator's NPC-initiation rolls for the current turn. Track which NPC
   approaches (if any) and produce a `npc_initiated_conversation` event.
5. **Engine reaction to NPC initiation**: if orchestrator says "Liam walks
   over to you at the pool", next player turn flips to `start_conversation`
   from Liam's side. Player's `available_actions` shows the new
   conversation context (response options).
6. **Remove** `ADVANCE_PHASE`: drop from `ActionKind`, `available_actions`,
   `ACTION_TIME_COST`, CLI play loop, autopilot prompts, all fixtures.
7. **Auto-advance safety**: in `engine/turn.py`, if `available_actions(state)`
   returns only ambient options for ≥4 consecutive turns AND `auto_advance`
   keeps firing on next budget tick, that's fine — phases just end. But if
   the budget is 0 and no event fires, force-advance (already handled).
8. **Autopilot** (`agents/player_autopilot.py`): update prompt to weigh
   ambient options vs chats. Each persona has a "sparking threshold" — when
   below it, ambient is acceptable; when above, must initiate a chat.
9. **Tests/fixtures**: every fixture that contains `advance_phase` must be
   regenerated with ambient choices or natural auto-advance. Schema-version
   bump. Determinism hashes change.
10. **Trace renderer**: ambient turns appear as a new scene kind (`ambient`
    or fold into `turn` / `movement`). Each ambient turn shows the action +
    any mood/stat trickle + whether an NPC was triggered.

### Open questions

- Should ambient options unlock as you "rank up" the location (e.g. nap
  unlocks after 1 hr in bedroom)? Probably no — flat list is simpler.
- Should the player see encounter probability before picking? Probably no —
  reveals too much; ambient should feel like flavor, not strategy.
- Do we model "the orchestrator decided to send Liam over while you're
  swimming" as a forced or accepted event? **Accepted** — player can still
  ignore the approach (the new player action sees Liam waiting; their first
  option could be "Wave him off"). This preserves agency.

**Renderer note.** The honest clock display surfaces the gaps this fix
removes. Once ambient is in, gaps disappear — every turn consumes time and
phase transitions are organic.

---

## 10. Producer texts fire on time but don't feel like events

**Observation.** Producer texts ("group_date_invite", "coupling_warning",
"flush_of_hearts_announce", "final_vote_announce") fire as expected via
`ceremony_events`. But each is a one-line message with no narrative wrapping.
The renderer surfaces them as small cards, but they read like system messages,
not show beats.

**Root cause.** Producer text content lives in `src/game/content/producer.py`
or similar — short string templates. No narrator wrap.

**Proposed fix.** Route producer texts through the narrator for a 2-3 sentence
wrap that names the day/phase and any specifics ("Tomorrow's group date will
take you, Maya, and Blake to a secluded cabana — bring sunscreen and your best
banter").

---

## 11. Final vote should feel like a finale, not a turn

**Observation.** Turn 75: `final_vote: the player and chloe win as the top
couple` — one ceremony event, one narrator prose paragraph. Renderer now
applies finale styling, but the engine treats it as another ceremony.

**Root cause.** `engine/ceremonies/` doesn't distinguish finale from in-show
ceremonies.

**Proposed fix.** Finale should produce a structured `FinaleResult` with:
- winning couple
- runner-up couples
- per-couple final audience score
- per-heartbreaker journey summary (e.g. "stayed loyal through Flush of Hearts", "biggest
  arc: ...")
- AP awarded (for the meta-progression layer)

Renderer can then lay out a proper outro screen.

---

## 13. Audience signaling on options + post-action feedback

**Decision.** Two-layer audience visibility, with the engine carrying the
weights and the renderer surfacing them.

### Layer 1: predicted hint on each option

Every `ContextualOption` gets an `audience_hint` field with one of three
values:

```python
class AudienceHint(str, Enum):
    POSITIVE = "+"   # audience would approve
    NEGATIVE = "-"   # audience would side-eye
    NEUTRAL  = ""    # no strong signal
```

Computed at option-generation time from the option's tags:

```python
AUDIENCE_WEIGHTS = {
    # positives
    "loyal": +3, "supportive": +2, "genuine": +3, "vulnerable": +2,
    "comforting": +2, "playful": +1, "honest": +2,
    # negatives
    "snakey": -3, "gossip": -2, "disloyal": -3, "harsh": -2,
    "boasting": -2, "petty": -2, "cold": -1,
    # neutrals (most tags)
    ...
}

def hint_for(option: ContextualOption) -> AudienceHint:
    score = sum(AUDIENCE_WEIGHTS.get(tag, 0) for tag in option.tags)
    if score >= 2: return POSITIVE
    if score <= -2: return NEGATIVE
    return NEUTRAL
```

3-way only — keeps the player from min-maxing fine-grained scores.

Renderer shows a small `+` / `−` chip on each wheel option. The chip is
*informational, not predictive of magnitude* — it tells you direction.

### Layer 2: observed delta after the turn

When `player.public_perception` changes by ≥ ±2 in a turn, the renderer
surfaces an "audience" chip in the exchange outcome row:

```
Audience −3 · "they didn't love the gossip"
```

The reason text is template-driven from the dominant contributing tag. Lives
in content (`content/audience_reactions.py`).

### Implementation

1. Define `AUDIENCE_WEIGHTS` table in `engine/audience.py` (or extend existing
   audience module).
2. Add `audience_hint` field to `ContextualOption` schema. Compute at
   option-generation time in `agents/contextual_options.py`.
3. Update `apply_action` to record `audience_delta` on the `MechanicalResult`
   when public_perception changes.
4. Renderer:
   - Wheel option chip — small `+`/`−` next to the option label
   - Exchange outcome — `audience-pill` next to other deltas when |delta| ≥ 2
   - Reason text from the dominant tag

### Open

- Should the audience hint be visible *before* the player picks (today's
  proposal), or only after? Today: visible before. Could become a difficulty
  setting later.
- Does the audience weighing differ per persona (loyal player gets bigger
  audience penalty for snakey moves than chaotic player)? Probably no for
  v0 — flat weights, same for everyone.

---

## 12. Audience snapshots are sparse

**Observation.** `audience_snapshot` only appears on certain turns (final vote +
some day boundaries). Couple strength rankings over time aren't traceable.

**Root cause.** Snapshot is only captured at specific ceremony events.

**Proposed fix.** Capture audience snapshot at every phase transition or every
day boundary. Required for a "trajectory" chart in the review packet (couple
strength over time, with annotations for events).

---

## 14. Pairing Ceremony proposal (Phase 2 — player and NPC initiated)

The show's "steal/spark" mechanic. Not just Pairing Ceremonies — any
contestant can propose to break a couple at any time once chemistry/affection
is high enough. Depends on §4 (NPC couples must exist as state) and §3
(curator at conversation end so the proposal moment generates a memory).

### Trigger thresholds

Player-initiated:
- Player ↔ non-partner NPC chemistry ≥ 60 AND affection ≥ 50
- Unlocks `ActionKind.PROPOSE_PAIR` action in the menu when chatting with
  that NPC, OR as a special option in the contextual wheel during a chat

NPC-initiated:
- NPC ↔ player chemistry ≥ 60 AND affection ≥ 50 AND NPC's current couple
  strength ≤ some threshold (~50 — they're drifting from their partner)
- Resort orchestrator decides to trigger: NPC walks up at a moment (during
  ambient or at the start of an action turn) — "Look, I need to tell you
  something serious…"
- Symmetric: NPC can also propose to other NPCs (background drama — surfaces
  via gossip + Pairing Ceremony state changes, no player-visible UI for now)

### Acceptance roll

When proposed, the receiving side rolls:

```
accept_chance = (
    chemistry_with_proposer * 0.4
  + affection_with_proposer * 0.3
  - current_couple_strength * 0.3
  + persona_bias              # loyal persona: -20; flirty: +20; chaotic: +10
)
```

Player's "accept_chance" is shown as a 3-way audience hint (positive = your
audience score will say "bold!", negative = "snakey", neutral = mixed).
Player can still pick either way; the hint is just signal.

NPC's response runs the same math. The result is deterministic from seed +
state — recordable in trace.

### Cascade on acceptance

```
Before: player↔Chloe, Maya↔Liam
Player proposes to Maya, Maya accepts.

After:
- player↔Chloe couple dissolves (formed_via -> "broken_by_steal_outgoing")
- Maya↔Liam couple dissolves (formed_via -> "broken_by_steal_incoming")
- new couple: player↔Maya, rebound=False (chosen via real attraction)
- Chloe and Liam are now SINGLE (not auto-paired — show-accurate)
```

### Cascade on rejection

- Proposer takes a small audience hit (looked desperate / disloyal)
- Proposer's relationship with target NPC takes a chemistry/affection hit
- Gossip seed propagates ("X tried to spark Y; Y said no")
- Proposer's current partner finds out (through gossip; takes a trust hit
  toward proposer)

### Singles handling (no auto-pair)

After a successful steal, the two left-behind NPCs are **single**:
- `Heartbreaker.coupled = False` (or removed from any active Couple)
- Mood crashes to "heartbroken" / "scrambling"
- Audience perception drops slightly for being Heart Out — but recovers quickly
  if they handle it well
- They can:
  - Pursue any other heartbreaker via their own chemistry/affection growth
  - End up "rebounding" with each other if they organically pair (their
    background interactions can build chemistry; once thresholds met, they
    couple up via the same proposal mechanic)
  - Get paired forcibly at the next forced Pairing Ceremony — and if they
    fail to attract anyone by then, one is at risk of dumping

The engine doesn't force any of this. Singles drift in background chats and
either pair up organically, get paired at ceremony, or risk elimination.

### Audience impact of steals

- Successful steal: bold (+2 if highly attractive proposer, -2 if disloyal
  reputation, net ~0 unless one side is extreme)
- Failed proposal: petty/desperate (-3 to -5)
- Being the *target* of a successful steal: sympathetic +2 to the Heart Out
  party; mild boost to the bold proposer; the cheating partner takes the
  biggest hit (-3 to -5 if they accepted)

### Implementation

1. Add `ActionKind.PROPOSE_PAIR` with target_id = receiver NPC.
2. Eligibility check in `available_actions(state)`: only surface when
   thresholds met with a non-partner.
3. `apply_action` handles the proposal:
   - Roll acceptance
   - Mutate couples on accept
   - Generate ceremony_event of kind `pair_proposal` with sub-kind
     `accepted` / `rejected`
   - Generate gossip seeds either way
   - Fire curator on the active conversation (it's now ending dramatically)
4. Resort orchestrator gets a new path: NPC-initiated proposal. New event
   kind `npc_proposal_incoming` surfaces to the player as a forced
   conversation start.
5. Singles state — extend `Heartbreaker` schema or derive from `state.couples`.
6. Audience module updated with proposal-specific reactions.

### Open questions for Phase 2 kickoff

- How does the Paradise Suite interact with this? Currently the player can use the
  Paradise Suite with their partner. Should a stolen couple immediately unlock
  Paradise Suite? Probably no — needs a cool-down to feel earned.
- Flush of Hearts + steal interactions: Flush of Hearts already does its own Pairing Ceremony. Does a
  steal during Flush of Hearts propagate to the post-Flush of Hearts reveal? Probably yes — but the
  reveal scene needs to handle it.
- How visible are NPC↔NPC proposals to the player? Just gossip seeds, or a
  visible "NPC X proposed to NPC Y" event chip in the day boundary recap?
  Lean: gossip only, surface in recap audience standings as couple changes.

---

## Severity / order

Roughly:

| # | Issue | Severity | Effort |
|---|---|---|---|
| 4 | NPC couples not in state | **High** — blocks audience system | M |
| 3 | Curator per-turn instead of per-conversation | **High** — token cost + confusion | M |
| 5 | Autopilot coasts on one NPC | **High** — visible game-feel bug | S |
| 9b | `advance_phase` free for player | **High** — root cause of #5 + skipped content | S |
| 6 | No Day-1 onboarding | **High** — first-run experience | M |
| 1 | Day-1 Pairing Ceremony label | **Med** — narrative correctness | S |
| 7 | Narrator prose is thin | **Med** — feel | S (prompt) |
| 2 | Phase anchors not in engine | **Med** — clean abstraction | S |
| 9 | Auto-advance never trips | **Med** — broken mechanic | S |
| 11 | Finale should be structured | **Low** — polish | M |
| 10 | Producer texts feel system-y | **Low** — polish | S |
| 12 | Audience snapshots sparse | **Low** — analytics | S |
| 8 | Challenges are single rolls | **Low** — out of scope v0 | L |

S ≈ <1 day · M ≈ 1–3 days · L ≈ week+

---

## Notes from the renderer side

These workarounds in the review-packet renderer compensate for engine gaps and
should ideally be removed once the engine is fixed:

- **Day-1 "Opening Coupling" rename** — renderer-side string substitution; should
  be a distinct engine event kind (issue #1).
- **Phase anchor times (09:00 / 14:00 / etc.)** — documented display convention;
  should be engine config (issue #2).
- **Player vs background curator batch split** — renderer filters by
  `source == "direct"` and `holder/subject == "player"`; should be structurally
  separated in engine commits (issue #3).
- **Couples panel shows only player couple** — faithful to data, looks wrong;
  resolves itself once NPC couples are stored (issue #4).
