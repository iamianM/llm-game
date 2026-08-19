# Kiss Wed Pass

**Engine kind:** `kiss_wed_pass`
**Player-facing name:** Kiss Wed Pass
**Scheduled day:** 5
**Rollout step:** 5
**Status:** Shipped through the shared round-based challenge harness, with
deterministic engine coverage and a golden narration scenario.

Validates the constrained-allocation choice pattern: pick exactly one
heartbreaker for each of three labels. Reuses the shared round shape, but the
choice space is a permutation, not a multiple choice.

## 1. Player experience

Day 5. The producer hands the player three labels — Kiss, Wed, Pass — and
three available targets. The player allocates them. Every other heartbreaker
does the same off-camera (deterministically), then the producer reads
everyone's allocations aloud. Reactions follow.

The minigame's drama is choosing whom to *pass*. Passing a strong heartbreaker
makes a public statement; passing the wrong person dents friendships and
risks audience favor.

## 2. Round shape

Three sequential rounds, one per label:

- Round 0 — Kiss. `target_id = null` (no fixed subject). `choices` =
  three available heartbreakers. The pick removes that heartbreaker from the
  remaining pool.
- Round 1 — Wed. Same shape; remaining two heartbreakers.
- Round 2 — Pass. Same shape; one heartbreaker remains. The "choice" is
  rendered with a one-option `MinigameChoice` so the trace still records
  it as an explicit pick.

Available heartbreakers for the player are: the player's current partner, the
top-affection non-partner, and the top-chemistry non-partner. If those
collapse (e.g., partner is also top-chemistry), the engine fills with
deterministic next-best picks.

## 3. Scoring

```yaml
kiss_wed_pass:
  rounds: 3
  per_round_points:
    kiss_partner: 2
    kiss_chemistry: 3
    kiss_friend: 1
    wed_partner: 3
    wed_chemistry: 2
    wed_friend: 1
    pass_rival: 3
    pass_friend: -3
    pass_partner: -5
  thresholds:
    success: 6
    partial: 2
  audience:
    success: 3
    partial: 1
    failure: -2
```

Per-round point lookup keys off `(label, relationship_kind_of_target)` where
`relationship_kind_of_target` is computed at score time from current state:
`partner`, `chemistry` (top non-partner chemistry), `friend` (top
non-partner friendship), or `rival` (lowest non-partner affection).

Classification → effects:

- `success`: drama earned, audience `+3`. Per-target deltas applied:
  the kissed target gets `RelationshipDelta(chemistry=+3)`, the
  wed target gets `RelationshipDelta(affection=+2, trust=+2)`,
  the passed target gets `RelationshipDelta(friendship=-2)`.
- `partial`: audience `+1`. Lighter deltas across the board.
- `failure` (passed partner or passed friend): audience `-2`. Passed partner
  triggers `RelationshipDelta(affection=-5, trust=-5)` and records a
  `humiliated_publicly` memory.

Passing the partner is an extreme play. It is legal — the engine offers it
— but the failure threshold is calibrated so the player feels the cost.

## 4. Knowledge bridge

No direct Trait Card / Known Fact dependency. Pulls from current
relationship state and audience knowledge.

A pass of a target with a strong friendship score creates a public-knowledge
entry the audience layer will reference for several days, similar to a
caught lie.

## 5. Reveals and wrap

Per round:

- `MinigameReveal(kind="reaction", subject_id=target_id, payload =
  {"label": "kiss" | "wed" | "pass", "tone": "..."})`.
- For the passed target, a curator rail entry.

Wrap:

- The other heartbreakers' allocations are revealed as `MinigameReveal(kind=
  "fact", payload={"performer": npc_id, "kiss": id, "wed": id,
  "pass": id})`. Each is computed deterministically from the heartbreaker's
  current relationship matrix.
- Any "you were everyone's pass" or "your partner passed you" beats trigger
  a wrap memory.

The narrator must name the player's three picks by label and target. The
judge's `narration_mentions_choice_label` check enforces this.

## 6. Surfaces

- `src/game/engine/challenges.py` — `score_kiss_wed_pass`,
  `apply_kiss_wed_pass_result`, `available_targets_for_kiss_wed_pass`.
- `src/game/engine/actions.py` — sequential label rounds.
- `web/components/stage/ChoiceMenu.tsx` — allocation UI (target removed
  from pool after each pick).
- `tests/engine/test_kiss_wed_pass.py` — pool-shrinking choices, pass-
  partner failure path, deterministic NPC allocations.

## 7. Acceptance

A reviewer can:

- See three rounds in the trace with the player's allocation.
- See the other-heartbreaker allocation matrix in the wrap reveal payload and
  verify it's stable on a fixed seed.
- Confirm the pass-partner path drives the calibrated `failure` audience and
  relationship deltas.

## 8. Fun notes

- The pass is the spice. Every other minigame is about getting things right;
  this one rewards an interesting wrong-on-paper move.
- A pass of a rival should feel like a power move that the audience loves.
  Calibrate the success threshold so a rival-pass hits `success`.
- Passed partner is a self-detonation. The wrap should not soften it —
  Conversation Curator should run a rail line that follows the player for
  the rest of the day.
- The other heartbreakers' allocations are the most fun reveal because they
  expose what the cast actually thinks. The narrator should name at least
  one surprising NPC allocation.

## 9. Open questions

To resolve in the Kiss Wed Pass PR, before merging:

- **Mock-mode stem phrasing.** Kiss Wed Pass has only three labels and no
  trait stems, so mock-mode and real-mode produce nearly identical scenes.
  Confirm the golden eval doesn't accidentally depend on a real-mode label
  variant. Lock label strings in `data/balance/minigames.yaml` rather than
  the prompt.
- **Available-target tie-breaking.** When picking the three available
  targets (top-affection, top-chemistry, lowest-affection non-partners),
  ties are possible. Proposed rule: same NPC id sort order convention as
  the rest of the harness. Document and test.
- **Pass-partner audience reaction shape.** A passed partner triggers
  `RelationshipDelta(affection=-5, trust=-5)` and a `humiliated_publicly`
  memory. The audience delta is the standard `failure` value (`-2`,
  recovery-floor-dampened). Should the audience react more strongly to a
  pass-partner move specifically, given how unusually theatrical it is?
  Proposed rule: extra `-3` audience for pass-partner, capped together with
  the standard `failure` delta at `-5` total. Reality TV audiences love
  drama but don't reward cruelty; the cap keeps the floor reasonable.
