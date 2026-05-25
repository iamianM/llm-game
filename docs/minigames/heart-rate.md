# Pulse Race (Heart Rate Challenge)

**Engine kind:** `heart_rate`
**Player-facing name:** Pulse Race
**Scheduled day:** 2
**Rollout step:** 4
**Status:** Spec authored; implementation pending shared harness.

Validates that the shared harness can host a minigame with **zero player
input rounds** — only deterministic reveals. The drama is in what the player
learns, not in what they choose.

## 1. Player experience

Day 2. The producer announces Pulse Race. The cast files into a room with
chest-strap heart-rate monitors. One by one, each islander performs a short
flirty bit for every other islander. Heart rates spike based on the actual
chemistry scores stored in the engine — scores the player has never seen
directly. The results are projected publicly. The player learns whose pulse
they raised, whose pulse raised theirs, and where the season's hidden
attractions actually sit.

There are no rounds in the choice sense. There are reveals. The player can
choose to react during the reveal sequence (a single follow-up beat at the
end), but the scoring is fixed by state.

## 2. Round shape

`rounds == []`. Instead, the minigame produces a `MinigameReveal` matrix on
the resolved `Challenge`:

- For every ordered pair `(performer, observer)` excluding self-pairs:
  - `reveal.kind = "chemistry_rank"`.
  - `reveal.subject_id = performer`.
  - `reveal.payload = {"observer_id": observer.id, "bpm": int,
    "chemistry": int}`.

`bpm = 60 + chemistry * 0.4`, deterministically. The matrix sort order is
fixed by the per-NPC turn order in the audience layer.

After the reveal matrix, a single follow-up turn surfaces three
`MinigameChoice`s as the player's *reaction* to the most surprising pair:

- "Lean into it." Boosts chemistry with the surprise target (+3).
- "Play it cool." No delta, audience-favored neutrality (+1 perception).
- "Apologize to partner." Trust+2 with partner, chemistry-1 with surprise
  target.

This single reaction round is the only place the player makes a choice in
Pulse Race. It is implemented as a normal `MINIGAME_RESPONSE` round with
`index = 0` and `target_id` pointed at the surprise target.

## 3. Scoring

```yaml
heart_rate:
  rounds: 1                      # the reaction round only
  per_round_points:
    lean_in: 0
    play_cool: 0
    apologize: 0
  thresholds:                    # classification is by reveal content, not points
    success: 0
    partial: 0
  audience:
    surprise_revealed: 2
    play_cool_chosen: 1
    lean_in_chosen: 3
    apologize_chosen: -1
```

Classification rule:

- If the chemistry matrix exposes a chemistry score ≥70 between the player
  and a non-partner: classification = `success` (drama earned).
- If the matrix exposes a chemistry score ≥70 between the *partner* and a
  non-player: classification = `partial` (drama is on the partner, not the
  player).
- Otherwise: classification = `failure` (Pulse Race is a fizzle on this
  seed — producer cuts to ad break in the wrap).

Audience deltas come from the reaction round + the classification.

## 4. Knowledge bridge

Pulse Race is the *primary* path by which a player learns hidden chemistry
scores. Every reveal that exposes a chemistry ≥50 writes a `KnownFact` of
kind `chemistry_observation`:

```python
KnownFact(
    subject_id=performer,
    key=f"chemistry_with_{observer_id}",
    value=str(chemistry),
    source="pulse_race",
    confidence=1.0,
)
```

These KnownFacts are picked up by the cast popout and become available to
the Conversation Curator for follow-up banter ("…about your reading on
Aisha…").

## 5. Reveals and wrap

The wrap narration must:

- Name the highest-BPM pair in the matrix involving the player (as either
  performer or observer).
- Name the highest-BPM pair *not* involving the player, if any score ≥80.
- Acknowledge the player's reaction choice.
- Not invent BPMs beyond the matrix entries.

Curator rail line: one summary "X had the highest read on you tonight"
sentence, added to memories.

## 6. Surfaces

- `src/game/engine/challenges.py` — `score_pulse_race`,
  `build_pulse_race_matrix`, `apply_pulse_race_result`.
- `src/game/engine/compatibility.py` — `chemistry_between(a, b)` already
  exists; Pulse Race just calls it.
- `web/components/stage/GameStage.tsx` — matrix reveal scene. CLI prints a
  formatted table.
- `src/game/reporting/slides/scene_renderers.py` — matrix table render in
  report packets.
- `tests/engine/test_pulse_race.py` — matrix determinism, classification
  rule, reaction-round application.

## 7. Acceptance

A reviewer can:

- See an N×N matrix in the review packet with BPM values that match
  `chemistry * 0.4 + 60`.
- Confirm `KnownFact`s of kind `chemistry_observation` written for every
  chemistry ≥50 entry.
- Open the narration eval and confirm the matrix's highest pairs are
  named.

## 8. Fun notes

- The point of this minigame is exposure. It should always tell the player
  something they didn't know. If a season's seed produces a matrix with
  zero scores ≥50, the wrap should *say so* and treat it as a flat week —
  not pretend drama exists.
- The reaction round is the only player input, so it has to matter. The
  three choices each shift audience favor and chemistry in clearly
  different directions.
- The "highest BPM is *your partner*" outcome should land as a wholesome
  beat with strong audience approval, not a fizzle. Make sure the wrap
  language matches.
- A `partial` classification (partner has chemistry with someone else)
  should reliably set up Casa Amor's emotional stakes. The trace's
  `gossip_seeds` table should pick this up automatically.

## 9. Open questions

To resolve in the Pulse Race PR, before merging:

- **Surprise-target tie-breaking.** The reaction round targets "the highest
  non-partner chemistry score in the matrix." If two non-partners tie, the
  selector must be deterministic. Proposed rule: tie-break by NPC id sort
  order (matching the audience-layer's existing turn-order convention).
  Lock this in `tests/engine/test_pulse_race.py`.
- **Surprise-target shape when nothing surprises.** If every non-partner
  chemistry sits below the `success` threshold (≥70) *and* the
  partner-with-non-player threshold (≥70), there is no surprise target.
  Proposed rule: skip the reaction round entirely; the wrap narrates the
  flat week and the minigame ends with zero player input. The shared
  harness already accepts zero-round minigames (Pulse Race is the
  validation case), so this is just an extension.
- **Mock-mode reveal phrasing.** The wrap narration must name specific
  BPMs and pairs. In mock mode the Event Narrator falls back to a
  template; lock the template's pair-naming convention so the golden eval
  assertions don't churn when the mock mode is exercised in CI.
