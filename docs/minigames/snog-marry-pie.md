# Kiss Wed Pass (Snog / Marry / Pie)

**Engine kind:** `snog_marry_pie`
**Player-facing name:** Kiss Wed Pass
**Scheduled day:** 5
**Rollout step:** 5
**Status:** Spec authored; implementation pending shared harness.

Validates the constrained-allocation choice pattern: pick exactly one
islander for each of three labels. Reuses the shared round shape, but the
choice space is a permutation, not a multiple choice.

## 1. Player experience

Day 5. The producer hands the player three labels — Snog (Kiss), Marry
(Wed), Pie (Pass) — and three available targets. The player allocates them.
Every other islander does the same off-camera (deterministically), then
the producer reads everyone's allocations aloud. Reactions follow.

The minigame's drama is choosing whom to *pie*. Pie-ing a strong islander
makes a public statement; pie-ing the wrong person dents friendships and
risks audience favor.

## 2. Round shape

Three sequential rounds, one per label:

- Round 0 — Snog. `target_id = null` (no fixed subject). `choices` =
  three available islanders. The pick removes that islander from the
  remaining pool.
- Round 1 — Marry. Same shape; remaining two islanders.
- Round 2 — Pie. Same shape; one islander remains. The "choice" is
  rendered with a one-option `MinigameChoice` so the trace still records
  it as an explicit pick.

Available islanders for the player are: the player's current partner, the
top-affection non-partner, and the top-chemistry non-partner. If those
collapse (e.g., partner is also top-chemistry), the engine fills with
deterministic next-best picks.

## 3. Scoring

```yaml
snog_marry_pie:
  rounds: 3
  per_round_points:
    snog_partner: 2
    snog_chemistry: 3
    snog_friend: 1
    marry_partner: 3
    marry_chemistry: 2
    marry_friend: 1
    pie_rival: 3
    pie_friend: -3
    pie_partner: -5
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
  the snogged target gets `RelationshipDelta(chemistry=+3)`, the
  married target gets `RelationshipDelta(affection=+2, trust=+2)`,
  the pied target gets `RelationshipDelta(friendship=-2)`.
- `partial`: audience `+1`. Lighter deltas across the board.
- `failure` (pied partner or pied friend): audience `-2`. Pied partner
  triggers `RelationshipDelta(affection=-5, trust=-5)` and records a
  `humiliated_publicly` memory.

Pie-ing the partner is an extreme play. It is legal — the engine offers it
— but the failure threshold is calibrated so the player feels the cost.

## 4. Knowledge bridge

No direct Trait Card / Known Fact dependency. Pulls from current
relationship state and audience knowledge.

A pie of a target with a strong friendship score creates a public-knowledge
entry the audience layer will reference for several days, similar to a
caught lie.

## 5. Reveals and wrap

Per round:

- `MinigameReveal(kind="reaction", subject_id=target_id, payload =
  {"label": "snog" | "marry" | "pie", "tone": "..."})`.
- For the pied target, a curator rail entry.

Wrap:

- The other islanders' allocations are revealed as `MinigameReveal(kind=
  "fact", payload={"performer": npc_id, "snog": id, "marry": id,
  "pie": id})`. Each is computed deterministically from the islander's
  current relationship matrix.
- Any "you were everyone's pie" or "your partner pied you" beats trigger
  a wrap memory.

The narrator must name the player's three picks by label and target. The
judge's `narration_mentions_choice_label` check enforces this.

## 6. Surfaces

- `src/game/engine/challenges.py` — `score_snog_marry_pie`,
  `apply_snog_marry_pie_result`, `available_targets_for_snog_marry_pie`.
- `src/game/engine/actions.py` — sequential label rounds.
- `web/components/stage/ChoiceMenu.tsx` — allocation UI (target removed
  from pool after each pick).
- `tests/engine/test_snog_marry_pie.py` — pool-shrinking choices, pie-
  partner failure path, deterministic NPC allocations.

## 7. Acceptance

A reviewer can:

- See three rounds in the trace with the player's allocation.
- See the other-islander allocation matrix in the wrap reveal payload and
  verify it's stable on a fixed seed.
- Confirm the pie-partner path drives the calibrated `failure` audience and
  relationship deltas.

## 8. Fun notes

- The pie is the spice. Every other minigame is about getting things right;
  this one rewards an interesting wrong-on-paper move.
- A pie of a rival should feel like a power move that the audience loves.
  Calibrate the success threshold so a rival-pie hits `success`.
- Pied partner is a self-detonation. The wrap should not soften it —
  Conversation Curator should run a rail line that follows the player for
  the rest of the day.
- The other islanders' allocations are the most fun reveal because they
  expose what the cast actually thinks. The narrator should name at least
  one surprising NPC allocation.

## 9. Open questions

To resolve in the Kiss Wed Pass PR, before merging:

- **Mock-mode stem phrasing.** Snog/Marry/Pie has only three labels and no
  trait stems, so mock-mode and real-mode produce nearly identical scenes.
  Confirm the golden eval doesn't accidentally depend on a real-mode label
  variant. Lock label strings in `data/balance/minigames.yaml` rather than
  the prompt.
- **Available-target tie-breaking.** When picking the three available
  targets (top-affection, top-chemistry, lowest-affection non-partners),
  ties are possible. Proposed rule: same NPC id sort order convention as
  the rest of the harness. Document and test.
- **Pie-partner audience reaction shape.** A pied partner triggers
  `RelationshipDelta(affection=-5, trust=-5)` and a `humiliated_publicly`
  memory. The audience delta is the standard `failure` value (`-2`,
  recovery-floor-dampened). Should the audience react more strongly to a
  pie-partner move specifically, given how unusually theatrical it is?
  Proposed rule: extra `-3` audience for pie-partner, capped together with
  the standard `failure` delta at `-5` total. Reality TV audiences love
  drama but don't reward cruelty; the cap keeps the floor reasonable.
