# The Couples Quiz (Mr & Mrs)

**Engine kind:** `couples_quiz`
**Player-facing name:** The Couples Quiz
**Scheduled day:** 3
**Rollout step:** 2
**Status:** Shipped through the shared round-based challenge harness, with
deterministic engine coverage and a golden narration scenario.

Reuses the round shape and harness proven by Compatibility Quiz. Adds a
two-sided round: the player guesses the partner, *and* the partner guesses
the player. Validates that the shared system handles minigames where both
sides of a couple produce answers.

## 1. Player experience

By Day 3 the player has had two days of conversation. The Couples Quiz tests
both directions of knowledge across the couple. Each round, both partners
answer the same question privately, then the answers are compared. Matches
score. Mismatches expose how well — or how little — the couple knows each
other on TV.

The Day-3 timing is intentional: it lands the night before the first
Pairing Ceremony, so a strong Couples Quiz buys the player relationship momentum
heading into the Heart Swap, and a weak one creates a "should we even be a couple"
beat the producer will exploit.

## 2. Round shape

Six rounds, structured as alternating directions:

- Rounds 0, 2, 4: question about the partner; player picks an answer about
  *them*. (Same as Compatibility Quiz.)
- Rounds 1, 3, 5: question about the player; partner picks an answer about
  *them*. The partner's answer is computed deterministically from their
  Trait Card's perception of the player (see §4); the player only sees the
  partner's answer revealed after the fact.

Each round:

- `target_id` is whichever heartbreaker the question is about.
- `prompt_id` from the `couples_quiz` Question Bank pool.
- `choices` for player-controlled rounds; partner-controlled rounds carry a
  single `chosen_id` filled in by the engine.
- `points = 3` per match (both partners give the same answer or both
  partners answer correctly about the third party). `0` otherwise.

## 3. Scoring

```yaml
couples_quiz:
  rounds: 6
  per_round_points:
    both_match: 3
    one_correct: 1
    mismatch: 0
  thresholds:
    success: 14
    partial: 8
  audience:
    success: 5
    partial: 2
    failure: -3
```

Classification → effects (audience deltas post-processed by the shared
recovery floor in system doc §5.2):

- `success`: Couple gains a `solid_couple` memory. Relationship delta
  `RelationshipDelta(friendship=+5, affection=+3, trust=+2)`. Audience `+5`.
- `partial`: `RelationshipDelta(friendship=+1)`. Audience `+2` (recovery
  floor lifts to `+4` when audience favor is below the floor threshold).
- `failure`: `RelationshipDelta(friendship=-3, affection=-2)`. Audience `-3`
  (recovery floor dampens to `-1` when audience favor is below the floor
  threshold). Triggers a `awkward_silence` memory and a Conversation
  Curator recap line.

A run of three consecutive mismatches at any point unlocks a `lost_in_the_loop`
moment — the wrap calls out the streak by name.

## 4. Partner-side answer derivation

The partner's "guess about the player" is deterministic:

- The partner consults their `known_facts` about the player. For Tier 1/2
  facts, they answer correctly. For Tier 3/4 facts that they haven't been
  told, they pick a distractor weighted by their `secret_engine` and
  personality traits.
- Engine helper: `engine/knowledge.py:partner_guess_about_player(state,
  partner_id, trait_key, rng)`. Pure function. Tested.
- Reveals from partner-controlled rounds include the partner's pick *and*
  the truth, both attached to the round.

This is the addition that justifies a separate minigame instead of a
"Compatibility Quiz Vol 2". The two-direction symmetry is the gameplay.

## 5. Knowledge bridge

- Same eligibility gates as Compatibility Quiz on player-controlled rounds.
  The round selector consults `state.quizzed_traits_this_run` (system doc
  §6.5) so a trait the Day-1 quiz already used does not reappear unless the
  exhaustion fallback fires.
- The Day-3 pool is much wider than Day 1: familiarity has had time to push
  Tier 2/3 facts into eligibility. Mechanical prompts are preferred; flavor
  prompts are still in the pool as exhaustion padding.
- Partner-controlled rounds are gated by what the *partner* knows about the
  player. The player's `revealed_to(partner_id)` ledger drives partner
  eligibility (already part of the knowledge layer).
- Correct player picks write `KnownFact(..., source="couples_quiz",
  confidence=1.0)`; incorrect picks write `KnownFact(...,
  source="quiz_misread", confidence=0.5)` plus a `caught_unprepared` memory
  per the shared rule in system doc §6.3 / compatibility-quiz §4.
- Partner-controlled rounds write a *symmetric* `KnownFact` onto the
  partner side of the ledger: when the partner guesses correctly about the
  player, the partner has confirmed a fact about the player; when they
  guess wrong, the partner has formed a misconception. Both feed downstream
  Conversation Curator and gossip propagation.
- All matches and mismatches write `KnownFact`s into both directions
  (player learns what the partner thinks; partner has already been computed
  to know or not know).

## 6. Reveals and wrap

- Per round: one fact reveal in each direction (correct and partner's
  guess).
- Wrap: a couple-level reveal carrying the match count, the audience delta,
  and a per-round `("aligned" | "missed")` label.
- Streak reveal if three consecutive mismatches occurred.

The wrap narration must name at least two specific mismatches by question
text and answer. Vague summaries ("you got some right, some wrong") fail the
judge's faithfulness check.

## 7. Surfaces

Same shape as Compatibility Quiz (system doc §8). Only the changes:

- `src/game/engine/knowledge.py` — `partner_guess_about_player` helper.
- `src/game/engine/challenges.py` — `score_couples_quiz`,
  `apply_couples_quiz_result`. The scoring function handles alternating
  directions.
- `web/components/stage/GameStage.tsx` — visual distinction between
  player-controlled and partner-controlled rounds (a small "Chloe answers"
  header on partner rounds).
- `tests/engine/test_couples_quiz.py` — partner derivation, alternating
  rounds, streak detection.

## 8. Acceptance

A reviewer can:

- See six rounds in the trace, three from each direction.
- See the partner's recorded picks in the trace, derived from
  `partner_guess_about_player`.
- Confirm the streak detection by reading a fixture where three consecutive
  mismatches trigger the `lost_in_the_loop` reveal.
- Open the `couples-quiz-narration.yaml` golden eval and confirm the narrator
  named at least two specific mismatches.

## 9. Fun notes

- The two-sided structure is what makes this funny. The narration should
  lean on contrast: "She thinks your love language is words. You think hers
  is touch. Neither of you is right."
- Day 3 is right before the first Pairing Ceremony. A failure here should plant
  a real seed of doubt — the player should leave wondering if the couple is
  actually compatible heading into the Heart Swap.
- A `success` should feel like a public proof of compatibility that the
  producer will reference in next-day texts.
