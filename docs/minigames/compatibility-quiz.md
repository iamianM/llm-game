# Compatibility Quiz

**Engine kind:** `compatibility_quiz`
**Player-facing name:** Compatibility Quiz
**Scheduled day:** 1
**Rollout step:** 1 (vertical slice — proves the shared harness)
**Status:** Spec authored; implementation pending. See [current-plan.md](../current-plan.md).

This is the first minigame and the proving ground for everything in
[../minigame-system.md](../minigame-system.md). When it works, the other five
specs reuse the same engine + agent + UI scaffolding.

## 1. Player experience

A small structured scene runs on Day 1, before the player has had time to
build deep familiarity with anyone. The producer announces it, the player is
paired with their Day-1 couple partner (post First Spark), and the quiz asks
the player five questions about that partner. Each question is a multiple
choice with one correct answer pulled from the partner's Trait Card and three
distractors. The player can only see questions whose target facts are
eligible at their current familiarity tier (so a Day-1 quiz is mostly Tier-1
and Tier-2 facts). At the end, the player learns which answers they got
right, which they got wrong, and what the truth was for the wrong ones.

A success boosts the couple's affection and trust; a partial result is neutral
with a hint of awkwardness; a failure produces a public misread moment that
costs audience favor and tightens the player's hand for the rest of the
week.

## 2. Round shape

Five rounds. Each round is:

- `target_id`: the player's current Day-1 partner (deterministic from the
  First Spark pairing).
- `prompt_id`: drawn from the Question Bank's `compatibility_quiz` pool,
  skipping prompts already recorded in
  `state.quizzed_traits_this_run[target_id]`. (Day 1 nothing is in the
  ledger yet, but the gate matters once Couples Quiz lands on Day 3.)
- `choices`: four `MinigameChoice`s — one correct (pinned to
  `TraitFact.value`), three distractors (`TraitFact.distractors` first, then
  Question Bank flavor distractors).
- `reveals`: appended after the round closes (see §5).

Eligibility per round (resolved by the round selector against the partner's
Trait Card and the player's `known_facts`):

- Tier 1 mechanical facts (`occupation`, `hometown`, `age`) always eligible.
- Tier 2 mechanical facts (`favorite_food`, `hobby`, `drink_of_choice`)
  eligible if `familiarity_with_player >= 25`.
- Tier 3 / Tier 4 mechanical facts only appear if the player has already
  revealed them via conversation (a `KnownFact` of source `direct` or
  `gossip` with `confidence >= 0.7` is on `player.known_facts`).
- Flavor facts (`mechanical=False`) are *always* eligible at the partner's
  current familiarity tier. They exist specifically so Day-1 has a viable
  pool — a fresh partner at familiarity 10 has three Tier 1 mechanical
  fields, but the flavor pool fills the remaining two rounds.

The round selector pulls in this priority order:

1. Eligible Tier 2+ mechanical facts not yet in the ledger.
2. Eligible Tier 1 mechanical facts not yet in the ledger.
3. Eligible flavor facts not yet in the ledger.
4. Shared exhaustion fallback (system doc §6.5) — only triggered if the
   first three pools cannot produce five rounds, which is rare on Day 1
   but possible mid-season.

This means a typical Day-1 quiz mixes three Tier-1 mechanical questions
with two flavor questions, and the *ceiling* is around 11 points if the
player guesses everything correctly (3 × 2 + 2 × 1) — well inside the
`partial` band and meaningfully below the `success` threshold of 14. To
hit `success` on Day 1 the player must have actively pushed familiarity
past 25 before the quiz fires, which means investing in the partner
during First Spark and the morning beats.

## 3. Scoring

Implemented in `score_compatibility_quiz(state, challenge, rng)` per the
shared scoring contract (system doc §5). Point table from
`data/balance/minigames.yaml`:

```yaml
compatibility_quiz:
  rounds: 5
  per_round_points:
    correct_tier1: 2
    correct_tier2: 3
    correct_tier3: 4
    correct_tier4: 5
    correct_flavor: 1                  # mechanical=False trait, any tier
    incorrect: 0
  thresholds:
    success: 14
    partial: 8
  audience:
    success: 4
    partial: 1
    failure: -2
```

Classification, deltas, and audience effect (audience deltas post-processed
by the shared recovery floor in system doc §5.2):

- `total_points >= 14` → `success`. Relationship delta on partner:
  `RelationshipDelta(affection=+6, trust=+3)`. Audience `+4`.
- `8 <= total_points < 14` → `partial`. Delta `RelationshipDelta(affection=+2)`.
  Audience `+1` (recovery floor lifts to `+3` when audience favor is below
  the floor threshold).
- `total_points < 8` → `failure`. Delta
  `RelationshipDelta(affection=-2, trust=-3)`. Audience `-2` (recovery
  floor dampens to `0` when audience favor is below the floor threshold).

A perfect five-correct round records a `perfect_quiz` memory on the couple
and unlocks a bonus reveal in the wrap (see §5). Note that with the Day-1
pool composition described in §2, hitting "perfect" caps around 11 points
unless the player has pushed familiarity above 25 before the quiz fires.
That's intended — the perfect-quiz bonus is a *real* hero moment that
requires investment, not a Day-1 freebie.

## 4. Knowledge bridge

This minigame is the most direct consumer of the Knowledge Foundation.

- The correct answer for every round is `TraitFact.value` for the
  `(target_id, trait_key)` pair on the partner's Trait Card. The engine
  reads it directly; the Question Bank stem can re-phrase it but the truth
  is pinned in code.
- Distractors are selected with this priority: (1) the matching
  `TraitFact.distractors`, (2) other NPCs' `value` for the same key (good for
  "your partner's hometown is X" — Liverpool/Manchester/Cardiff cross-pollute),
  (3) Question Bank generator-provided flavor distractors.
- Correct picks emit a `MinigameReveal(kind="fact", subject_id=target_id,
  payload={"trait_key": key, "value": value, "delivery": "confirmed"})` and
  write a `KnownFact(..., source="compatibility_quiz", confidence=1.0)` to
  `player.known_facts`.
- Incorrect picks emit `MinigameReveal(kind="fact", ..., payload={...,
  "delivery": "post_reveal"})` and write a `KnownFact(...,
  source="quiz_misread", confidence=0.5)` per the system doc §6.3
  reduced-confidence rule. The player still learns the truth, but the
  ledger flags it as a quiz-derived fact so downstream systems can weight
  it appropriately and so the player cannot cheaply farm Tier 3/4 secrets
  by deliberately guessing wrong.
- Every incorrect pick also writes a `caught_unprepared` memory to the
  partner's memory list with `payload={"trait_key": key}`. Conversation
  Curator may surface this as a rail callback ("She still hasn't forgotten
  that you guessed *Cardiff*.") and the producer may reference it in later
  texts. The memory's effect is narrative-only — no automatic relationship
  delta beyond the round's classification.
- Every round (correct or incorrect) appends `(target_id, trait_key)` to
  `state.quizzed_traits_this_run[target_id]` at the moment of selection,
  not at resolution, so the ledger is correct even if the player walks
  away mid-quiz and resumes from a checkpoint.

## 5. Reveals and wrap

After the final round, the engine emits:

- One `MinigameReveal(kind="reaction", subject_id=partner)` carrying the
  partner's emotional read (`payload = {"tone": "...", "delta": int}`)
  computed from the round-by-round breakdown.
- One `MinigameReveal(kind="fact", ...)` per round (already appended in §4).
- On a perfect quiz, one bonus `MinigameReveal(kind="fact",
  payload={"trait_key": "hidden_secret", "delivery": "bonus"})` — the
  partner shares something they wouldn't normally reveal until Tier 4.

The narrator (Event Narrator) writes the wrap using these reveals. Required
content (graded by the judge):

- Names the actual correct values for every Tier 3+ fact.
- Names the player's actual wrong picks.
- Says the partner's emotional read in their voice.
- Does not invent a new fact, score, or delta.

## 6. Action vocabulary

- Round actions: one `MINIGAME_RESPONSE` per `MinigameChoice` in the current
  round. `payload = {"choice_id": <choice.id>}`. `target_id` unused.
- The producer-text-announce step uses the existing `Producer Event` of
  `kind="challenge"` with `subkind="compatibility_quiz"`. No new action kind
  for announcing.

## 7. Surfaces (checklist)

Following the system doc §8:

**Engine**
- `src/game/engine/challenges.py` — entry in `MinigameKind`,
  `DAILY_CHALLENGE_SCHEDULE`, `score_compatibility_quiz`,
  `apply_compatibility_quiz_result`.
- `src/game/engine/actions.py` — round option emission.
- `src/game/engine/turn.py` — schedule → present → score → apply → narrate.
- `src/game/engine/knowledge.py` — `KnownFact` write on correct/incorrect
  reveal.
- `src/game/state/event_models.py` — shared `MinigameRound`/`MinigameChoice`/
  `MinigameReveal` (one-time shared work).

**Agents**
- `src/game/agents/question_bank.py` — populate `compatibility_quiz` pool.
- `src/game/agents/event_narrator.py` and prompt — extend payload contract
  for `MinigameRound`/`MinigameReveal`.

**Content / balance**
- `content/challenges/compatibility_quiz.md` — flavor copy already exists;
  add tone notes for each classification.
- `data/balance/minigames.yaml` — entry above.

**CLI**
- `src/game/cli/commands/play.py` — interactive multiple choice render.
- `src/game/reporting/slides/scene_renderers.py` — minigame scene type.

**Browser**
- `web/components/stage/ChoiceMenu.tsx` — multiple choice render of the
  round.
- `web/components/stage/GameStage.tsx` — minigame scene shell.
- `web/lib/types.ts`, `web/lib/api.ts` — TS mirrors.

**Tests / evals**
- `tests/engine/test_compatibility_quiz.py` — threshold edges, eligibility
  gates, distractor stability, Day-1 pool composition (3 mechanical +
  2 flavor), wrong-answer confidence (must be 0.5), `caught_unprepared`
  memory written exactly once per incorrect round, and
  `quizzed_traits_this_run` ledger updated on selection not resolution.
- `tests/engine/test_recovery_floor.py` — shared; locks the audience-floor
  math used by every minigame.
- `tests/scenarios/fixtures/compatibility-quiz-vertical.yaml` — three seeds
  hitting `success`, `partial`, `failure`.
- `tests/scenarios/fixtures/compatibility-quiz-low-audience.yaml` — seed
  where audience favor starts below the recovery floor; asserts the
  `partial`-bonus and `failure`-dampener are applied.
- `evals/llm/scenarios/compatibility-quiz-narration.yaml` — narration eval
  with authored intent and judge checks.
- `web/tests/e2e/compatibility-quiz.spec.ts` — Playwright run.

**Docs**
- This file (kept present tense post-merge).
- `docs/current-plan.md` — close the "Compatibility Quiz Vertical Slice"
  item.
- `12-Challenges-And-Events.md` — cross-reference this spec.
- `docs/contract-map.yaml` — already covered if
  `balance_boundary` group includes `docs/minigames/**`.

## 8. Acceptance

A reviewer can:

- Open the review packet for a Day-1 trace and read the five questions, the
  player's picks, the correct answers, the per-round point breakdown, and
  for each round whether it pulled a mechanical or a flavor trait.
- Confirm that on a fresh-partner seed the Day-1 pool composition is three
  mechanical + two flavor, and that the maximum reachable total without
  pre-quiz familiarity investment caps around 11 points.
- Diff a `success` and `failure` checkpoint and see different audience,
  affection, and trust numbers (no narration-derived divergence).
- Diff a `failure` checkpoint at high audience favor (e.g. 60) against the
  same `failure` at low audience favor (e.g. 20) and see the recovery
  floor dampen the second one's audience delta without lifting it above
  zero.
- Confirm that every wrong-answer round wrote `KnownFact(...,
  confidence=0.5)` and a `caught_unprepared` memory, and that
  `state.quizzed_traits_this_run[partner_id]` has all five trait keys.
- Open `evals/llm/scenarios/compatibility-quiz-narration.yaml` and see that
  the authored intent matches the narrator output across all three
  classifications.
- Run `make qa` and have it pass.

## 9. Fun notes

- The Day-1 partner is barely known; failing badly should feel like a *very*
  public faceplant. Lean into the awkward silence in the failure narration.
- A correct Tier 3+ answer is a flex. The narration should show the partner
  registering the depth ("She didn't expect you to know that.").
- A perfect quiz is a Day-1 hero moment that earns the bonus Tier-4 reveal.
  Make sure the audience delta and partner reaction match the scale.
- Wrong answers are the most useful information the player gets all day.
  They should leave the scene with three facts they didn't have, and one
  partner who knows the player didn't have them.
