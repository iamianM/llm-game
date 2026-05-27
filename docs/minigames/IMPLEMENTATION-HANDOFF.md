# Minigame Implementation — Handoff

**Status:** docs landed (`19b2567a doc updates`); implementation NOT started.
**Why:** the Cowork sandbox runs Python 3.10 and cannot install Python 3.11+ (no network access to python-build-standalone releases). The project requires 3.11+ (`from enum import StrEnum`). Without a working interpreter the implementation cannot be verified, scenario fixture `expected_hash` values cannot be regenerated, and `make qa` cannot run. Code can be *written* in the sandbox but every assertion of correctness would be unfounded. The honest move was to stop, leave the working tree clean, and write this handoff so the implementation resumes from a Windows shell where Python 3.11 + the project venv are available.

**Run from Windows-side** (PowerShell or cmd, not Cowork):

```
cd C:\Users\Mcian\projects\llm-game
# Re-create venv if needed:
uv sync
# Sanity:
uv run python -m src.game.cli verify --all
make qa
```

The rest of this document is the exact implementation plan. Sections map one-to-one to the file changes the PR will make. Code blocks are paste-ready against the current `master` (`19b2567a`).

---

## 0. Pre-flight

- `SCHEMA_VERSION` will bump 25 → 26 (`src/game/state/models.py:43`). Every scenario fixture under `tests/scenarios/fixtures/` carries an `expected_hash`; those values become stale once new fields land on `GameState` / `Challenge`. Plan to regenerate them in step 6.
- The implementation does *not* break the legacy single-roll `resolve_challenge` path. The other five minigames (`heart_rate`, `mr_and_mrs`, `lie_detector`, `snog_marry_pie`, `final_couples`) continue to run through the old path until each gets its own PR per the per-minigame specs. Only `compatibility_quiz` is migrated to the new round-based harness in this PR.
- The Question Bank ships in **mock mode only** in this PR (deterministic generation from existing Trait Cards). The live OpenAI Question Bank agent is a follow-up; the mock implementation already lets every other surface ship.

---

## 1. Schema additions — `src/game/state/event_models.py`

Append these classes; do not modify existing `Challenge` (it picks them up via new optional fields lower down):

```python
class MinigameChoice(BaseModel):
    """One legal player choice in a minigame round."""
    model_config = ConfigDict(extra="forbid")
    id: str
    label: str
    fact_value: str | None = None
    is_correct: bool = False
    distractor_source: Literal["trait_card", "other_npc", "generator", "lie"] = "generator"


class MinigameReveal(BaseModel):
    """A visible side effect surfaced after a minigame round."""
    model_config = ConfigDict(extra="forbid")
    kind: Literal["fact", "chemistry_rank", "reaction", "lie_caught", "truth_told"]
    subject_id: str
    payload: dict[str, str | int] = Field(default_factory=dict)


class MinigameRound(BaseModel):
    """One scored unit inside a minigame."""
    model_config = ConfigDict(extra="forbid")
    index: int
    prompt_id: str
    target_id: str | None = None
    trait_key: str | None = None
    tier: int = 0
    mechanical: bool = True
    stem: str = ""
    choices: list[MinigameChoice] = Field(default_factory=list)
    chosen_id: str | None = None
    points: int = 0
    reveals: list[MinigameReveal] = Field(default_factory=list)


class QuestionBankPrompt(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    minigame_kind: str
    target_id: str
    trait_key: str
    tier: int = Field(ge=0, le=4)
    mechanical: bool = True
    stem: str
    correct_value: str
    distractors: list[str] = Field(default_factory=list)
    flavor_tags: list[str] = Field(default_factory=list)


class QuestionBank(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int = 1
    bank_seed: int
    prompts: dict[str, list[QuestionBankPrompt]] = Field(default_factory=dict)
```

Then extend `Challenge` (no field reordering — append only):

```python
class Challenge(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    day: int
    kind: str
    stat_tested: Literal["charm", "banter", "eq", "graft", "loyalty", "combined"]
    participants: list[str] = Field(default_factory=list)
    player_choice: str | None = None
    result: Literal["success", "failure"] | None = None
    deltas: dict[str, RelationshipDelta] = Field(default_factory=dict)
    # Round-based shape; populated only by minigames migrated to the new harness.
    rounds: list[MinigameRound] = Field(default_factory=list)
    current_round_index: int = 0
    total_points: int = 0
    classification: Literal["success", "partial", "failure"] | None = None
    audience_delta: int = 0
```

---

## 2. KnownFact source enum — `src/game/state/traits.py`

```python
source: Literal[
    "direct",
    "social_event",
    "gossip",
    "witnessed",
    "compatibility_quiz",
    "quiz_misread",
]
```

The two new values are written by the Compatibility Quiz apply step (see §7).

---

## 3. GameState additions — `src/game/state/models.py`

Bump and add. Place `quizzed_traits_this_run` and `question_bank` near `pending_challenge`:

```python
SCHEMA_VERSION = 26

# ... inside GameState ...
pending_challenge: Challenge | None = None
quizzed_traits_this_run: dict[str, list[str]] = Field(default_factory=dict)
question_bank: QuestionBank | None = None
```

Also re-export `QuestionBank` and `QuestionBankPrompt` from the top of `models.py` for downstream imports.

---

## 4. Balance data — new file `data/balance/minigames.yaml`

```yaml
recovery_floor:
  audience_threshold: 35
  partial_audience_bonus: 2
  failure_audience_dampener: 2

compatibility_quiz:
  rounds: 5
  per_round_points:
    correct_tier1: 2
    correct_tier2: 3
    correct_tier3: 4
    correct_tier4: 5
    correct_flavor: 1
    incorrect: 0
  thresholds:
    success: 14
    partial: 8
  audience:
    success: 4
    partial: 1
    failure: -2
```

Pydantic loader — new file `src/game/content/minigame_balance.py`:

```python
"""Validated minigame balance data."""
from __future__ import annotations
from pathlib import Path
from typing import Annotated
import yaml
from pydantic import BaseModel, ConfigDict, Field


class RecoveryFloor(BaseModel):
    model_config = ConfigDict(extra="forbid")
    audience_threshold: int = Field(ge=0, le=100)
    partial_audience_bonus: int = Field(ge=0)
    failure_audience_dampener: int = Field(ge=0)


class CompatQuizPoints(BaseModel):
    model_config = ConfigDict(extra="forbid")
    correct_tier1: int
    correct_tier2: int
    correct_tier3: int
    correct_tier4: int
    correct_flavor: int
    incorrect: int


class CompatQuizThresholds(BaseModel):
    model_config = ConfigDict(extra="forbid")
    success: int
    partial: int


class CompatQuizAudience(BaseModel):
    model_config = ConfigDict(extra="forbid")
    success: int
    partial: int
    failure: int


class CompatibilityQuizBalance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rounds: int = Field(ge=1)
    per_round_points: CompatQuizPoints
    thresholds: CompatQuizThresholds
    audience: CompatQuizAudience


class MinigameBalance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recovery_floor: RecoveryFloor
    compatibility_quiz: CompatibilityQuizBalance


_PATH = Path("data/balance/minigames.yaml")
_CACHE: MinigameBalance | None = None


def load_minigame_balance() -> MinigameBalance:
    global _CACHE
    if _CACHE is None:
        _CACHE = MinigameBalance.model_validate(yaml.safe_load(_PATH.read_text(encoding="utf-8")))
    return _CACHE
```

---

## 5. Recovery floor helper — `src/game/engine/challenges.py`

```python
def apply_recovery_floor(state: GameState, audience_delta: int, classification: str) -> int:
    """Shared minigame audience-floor rule. See docs/minigame-system.md §5.2."""
    from src.game.content.minigame_balance import load_minigame_balance
    floor = load_minigame_balance().recovery_floor
    if state.player.public_perception >= floor.audience_threshold:
        return audience_delta
    if classification == "partial":
        return audience_delta + floor.partial_audience_bonus
    if classification == "failure":
        return min(0, audience_delta + floor.failure_audience_dampener)
    return audience_delta  # success unchanged
```

---

## 6. Mock-mode Question Bank — new module `src/game/engine/question_bank.py`

```python
"""Mock-mode Question Bank generator. Live agent ships separately."""
from __future__ import annotations
from src.game.state.event_models import QuestionBank, QuestionBankPrompt
from src.game.state.models import GameState
from src.game.state.rng import SeededRng


def build_question_bank(state: GameState) -> QuestionBank:
    """Deterministically derive a Question Bank from current Trait Cards."""
    rng = SeededRng(state.seed).fork("question_bank")
    prompts: dict[str, list[QuestionBankPrompt]] = {"compatibility_quiz": []}
    for islander in state.islanders:
        card = islander.trait_card
        for key, fact in {**card.core_traits, **card.flavor_traits}.items():
            prompts["compatibility_quiz"].append(QuestionBankPrompt(
                id=f"cq_{islander.id}_{key}",
                minigame_kind="compatibility_quiz",
                target_id=islander.id,
                trait_key=key,
                tier=fact.tier,
                mechanical=fact.mechanical,
                stem=_mock_stem(islander.name, key),
                correct_value=fact.value,
                distractors=list(fact.distractors),
            ))
    return QuestionBank(bank_seed=rng.next_int(), prompts=prompts)


_STEMS = {
    "occupation": "What does {name} do for work?",
    "hometown": "Where is {name} from?",
    "age": "How old is {name}?",
    "favorite_food": "What's {name}'s favourite meal?",
    "hobby": "How does {name} spend their free time?",
    "drink_of_choice": "What's {name}'s usual drink?",
    "biggest_fear": "What's {name}'s biggest fear?",
    "love_language": "What's {name}'s love language?",
    "worst_habit": "What's {name}'s worst habit?",
    "pet_peeve": "What's {name}'s biggest pet peeve?",
    "insecurity": "What is {name} most insecure about?",
    "past_heartbreak": "What was {name}'s last heartbreak?",
    "hidden_secret": "What is {name} hiding from the villa?",
}


def _mock_stem(name: str, key: str) -> str:
    return _STEMS.get(key, f"Tell us about {name}'s {key.replace('_', ' ')}.")
```

Call site: at the end of `engine/turn_events.py:_run_intros` or the first turn after First Spark, set `state.question_bank = build_question_bank(state)` if it's `None`.

---

## 7. Compatibility Quiz — new module `src/game/engine/compatibility_quiz.py`

```python
"""Compatibility Quiz minigame implementation."""
from __future__ import annotations
from src.game.content.minigame_balance import load_minigame_balance
from src.game.engine.challenges import apply_recovery_floor
from src.game.engine.state_access import apply_relationship_delta, find_islander
from src.game.engine.couples import player_couple
from src.game.state.event_models import (
    Challenge, MinigameChoice, MinigameReveal, MinigameRound,
)
from src.game.state.models import GameState, RelationshipDelta
from src.game.state.rng import SeededRng
from src.game.state.traits import KnownFact, TIER_THRESHOLDS


def build_rounds(state: GameState, target_id: str, rng: SeededRng) -> list[MinigameRound]:
    """Build five eligible quiz rounds with priority: T2+ mech → T1 mech → flavor → fallback."""
    bank = state.question_bank
    assert bank is not None, "question_bank must be initialized before minigame start"
    target = find_islander(state, target_id)
    used = set(state.quizzed_traits_this_run.get(target_id, []))
    pool = [p for p in bank.prompts.get("compatibility_quiz", []) if p.target_id == target_id]

    def eligible(p) -> bool:
        if p.trait_key in used:
            return False
        if not p.mechanical:
            return True
        if p.tier <= 1:
            return True
        if target.familiarity_with_player >= TIER_THRESHOLDS[p.tier]:
            return True
        # KnownFact escape: a fact previously revealed is eligible regardless of familiarity.
        return any(kf.fact_key == f"{target_id}.{p.trait_key}" and kf.confidence >= 0.7
                   for kf in state.player.known_facts.values())

    tier_buckets = (
        [p for p in pool if p.mechanical and p.tier >= 2 and eligible(p)],
        [p for p in pool if p.mechanical and p.tier == 1 and eligible(p)],
        [p for p in pool if not p.mechanical and eligible(p)],
    )
    selected: list[Any] = []
    for bucket in tier_buckets:
        bucket.sort(key=lambda p: p.id)  # deterministic
        for p in bucket:
            if len(selected) >= 5:
                break
            selected.append(p)
        if len(selected) >= 5:
            break
    # Exhaustion fallback: repeats from earlier in season.
    if len(selected) < 5:
        for p in pool:
            if p in selected:
                continue
            selected.append(p)
            if len(selected) >= 5:
                break

    rounds: list[MinigameRound] = []
    for index, p in enumerate(selected[:5]):
        round_rng = rng.fork(f"compat_quiz::round::{index}")
        # Build choices: correct + up to 3 distractors.
        distractors = list(p.distractors)
        round_rng.shuffle(distractors)
        choices_in: list[MinigameChoice] = [
            MinigameChoice(id="correct", label=p.correct_value, fact_value=p.correct_value,
                           is_correct=True, distractor_source="trait_card"),
        ]
        for d_index, d in enumerate(distractors[:3]):
            choices_in.append(MinigameChoice(id=f"distractor_{d_index}", label=d,
                                              fact_value=d, is_correct=False,
                                              distractor_source="trait_card"))
        round_rng.shuffle(choices_in)
        rounds.append(MinigameRound(
            index=index, prompt_id=p.id, target_id=target_id, trait_key=p.trait_key,
            tier=p.tier, mechanical=p.mechanical, stem=p.stem, choices=choices_in,
        ))
        state.quizzed_traits_this_run.setdefault(target_id, []).append(p.trait_key)
    return rounds


def score_compatibility_quiz(state: GameState, challenge: Challenge) -> Challenge:
    bal = load_minigame_balance().compatibility_quiz
    total = 0
    new_rounds: list[MinigameRound] = []
    for r in challenge.rounds:
        chosen = next((c for c in r.choices if c.id == r.chosen_id), None)
        correct = chosen is not None and chosen.is_correct
        if correct:
            if not r.mechanical:
                pts = bal.per_round_points.correct_flavor
            else:
                pts = getattr(bal.per_round_points, f"correct_tier{r.tier}")
        else:
            pts = bal.per_round_points.incorrect
        total += pts
        new_rounds.append(r.model_copy(update={"points": pts}))
    if total >= bal.thresholds.success:
        classification = "success"
    elif total >= bal.thresholds.partial:
        classification = "partial"
    else:
        classification = "failure"
    audience = getattr(bal.audience, classification)
    audience = apply_recovery_floor(state, audience, classification)
    return challenge.model_copy(update={
        "rounds": new_rounds,
        "total_points": total,
        "classification": classification,
        "audience_delta": audience,
        "result": "success" if classification != "failure" else "failure",
    })


def apply_compatibility_quiz_result(state: GameState, challenge: Challenge) -> None:
    """Side effects: relationship deltas, audience, KnownFacts, caught_unprepared memories."""
    target_id = challenge.participants[1] if len(challenge.participants) > 1 else "chloe"
    target = find_islander(state, target_id)
    cls = challenge.classification
    if cls == "success":
        delta = RelationshipDelta(affection=6, trust=3)
    elif cls == "partial":
        delta = RelationshipDelta(affection=2)
    else:
        delta = RelationshipDelta(affection=-2, trust=-3)
    apply_relationship_delta(target, delta)
    state.player.public_perception = max(0, min(100,
        state.player.public_perception + challenge.audience_delta))
    # KnownFact + caught_unprepared writes:
    for r in challenge.rounds:
        chosen = next((c for c in r.choices if c.id == r.chosen_id), None)
        if chosen is None or r.trait_key is None:
            continue
        correct = chosen.is_correct
        fact_key = f"{target_id}.{r.trait_key}"
        correct_value = next(c.fact_value for c in r.choices if c.is_correct)
        state.player.known_facts[fact_key] = KnownFact(
            fact_key=fact_key, value=correct_value or "",
            source="compatibility_quiz" if correct else "quiz_misread",
            source_npc_id=target_id, learned_on_day=state.day, learned_on_turn=state.turn_index,
            confidence=1.0 if correct else 0.5,
            citation=f"compatibility_quiz day {state.day}",
        )
        if not correct:
            target.memories.append(_caught_unprepared_memory(state, r.trait_key))
```

(The `_caught_unprepared_memory` helper produces a `Memory` matching the schema in `src/game/state/memory.py`.)

---

## 8. Wire into the turn pipeline — `src/game/engine/turn_events.py`

In `_scheduled_phase_events`, branch on kind:

```python
if state.phase.value == "challenge":
    challenge = schedule_challenge(state.day)
    if challenge is not None:
        state.pending_challenge = challenge
        if challenge.kind == "compatibility_quiz":
            from src.game.engine.compatibility_quiz import build_rounds
            target_id = _quiz_partner_id(state)
            challenge.rounds = build_rounds(state, target_id, rng.fork(f"compat_quiz_{state.day}"))
            challenge.participants = ["player", target_id]
        elif challenge.kind != "snog_marry_pie":
            state.pending_challenge = resolve_challenge(state, challenge, rng.fork(f"challenge-{state.day}"))
        events.append(...)
```

In `engine/rules.py`, add a path for the round-based Compat Quiz response in `_apply_challenge_response` that delegates to `compatibility_quiz.score_compatibility_quiz` + `apply_compatibility_quiz_result` when `state.pending_challenge.kind == "compatibility_quiz"`. Set `state.pending_challenge.current_round_index += 1` until the last round, then score + apply.

---

## 9. Available actions for Compat Quiz rounds — `src/game/engine/actions.py`

Extend the existing `pending_challenge` block:

```python
if state.pending_challenge is not None and state.pending_challenge.result is None:
    if state.pending_challenge.kind == "compatibility_quiz":
        current = state.pending_challenge.rounds[state.pending_challenge.current_round_index]
        for choice in current.choices:
            actions.append(ActionSpec(
                action=PlayerAction(
                    kind=ActionKind.CHALLENGE_RESPONSE,
                    target_id=state.pending_challenge.participants[1] if len(state.pending_challenge.participants) > 1 else "chloe",
                    payload={"choice_id": choice.id},
                ),
                label=f"Compat Quiz r{current.index+1}: {choice.label}",
            ))
        return actions
    if state.pending_challenge.kind == "snog_marry_pie":
        # ... existing block ...
```

---

## 10. Tests — `tests/engine/test_compatibility_quiz.py`

Cover:
- `build_question_bank` is deterministic for a fixed seed (hash the dump).
- `build_rounds` produces exactly 5 rounds with no duplicate trait_keys.
- Day-1 fresh-partner pool composition (familiarity 10): expect 3 mechanical + 2 flavor.
- Scoring at threshold edges: 7 (failure), 8 (partial), 13 (partial), 14 (success).
- Recovery floor: audience 30 + failure → audience delta clamped to 0; audience 60 + failure → -2.
- Wrong-answer side effects: `KnownFact(source="quiz_misread", confidence=0.5)` written; `caught_unprepared` memory present once per wrong round; `quizzed_traits_this_run[target_id]` updated.
- Determinism: same seed → identical `state_hash` after a full run.

---

## 11. Scenario fixtures

- `tests/scenarios/fixtures/compatibility-quiz-vertical.yaml` — three seeds, one for each classification.
- `tests/scenarios/fixtures/compatibility-quiz-low-audience.yaml` — recovery-floor path.

Regenerate every other fixture's `expected_hash` because GameState shape changed. Helper:

```
uv run python -m src.game.cli verify --regenerate-hashes
```

If that flag doesn't exist yet, add it. Otherwise hand-edit by running `verify --playthrough` on each and copying the printed hash.

---

## 12. Golden LLM eval — `evals/llm/scenarios/compatibility-quiz-narration.yaml`

Follow the existing `challenge-result-narration.yaml` pattern. Authored intent: the question stems, the player's picks (one of each: tier1 correct, tier3 wrong, flavor correct, tier2 wrong, tier3 correct), the deterministic classification, the required reveals. Judge checks: `minigame_reveal_present`, `narration_mentions_choice_label`, `no_invented_facts`, `classification_consistent`.

---

## 13. CLI rendering — `src/game/cli/commands/play.py`

The interactive play loop already renders `available_actions()` as a numbered menu. The new round-based actions surface naturally because they emit `ActionSpec` with `label`. The only extra work is to render the question stem above the choice list, by checking for `state.pending_challenge` and printing the current round's stem before the action menu.

---

## 14. Browser wiring — `web/components/stage/ChoiceMenu.tsx`

`ChoiceMenu` already renders actions returned by the API. The API serializes `available_actions()` into the typed `Action[]` shape consumed by `web/lib/types.ts`. The only browser-side change is in `web/components/stage/GameStage.tsx`: when `state.pending_challenge?.kind === "compatibility_quiz"`, render the current round's `stem` and `current_round_index + 1 / total` above the choice menu. Mirror the new `Challenge` fields in `web/lib/types.ts`.

---

## 15. QA gate

```
make qa
```

Should pass once §1-14 are in. Then opt-in:

```
make llm-eval-real-judge
```

---

## 16. After Compatibility Quiz merges

The per-minigame specs under `docs/minigames/` are paste-ready for the next five. Each is one PR. Order per `current-plan.md`: Couples Quiz, Lie Detector, Pulse Race, Kiss Wed Pass, Final Couples. The shared harness should not need to change for the next two; reassess after Lie Detector lands.

---

## What this PR is *not*

- Live OpenAI Question Bank agent. Mock mode only. Live agent is a follow-up PR (~100 lines in `src/game/agents/question_bank.py`, prompt at `src/game/agents/prompts/question_bank.md`).
- Couples Quiz, Lie Detector, Pulse Race, Kiss Wed Pass, Final Couples. Separate PRs.
- Browser polish: the round renders functionally but visual treatment (progress dots, reveal animations) is deferred to a UI polish pass.
- Cross-run persistence of `quizzed_traits_this_run`. Single-season only, matching `current-plan.md` "Persistent Knowledge Across Runs" being parked.
