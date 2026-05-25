# Lie Detector

**Engine kind:** `lie_detector`
**Player-facing name:** Lie Detector
**Scheduled day:** 4
**Rollout step:** 3
**Status:** Spec authored; implementation pending shared harness.

The first minigame where the player chooses *whether to be honest*. Reuses
the quiz round shape, but the "correct answer" is computed from event
history (kisses, hideaway visits, gossip propagation) instead of Trait
Cards. The drama comes from the player deciding to lie about something the
machine will detect.

## 1. Player experience

Day 4 is after the first recoupling. The producer announces a Lie Detector
session. The player is wired up to a fake polygraph and the partner asks
five questions about the player's behavior in the villa so far. For each
question, the player picks between (a) the truthful answer and (b) a small
set of plausible lies. The "machine" — actually the engine, consulting state
— reveals after each round whether the partner *believes* the answer based
on what they know, what the audience knows, and what the rest of the cast
has been gossiping about.

Telling the truth is sometimes painful. Lying is sometimes safe. The
information asymmetry between the player, the partner, and the audience is
the whole minigame.

## 2. Round shape

Five rounds. Each round:

- `target_id`: the partner asking.
- `prompt_id`: drawn from `lie_detector` pool. Each prompt names a specific
  past event class (e.g., "kissed someone other than your current partner")
  or a structured belief (e.g., "do you still have feelings for your first
  pairing").
- `choices`: a small set of `MinigameChoice`s, each tagged with
  `is_correct=True` (the truthful answer) or `is_correct=False` (a lie).
  The `fact_value` field carries the actual event evidence the engine will
  check. Multiple lies are offered with different severities (a small lie of
  omission vs. an outright denial).
- `points`: positive for truth picks that the partner *can* verify, negative
  for lies the partner *does* catch.

The prompt and its evidence are pulled from event history at session
generation time, not at play time, so the bank captures a stable snapshot of
"questions worth asking on Day 4 in this season."

## 3. Scoring

```yaml
lie_detector:
  rounds: 5
  per_round_points:
    truth_verified: 3
    truth_unverified: 1
    lie_undetected: 2
    lie_caught: -4
  thresholds:
    success: 10
    partial: 4
  audience:
    success: 3
    partial: 0
    failure: -5
```

Detection rule (per round):

- The engine computes a `detection_chance` from the partner's familiarity
  with the player, the public visibility of the underlying event (the
  audience-knowledge ledger), and a small RNG draw from
  `rng.spawn(f"lie_detector::{round_index}")`.
- `chance = 30 + familiarity_factor + public_visibility_factor`, clamped
  `[10, 95]`. Exact factors live in `data/balance/minigames.yaml`.
- A lie is "caught" iff `rng.randint(1, 100) <= chance`.

Classification → effects:

- `success` (most truths verified, few lies caught): partner
  `RelationshipDelta(trust=+5, affection=+1)`. Audience `+3`.
- `partial`: small `RelationshipDelta(trust=+1)`. Audience `0`.
- `failure` (multiple lies caught): partner
  `RelationshipDelta(trust=-8, affection=-3)`. Audience `-5`. Records a
  `lie_exposed` memory the producer can reference in future texts.

A single high-stakes lie caught on a Tier-4 event (kiss with another
islander, hideaway with a third party) escalates the failure: an additional
`-3` audience and an entry on the partner's `dealbreakers` list.

## 4. Knowledge bridge

This minigame consumes the **event history** layer instead of the
Trait Card layer:

- Each round's "truth" is a function of recorded engine events: kiss
  registry, hideaway visit ledger, gossip-propagation graph, recoupling
  history. The Question Bank captures the *question*, but the *answer* is
  looked up live at score time.
- Lies are still discrete choices from the bank. The bank produces 3-4
  graded lies per question with `distractor_source = "lie"` and a tag
  describing severity (`white_lie`, `omission`, `denial`).
- Reveals: every round emits `MinigameReveal(kind="truth_told")` or
  `MinigameReveal(kind="lie_caught")` so the trace records the partner's
  belief state. These are visible to the audience layer too.

## 5. Reveals and wrap

Per round:

- The partner's belief (`believed` | `suspected` | `caught`) attached as a
  `MinigameReveal(kind="reaction", subject_id=partner)`.
- For truth picks: the underlying event class becomes a `KnownFact` on the
  partner (`partner.known_facts[player_id][event_key]`).
- For caught lies: the truth becomes a public-knowledge entry — every NPC
  learns it via gossip propagation by the next phase.

Wrap:

- Total caught lies, total truths verified.
- The partner's read of the player's honesty (`"trusted" | "suspicious" |
  "betrayed"`).
- If any lies were caught about a romantic event, an extra
  `MinigameReveal(kind="lie_caught")` carries the romantic target's id and
  triggers a Conversation Curator recap line shown in the rail.

## 6. Surfaces

Differences vs. the shared checklist:

- `src/game/engine/knowledge.py` — `lookup_event_truth(state, player_id,
  prompt_key)` helper that resolves a prompt to a truthful answer.
- `src/game/engine/gossip.py` — caught lies feed the propagation graph
  (this hook already exists; the minigame just uses it).
- `src/game/agents/event_narrator.py` — narration must respect the
  `believed`/`suspected`/`caught` triple. New required prompt section.
- `tests/engine/test_lie_detector.py` — detection clamping, severity
  escalation, gossip-propagation side effects.

## 7. Acceptance

A reviewer can:

- Open a Day-4 review packet and see, per round, which lie or truth was
  picked, what event the engine consulted, and whether the partner believed
  it.
- Confirm via `tests/engine/test_lie_detector.py` that a `failure` raises
  trust by exactly the table value, with no extra fudge.
- See gossip propagation in the trace: a caught lie at Day-4 minigame
  should appear in Day-5 conversations as a `gossip_seed`.
- Open the golden eval and verify narration named the specific events and
  the specific belief outcomes.

## 8. Fun notes

- The best moments here are the ones where the player tells a hard truth
  and the partner *appreciates* it ("I'm glad you didn't lie about that").
  Lean on this with a `truth_told` reveal that grants real trust.
- A caught lie about a hideaway visit should feel like a season-defining
  moment. The audience delta and the gossip propagation should make it
  matter for two more days.
- Avoid making the polygraph feel arbitrary. Every belief outcome should be
  derivable from prior play — never from raw chance. The detection RNG only
  exists for ties.
- The lie set per question must include at least one "barely a lie" option
  so the player can shade the truth without going nuclear. That option
  carries lower stakes both ways.

## 9. Open questions

To resolve in the Lie Detector PR, before merging:

- **Detection floor at low knowledge.** The current formula clamps to
  `[10, 95]`. The floor of 10 means a partner who knows almost nothing about
  the player and an event with low public visibility can still randomly
  catch a lie 10% of the time, which feels arbitrary. Proposed rule: drop
  the floor to `0` when both `familiarity_factor` and `visibility_factor`
  are below their respective midpoints. Keep the ceiling at 95 — a partner
  who's seen everything should not catch lies 100% of the time, but should
  be very close. Lock the clamp behavior in
  `tests/engine/test_lie_detector.py`.
- **Caught-lie gossip seed dosage.** A caught lie writes to the gossip
  propagation graph. Currently unspecified how many NPCs hear it on Day 5.
  Proposed rule: re-use the existing gossip propagation `tier=2` injection
  point (Tier 2 = "spreads to friends of the partner within one phase").
  Confirm the propagation graph already supports this; otherwise add a
  one-time `seed_gossip_from_lie(state, event_key, target_id)` helper in
  `engine/gossip.py`.
- **Truth-told reward when the partner doesn't believe you.** If the
  player tells the truth and the partner *suspects* a lie anyway (which
  happens when the partner has competing evidence from gossip), the round
  is `truth_unverified`. The current table gives 1 point. Should the
  audience see the truth and reward the player even though the partner
  didn't believe it? Proposed rule: yes — add a `+1` audience nudge for
  `truth_unverified` rounds, capped at `+3` per minigame, so the player
  who tells unpopular truths gets some credit even when the partner is
  unconvinced.
