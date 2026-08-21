# Minigame System

This document defines the shared contract implemented by every Paradise Hearts
daily challenge ("minigame"). The deterministic engine owns rounds, choices,
scoring, reveals, and results. A typed presentation adapter projects that state
into compact browser boards without exposing hidden truth or inventing display
values.

**Read alongside:** [12-Challenges-And-Events.md](../design/12-Challenges-And-Events.md)
(design canon for individual challenges), [paradise-hearts-glossary.md](../reference/paradise-hearts-glossary.md)
(player-facing terminology), [knowledge.md](knowledge.md)
(trait cards / known facts), [03-LLM-Architecture.md](../design/03-LLM-Architecture.md)
(agent boundaries), [qa.md](qa.md) (test layering),
[llm-evals.md](llm-evals.md) (golden scenario format).

Per-minigame specs live under [docs/systems/minigames/](minigames/).

---

## 0. North star

A minigame is a structured player-facing scene with the following properties:

- It is one of the six entries in `DAILY_CHALLENGE_SCHEDULE`.
- It produces real player decisions, not a dice roll. The player picks answers,
  ranks targets, or chooses lie-vs-truth based on information they have
  accumulated through play.
- Its score is computed deterministically in Python from seeded RNG, Known
  Facts, Trait Cards, and recorded play history. No agent ever decides who
  wins, by how much, or which relationship deltas apply.
- Its narration is written by the existing agent layer (Event Narrator,
  Heartbreaker Voice, Conversation Curator) using a typed result payload. The
  agent reveals facts and dramatizes the moment; it never changes the result.
- Its question/prompt pool is generated **once at session start** by a typed
  Question Bank agent (see §4), then cached in `GameState`. Minigame turns
  sample from the bank deterministically. No live LLM call happens inside a
  minigame turn except for narration.
- It is fully reachable in CLI and browser using the same `ActionKind`
  vocabulary, the same `Challenge`-derived state, and the same scene rendering
  in review packets and traces.
- It ships with deterministic unit tests, at least one scenario fixture, and
  a golden LLM eval scenario.

A minigame **never**:

- Decides whether a heartbreaker is eliminated, paired, or unlocked.
  (Eliminations, pairings, and unlocks happen in their owning systems and
  may *consume* a minigame's deltas, but the minigame does not branch them.)
- Persists state outside the seasonal run. Question banks and per-run
  knowledge stay in the run; cross-run carryover is parked
  ([current-plan.md](../current-plan.md), "Later").
- Adds a parallel fact model. All facts a minigame reads or reveals are
  `TraitFact`s already defined in `src/game/state/traits.py`.

---

## 1. Vocabulary

The terms below appear in code, content, and the per-minigame specs.

| Term | Meaning |
|---|---|
| **Minigame** | One of the six entries in `DAILY_CHALLENGE_SCHEDULE`. Also called a "challenge" externally; the per-minigame design canon uses both interchangeably. |
| **Minigame kind** | The discriminator string: `compatibility_quiz`, `heart_rate`, `couples_quiz`, `lie_detector`, `kiss_wed_pass`, `final_couples`. Stable. Never renamed without a snapshot version bump. |
| **Round** | One scored unit inside a minigame (one question, one heart-rate reveal pair, one kiss/wed/pass pick). A minigame is a sequence of 1..N rounds. |
| **Prompt** | A round's player-facing question/setup, drawn from the Question Bank. |
| **Choice** | One discrete option the player can pick. Always part of a finite, engine-validated set. |
| **Reveal** | A fact, chemistry score, or relationship beat that becomes visible to the player as a side effect of resolving a round. |
| **Question Bank** | The per-run, deterministically generated pool of prompts and distractors keyed by minigame kind. Built once at session start, cached in `GameState`. |
| **Result payload** | The typed `MinigameResult` (extending `Challenge`) handed to narration agents. Carries the per-round breakdown, totals, deltas, and reveals. |
| **Surface checklist** | The list of code, content, and docs files a minigame must touch before merging. Same shape for every minigame. |

Player-facing names follow [paradise-hearts-glossary.md](../reference/paradise-hearts-glossary.md):
Compatibility Quiz, Pulse Race (Heart Rate), The Couples Quiz (Mr & Mrs),
Lie Detector, Kiss Wed Pass, Final Couples Challenge. Engine
identifiers keep the underscored forms.

---

## 2. Shared phase shape

Every minigame runs inside a Producer Event of kind `challenge` and progresses
through the same phase ordering. The engine drives the phase clock; the player
drives round-by-round decisions.

```
+----------------+   +----------------+   +-------------+   +-----------+
| announce       |-->| present round  |-->| score round |-->| reveal    |
+----------------+   +----------------+   +-------------+   +-----------+
                          ^   |                 |                 |
                          |   v                 v                 v
                          +---+         (engine, deterministic)   |
                                                                  v
                                                          +---------------+
                                                          | final tally   |
                                                          +---------------+
                                                                  |
                                                                  v
                                                          +---------------+
                                                          | apply deltas  |
                                                          +---------------+
                                                                  |
                                                                  v
                                                          +---------------+
                                                          | narrator wrap |
                                                          +---------------+
```

- **announce**: Event Narrator writes the cold-open beat. Engine has already
  scheduled the `Challenge`, populated `state.pending_challenge`, and surfaced
  the announce event to traces.
- **present round**: Engine reads the next prompt from the Question Bank and
  emits the choice set through `available_actions()`. The CLI renders those
  actions directly. The browser scene uses the same actions in its `ChoiceFan`
  while the minigame module renders a compact typed board.
- **score round**: Engine computes the round's points from the choice + state.
  No LLM call.
- **reveal**: Engine appends any newly visible `KnownFact`s,
  chemistry-rank entries, or per-NPC reaction triples to the result payload.
- **final tally**: After the last round, engine totals points, classifies the
  overall result (`success`, `partial`, `failure`), and computes per-target
  relationship deltas + public perception deltas.
- **apply deltas**: Engine writes `RelationshipDelta`s and audience deltas
  into state, attaches the new facts to `player.known_facts`, and persists.
- **narrator wrap**: Event Narrator produces the closing prose, citing the
  reveals. Heartbreaker Voice may speak the loudest reaction line.

Each step is one engine turn except for **present round** ↔ **score round**,
which advance together when the player submits a choice. The browser and CLI
must render the same round count and the same surfacing order.

---

## 3. State and action schema

### 3.1 Extended `Challenge` model

`src/game/state/event_models.py:Challenge` is the canonical round state. The
checked-in schema and fixtures use one shape; old snapshot schemas are rejected
and regenerated rather than adapted at runtime.

```python
class MinigameRound(BaseModel):
    """One scored unit inside a minigame."""

    model_config = ConfigDict(extra="forbid")

    index: int                              # 0-based
    prompt_id: str                          # FK into the Question Bank
    target_id: str | None = None            # which NPC the round is about
    choices: list[MinigameChoice]           # what the player could pick
    chosen_id: str | None = None            # which choice the player picked
    points: int = 0                         # round score after resolution
    reveals: list[MinigameReveal] = Field(default_factory=list)


class MinigameChoice(BaseModel):
    """One legal player choice in a round."""

    model_config = ConfigDict(extra="forbid")

    id: str                                 # opaque, stable within the round
    label: str                              # short player-facing copy
    fact_value: str | None = None           # the underlying TraitFact value if this is a quiz answer
    is_correct: bool                        # engine-known truth
    distractor_source: Literal["trait_card", "other_npc", "generator", "lie"] = "generator"


class MinigameReveal(BaseModel):
    """A visible side effect surfaced after a round."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["fact", "chemistry_rank", "reaction", "lie_caught", "truth_told"]
    subject_id: str                         # who the reveal is about
    payload: dict[str, str | int] = Field(default_factory=dict)


class Challenge(BaseModel):
    # ... existing fields ...
    rounds: list[MinigameRound] = Field(default_factory=list)
    current_round_index: int = 0
    total_points: int = 0
    classification: Literal["success", "partial", "failure"] | None = None
    audience_delta: int = 0
```

Single-roll fields remain meaningful only for challenge families that still use
the single-roll resolution path. Round-based minigames use `rounds`,
`current_round_index`, `total_points`, `classification`, and `audience_delta`.
No adapter translates between two round formats.

### 3.2 Canonical `ActionKind`

All round choices use the existing canonical action kind:

```python
class ActionKind(StrEnum):
    # ... existing values ...
    CHALLENGE_RESPONSE = "challenge_response"
```

`CHALLENGE_RESPONSE` carries the current round index and selected choice in its
payload. Per round, `available_actions()` emits one action per legal
`MinigameChoice`. Validation rejects a stale round or a choice not present in
the current round. Browser code never rebuilds this choice set from the
minigame projection.

### 3.3 `MinigameKind` enum

`src/game/engine/challenges.py` gains:

```python
class MinigameKind(StrEnum):
    COMPATIBILITY_QUIZ = "compatibility_quiz"
    HEART_RATE = "heart_rate"
    COUPLES_QUIZ = "couples_quiz"
    LIE_DETECTOR = "lie_detector"
    KISS_WED_PASS = "kiss_wed_pass"
    FINAL_COUPLES = "final_couples"
```

`DAILY_CHALLENGE_SCHEDULE` keys this enum. Scenario YAML may still use string
literals; Pydantic coerces.

### 3.4 Player-facing projection

`src/game/presentation/minigame.py` projects `Challenge` into a strict
`MinigameRoundView | MinigameWrapView` union. `status` is the discriminator and
`kind` selects one of six exhaustive board payloads. Narration and the concise
question are separate fields; serializers do not parse questions from prose.

The projection never carries legal choices. `available_actions` is the only
choice authority. It exposes only display-safe engine reveals:

- Compatibility Quiz: latest recorded answer and reaction.
- Couples Quiz: player answer, partner answer, and alignment.
- Pulse Race: recorded performer, observer, BPM, and chemistry readings.
- Lie Detector: recorded subject, verdict, and engine roll.
- Kiss Wed Pass: recorded allocations.
- Final Couples: scored facets and final tally.

The generated OpenAPI types feed the browser aliases. The renderer registry is
exhaustive; an unknown kind fails validation or compilation instead of falling
back to a generic card.

### 3.5 Question Bank

Cached in `GameState` as a top-level field so it survives snapshots and is
deterministic from the seed:

```python
class QuestionBankPrompt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str                                 # stable, e.g. "cq_chloe_biggest_fear_t3_r0"
    minigame_kind: MinigameKind
    target_id: str                          # subject NPC
    trait_key: str                          # which TraitFact this exercises
    tier: int                               # familiarity tier 1-4
    mechanical: bool                        # mirror of TraitFact.mechanical
    stem: str                               # the question phrasing
    correct_value: str                      # mirror of TraitFact.value
    distractors: list[str]                  # 3 plausible wrong answers
    flavor_tags: list[str] = Field(default_factory=list)


class QuestionBank(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompts: dict[str, list[QuestionBankPrompt]]   # keyed by minigame_kind
    bank_seed: int                                 # the sub-seed used to generate it
    schema_version: int                            # for migration


class GameState(BaseModel):
    # ... existing ...
    question_bank: QuestionBank | None = None
    quizzed_traits_this_run: dict[str, list[str]] = Field(default_factory=dict)
    # keyed by target_id; each value is a list of trait_keys already used in
    # any minigame round this season. Round selectors consult this to avoid
    # repeating questions. Reset by checkpoint restore; never written by
    # narration.
```

`question_bank` is `None` until session start finishes; engine code that
accesses it should treat `None` as a programmer error after first-spark.

`quizzed_traits_this_run` is the season-wide repeat-prevention ledger. Every
round selector appends `(target_id, trait_key)` to it the instant a prompt
is chosen — not after the round resolves — so a player who quits mid-round
and resumes does not see the same question twice.

The bank includes **both** mechanical and flavor `TraitFact`s. Mechanical
prompts are the canonical pool; flavor prompts (`mechanical=False`) are the
Day-1 padding pool and the season-wide exhaustion fallback. Round selectors
prefer mechanical prompts when both are eligible; the per-minigame scoring
table assigns flavor prompts a lower point value (see §5.1).

---

## 4. Question Bank agent

A new agent in `src/game/agents/question_bank.py` runs once at session start,
right after `trait_generator` finishes (so every Trait Card is populated).

**Inputs:** the full curated cast, every NPC's `TraitCard`, the locked
seasonal seed, and the schedule of minigames that will run this season.

**Outputs:** a `QuestionBank` with N prompts per minigame kind. Per the
"LLM generates full question pool at run start" decision in chat, the agent
authors stems and any flavor distractors that the trait card doesn't already
provide; the *correct* answer is always pinned to `TraitFact.value` and the
*primary* distractors are always pulled from `TraitFact.distractors` so the
LLM cannot decide what is true.

**Determinism contract:**

- The agent runs at most once per session. Re-runs use cached output.
- In `mock-llm` mode, the bank is produced by a deterministic mock that reads
  Trait Cards directly. Mock and real modes produce *different* phrasings,
  but must produce the same `(target_id, trait_key, correct_value, distractors)`
  for the same seed and trait card set. Tests in
  `tests/agents/test_question_bank.py` assert this invariant.
- The agent uses a derived sub-seed (`rng.spawn("question_bank")`) so its
  randomness is independent of in-session RNG draws.

**Prompt and schema files:**

- `src/game/agents/prompts/question_bank.md` (user-owned per `ENGINEERING.md` R17)
- `src/game/agents/question_bank.py` (typed Pydantic input/output)

**Why up-front, not per-turn:**

- Cheaper per-session token cost than calling the LLM once per round.
- Lets the player feel like the season is a fixed deck of questions a
  reasonable producer would have planned, not improvised mid-show.
- Stabilizes golden eval scenarios: a scenario that pins the seed pins the
  whole bank, so reviewers can read the planned questions before pressing play.

---

## 5. Scoring contract

Every minigame implements one function with this signature:

```python
def score_minigame(
    state: GameState,
    challenge: Challenge,
    rng: SeededRng,
) -> Challenge:
```

Rules:

1. **Pure-ish.** Read state, read `challenge.rounds`, read `rng`. Return a
   `Challenge.model_copy(update=...)` with `total_points`, `classification`,
   `deltas`, `audience_delta`, and per-round `points` filled in.
2. **No LLM calls.** Scoring is deterministic Python.
3. **No state mutation.** Side effects (writing to relationships, audience,
   `known_facts`) live in a separate `apply_minigame_result(...)` step
   called by `engine/turn.py`. This mirrors the existing
   `resolve_challenge` / `apply_relationship_delta` split.
4. **Per-round scoring is bounded.** Round points come from a small lookup
   table per minigame kind. No raw stat formulas inside the round loop.
5. **Classification thresholds are explicit.** Each minigame defines
   integer thresholds for `success` / `partial` / `failure`. They live in
   `data/balance/minigames.yaml` (Pydantic-validated, per
   [decisions/0013-balance-data-boundary.md](../decisions/0013-balance-data-boundary.md)).
6. **Reveals are appended, never overwritten.** Once a `MinigameReveal` is
   on a round, scoring may not remove it.

Per-minigame scoring formulas live in the individual specs under
`docs/systems/minigames/`.

### 5.1 Balance data

`data/balance/minigames.yaml` looks like:

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

heart_rate:
  # ... etc

recovery_floor:
  # Shared across all minigames. See §5.2.
  audience_threshold: 35
  partial_audience_bonus: 2
  failure_audience_dampener: 2
```

The shape is validated by a new Pydantic model in `src/game/content/models.py`
and read by `engine/challenges.py`. Tests in
`tests/content/test_balance_minigames.py` lock the contract.

### 5.2 Audience recovery floor

To prevent a single-bad-minigame snowball, every minigame's audience delta
is post-processed by a shared recovery rule:

- If `state.player.public_perception < recovery_floor.audience_threshold`:
  - A `partial` classification's audience delta is increased by
    `partial_audience_bonus`.
  - A `failure` classification's audience delta is reduced (closer to zero)
    by `failure_audience_dampener`, but never above zero. A failure stays a
    failure; it just doesn't bury you further when you're already low.
- A `success` is never modified. The recovery floor only softens floors, it
  never lifts ceilings.

This is the "underdog arc" beat — the reality-TV convention that a player
who's already losing the audience gets meaningful (but not free) ground to
recover. Implemented once in `engine/challenges.py:apply_recovery_floor()`
and called by every `apply_*_result` helper. Tests in
`tests/engine/test_recovery_floor.py` lock the math.

---

## 6. Knowledge bridge

Minigames are the primary payoff for the Knowledge Foundation. The bridge
rules below apply to every minigame; per-minigame specs may add more.

1. **Eligibility is gated by familiarity.** A round about NPC `X` and
   `trait_key`=`biggest_fear` only renders if
   `state.player.familiarity_with(X) >= TIER_THRESHOLDS[3]` *or* the trait has
   already been revealed via a `KnownFact` with sufficient confidence. The
   Question Bank still includes ineligible prompts; the round selector skips
   them at runtime.
2. **Distractors are picked from the bank, in deterministic order.** The
   round selector samples three distractors per question using
   `rng.spawn(f"minigame::{kind}::{round_index}")`. If a TraitFact already
   provides distractors, those are used first.
3. **Wrong answers reveal partial knowledge, at reduced confidence.** A
   round that ends with the player picking a distractor emits a
   `MinigameReveal(kind="fact", payload={"trait_key": key, "value":
   correct_value, "delivery": "post_reveal"})` and writes
   `KnownFact(..., source="quiz_misread", confidence=0.5)` to
   `player.known_facts`. The reduced confidence stops the player from
   exploiting wrong-answer reveals to learn Tier 3/4 secrets faster than
   conversation allows, and lets downstream systems weight quiz-derived
   facts below conversation-derived ones. The partner additionally records
   a `caught_unprepared` memory the producer and Conversation Curator can
   reference for the rest of the season.
4. **Quiz minigames never request facts the LLM has not previously surfaced.**
   The Trait Generator is the only producer of canonical facts. The Question
   Bank only re-uses what's already on a Trait Card.
5. **Repeat-prevention is season-wide.** Round selectors append every
   `(target_id, trait_key)` pair they choose to
   `state.quizzed_traits_this_run[target_id]`. Subsequent rounds skip pairs
   already in the ledger. When the eligible pool is exhausted (a real
   possibility on Day 4+, since each NPC has 12 mechanical fields and
   multiple minigames quiz the partner), the selector falls back in this
   order:
     a. Eligible flavor traits (`mechanical=False`) not yet quizzed.
     b. Eligible mechanical traits the player has *also* revealed about
        themselves to that NPC (reciprocal questions; only applies in
        Couples Quiz).
     c. Last-resort repeats from earlier in the season, marked with
        `MinigameReveal(payload={"repeat": True})` so the narrator can
        play it as a callback ("They're asking you about her job *again*…").
   The fallback ladder is the same across every minigame so the harness
   stays simple.

---

## 7. Narration contract

The Event Narrator is the primary writer; Heartbreaker Voice writes individual
reaction lines; Conversation Curator may write a recap line for the rail.

**Inputs handed to the narrator:**

- The fully resolved `Challenge` with all rounds, points, classification,
  deltas, and reveals.
- The Heartbreaker Voice context bundle for any speaking NPCs.
- The relevant `PersonaSummary`s.

**What the narrator must do:**

- Mention the actual question text, the actual player choice label, and any
  reveal payload values.
- Reflect the classification's tone (triumph / mixed / awkward).
- Cite the reveal source (e.g., "Chloe's love language is acts of service —
  you guessed quality time") so reviewers can verify faithfulness.

**What the narrator must not do:**

- Invent a different score.
- Add reveals that were not on the result payload.
- Decide a relationship moved.
- Say the player won when `classification == "failure"`.

The golden judge rubric in `src/game/eval/golden_judge.py` already grades
"faithfulness to engine result"; minigame scenarios extend that with a
`minigame_reveal_present` check (§10).

---

## 8. Surfacing checklist

The implemented system has one owner per concern:

| Concern | Owner |
|---|---|
| Schedule, round construction, scoring, and reveals | `src/game/engine/challenges.py` and the per-kind engine modules |
| Legal player choices | `src/game/engine/actions.py` and `available_actions()` |
| Persisted round truth | `src/game/state/event_models.py` |
| Display-safe HTTP projection | `src/game/presentation/minigame.py` |
| API field and generated contract | `src/api/models.py`, `src/api/serializers.py`, `web/lib/openapi-types.ts` |
| Browser interpretation and scene port | `web/lib/minigame/` |
| Compact board renderers | `web/components/minigame/` |
| Scene sequencing and action lanes | `web/lib/scene/` and `web/components/scene/` |
| CLI and reports | `src/game/cli/` and `src/game/reporting/` |
| Mechanical balance | `data/balance/minigames.yaml` |
| Flavor | `content/challenges/` |

A change to a minigame kind must update every owner whose contract changes. A
new reveal kind starts in engine state and the Pydantic projection, then flows
through OpenAPI generation and the exhaustive browser renderer. Browser-only
mechanics and hand-written TypeScript mirrors are not valid shortcuts.

---

## 9. Determinism rules

- Question Bank generation uses a sub-seed derived from `state.seed`. Two
  runs with the same seed produce the same bank.
- Round prompt order, distractor selection, and any randomized reveal
  ordering use sub-seeds derived from the minigame kind and round index.
- Per-round timing or animation budgets in the browser do **not** feed back
  into the engine. Browser animation never decides a result.
- `verify-script` and `play --replay` reproduce the exact same minigame
  outputs.

The existing checkpoint/branch-compare contract
([decisions/0008-snapshot-and-trace-architecture.md](../decisions/0008-snapshot-and-trace-architecture.md))
extends across minigames because the new fields all live on `Challenge`,
which is already snapshotted.

---

## 10. Eval policy

Every minigame ships with **three** eval surfaces, matching the layering in
[qa.md](qa.md) and [llm-evals.md](llm-evals.md):

1. **Engine unit tests** (`tests/engine/test_<minigame>.py`)
   - Scoring at threshold edges.
   - Ineligible rounds skipped.
   - Distractor sampling stable across seeds.
   - `apply_minigame_result` writes the expected deltas.

2. **Scenario fixture** (`tests/scenarios/fixtures/<minigame>-vertical.yaml`)
   - Drives the minigame end-to-end via `verify-script`.
   - Locked golden output via existing golden-state checks.

3. **Golden LLM eval scenario** (`evals/llm/scenarios/<minigame>-narration.yaml`)
   - Authored intent: the question, the player's pick, the deterministic
     classification, and the required reveals.
   - Checks under [evals/llm/scenarios/FORMAT.md](../../evals/llm/scenarios/FORMAT.md):
     `minigame_reveal_present`, `narration_mentions_choice_label`,
     `no_invented_facts`, `classification_consistent`.
   - Runs under `make llm-eval-mock` in CI; opt-in under
     `make llm-eval-real-judge` for human review.

A minigame is not ready to merge until all three layers exist and pass.

---

## 11. Implemented schedule

All six scheduled minigames use the shared harness:

| Day | Minigame | Distinct contract exercised |
| --- | --- | --- |
| 1 | Compatibility Quiz | Trait-card questions and deterministic distractors |
| 2 | Pulse Race | Reveal-driven rounds and reactions |
| 3 | The Couples Quiz | Two-sided partner answers |
| 4 | Lie Detector | Truth/lie choices grounded in known facts and event history |
| 5 | Kiss Wed Pass | Constrained allocation across multiple targets |
| 6 | Final Couples Challenge | Couple-level scoring and season aggregation |

Future work improves presentation and coverage; it does not maintain a second
legacy challenge path.

Per-kind mechanics remain in the owning specs under `docs/systems/minigames/`.
The shared presentation contract stays deliberately smaller than those
mechanics: it carries only truthful display values and never legal choices.

---

## 12. Fun checklist

A minigame is "fun" if a reviewer can answer "yes" to all of these after one
playthrough:

- I made at least one decision I had to think about.
- I learned something about an NPC I didn't know before — or I felt the
  consequence of having ignored someone.
- The result felt earned, not random. I could trace the score back to my
  picks.
- The narration named the actual question, the actual answer, and the
  actual reveal — not a paraphrase of them.
- The classification (success / partial / failure) matched the emotional
  beat. A failure should sting; a partial should feel awkward; a success
  should pop.
- The next minigame, day, or social event felt different because of how
  this one resolved.

The per-minigame specs each have a "Fun notes" section that names the
specific moments to lean into for that kind.

---

## 13. Deliberate POC limits

- Rewinding to a pre-session checkpoint follows the existing seeded replay
  contract; no special minigame reroll path exists.
- Pulse Race reveals use compact rows. Presentation timing never feeds back
  into engine state.
- The game does not add anti-grinding mechanics for checkpoint reloads.
- Knowledge-backed questions use the engine's eligibility rules. The browser
  does not compensate for hidden or missing facts.
