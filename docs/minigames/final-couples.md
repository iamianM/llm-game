# Final Couples Challenge

**Engine kind:** `final_couples`
**Player-facing name:** Final Couples Challenge
**Scheduled day:** 6
**Rollout step:** 6
**Status:** Spec authored; implementation pending shared harness.

The closing minigame of the season. Validates that the shared harness can
host a minigame whose scoring **aggregates the season's prior minigame
results**, plus relationship and audience state, into a final couple-level
performance.

## 1. Player experience

Day 6. The remaining couples compete in a five-round mixed challenge. Each
round tests a different facet of the couple — knowledge (one Compatibility
Quiz question), chemistry (a Heart Rate echo), honesty (one Lie Detector
question), banter (one Couples Quiz question), and audacity (a Snog/Marry/
Pie pick on the rest of the cast). The player makes one choice per round.
The other couples are scored deterministically.

The winner takes the season — or, in extended seasons, secures a Final-
Three slot. The minigame's emotional load is high; this is the player's
last chance to recover lost audience favor before the final vote.

## 2. Round shape

Five rounds, one per facet:

- Round 0 — Knowledge: pull one Compatibility Quiz prompt about the
  partner that the player has not yet seen this run.
- Round 1 — Chemistry: a forced binary — "perform" or "match the moment".
  Score reads from the couple's chemistry value.
- Round 2 — Honesty: one Lie Detector prompt about a past event involving
  the partner. Standard truth/lie choice set.
- Round 3 — Banter: a one-question Couples Quiz round, alternating
  direction from a fixed coin (deterministic from seed).
- Round 4 — Audacity: a single Snog/Marry/Pie allocation against three
  other islanders.

Each round reuses the *scoring* helper of its source minigame, but
contributes a fixed weight to the final tally — the Final Couples scoring
function is **a weighted sum of round outputs**, not a redo of each
minigame's full classification logic.

## 3. Scoring

```yaml
final_couples:
  rounds: 5
  per_round_weights:
    knowledge: 4
    chemistry: 3
    honesty: 5
    banter: 3
    audacity: 3
  per_round_points:
    knowledge_correct: 1
    knowledge_incorrect: 0
    chemistry_high: 1
    chemistry_low: 0
    honesty_truth: 1
    honesty_lie_undetected: 1
    honesty_lie_caught: -2
    banter_match: 1
    banter_miss: 0
    audacity_rival_pie: 1
    audacity_friend_pie: -1
    audacity_partner_pie: -3
  thresholds:
    success: 12
    partial: 6
  audience:
    success: 8
    partial: 3
    failure: -4
```

`total_points = sum(weight[facet] * facet_score for facet in rounds)`.

Classification → effects:

- `success`: couple wins the season. Audience `+8`. Player and partner
  share a `season_winner` memory. Final-vote weighting incorporates this
  outcome (see `engine/final_vote.py`).
- `partial`: respectable showing. Audience `+3`. Carries into final vote
  as a neutral nudge.
- `failure`: collapse on the last day. Audience `-4`. Final-vote weighting
  treats the couple as vulnerable.

Other couples' scores are computed deterministically using the same
formula and their state. The full ranking is captured in the result.

## 4. Knowledge bridge

- Reuses Compatibility Quiz / Couples Quiz / Lie Detector eligibility and
  bank pools. No new Trait Card or KnownFact additions.
- The Audacity round's allocation against the rest of the cast updates the
  same memories as a Day-5 Snog/Marry/Pie.

## 5. Reveals and wrap

Per round: the per-facet reveal from the source minigame, marked with
`payload.final_round_index` so the wrap can group them.

Wrap:

- The final ranking of all couples by `total_points`.
- The audience delta and the final-vote weighting applied.
- A narrator wrap with one focal moment per couple — the highest-impact
  round per couple — named explicitly.

The wrap is one of the longest narration scenes in the game and gets its
own slide template in report packets.

## 6. Surfaces

- `src/game/engine/challenges.py` — `score_final_couples`,
  `apply_final_couples_result`, per-facet round adapters that call into
  the source-minigame scoring helpers without re-applying their full
  classifications.
- `src/game/engine/final_vote.py` — consume Final Couples classification
  as one input to the final-vote weighting. New explicit hook.
- `src/game/reporting/slides/scene_renderers.py` — Final Couples wrap
  template.
- `tests/engine/test_final_couples.py` — facet weight math, weighted-sum
  thresholds, final-vote integration.

## 7. Acceptance

A reviewer can:

- Read the trace and see five round payloads, each tagged with its facet.
- Reproduce `total_points` from the per-round contributions and the
  weight table.
- See the other couples' computed scores and confirm they match
  `score_final_couples` run against their state.
- See the final-vote weighting change in
  `engine/final_vote.py` based on the classification.
- Open the narration eval and verify each couple's focal moment is named
  in the wrap.

## 8. Fun notes

- This is the closing scene. The narrator should feel like a finale, with
  longer, slower beats and named callbacks to earlier minigame moments
  ("…the lie you told on Day 4…").
- A `failure` here, on top of a strong season, should feel like a real
  setback — the audience delta and the final-vote nudge make it matter.
- A `success` here, after a bumpy week, is the comeback arc. The wrap
  should explicitly reference at least one earlier failure if there was
  one, so the recovery lands.
- The Audacity round's pie-partner option must be present even on Day 6.
  The story value of the player choosing to torch their own couple at the
  finish line is too high to remove. The calibration just makes the cost
  brutal.

## 9. Open questions

To resolve in the Final Couples PR, before merging:

- **Chemistry facet delegate.** The Chemistry round is supposed to delegate
  to a source-minigame helper, but Pulse Race doesn't really *score*
  (zero rounds in the scoring sense). Proposed rule: the Chemistry round
  reads `engine/compatibility.py:chemistry_between(player, partner)`
  directly and maps `[0, 60) -> chemistry_low`, `[60, 100] -> chemistry_high`.
  No call to `score_pulse_race`. Pulse Race remains the season's reveal
  layer; Final Couples just reads the underlying chemistry value.
- **Aggregate audience cap.** Final Couples can swing audience by `+8` or
  `-4` from this minigame alone, on top of whatever the season's other
  beats produced. Should there be a Day-6-specific cap so audience favor
  cannot end above `100` or below `0` purely from Final Couples? The
  audience state already clamps to `[0, 100]` per `state_access.py`, so
  the cap is implicit. Confirm this is true with an end-of-season fixture
  rather than re-implementing.
- **Other-couple scoring observability.** The wrap surfaces a ranking of
  all couples. The trace must record each couple's full per-facet score
  breakdown, not just the totals, so review packets can show why couple X
  beat couple Y. Proposed rule: extend `Challenge` to carry an
  `other_couple_breakdowns: dict[str, list[MinigameRound]]` mirror; the
  reviewer can read it inline.
- **Final-vote weighting magnitude.** `engine/final_vote.py` will consume
  Final Couples classification as one input. Open: how heavy is the
  weighting? Proposed rule: a `success` shifts the vote weighting by the
  same magnitude as one full day of audience favor (i.e., comparable to
  but not larger than the season's running audience score). Lock with a
  scenario fixture that runs the full Day-6 → final-vote pipeline.
