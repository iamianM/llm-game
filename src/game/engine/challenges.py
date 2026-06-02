"""Deterministic daily challenge resolution.

Legacy challenges resolve via :func:`resolve_challenge` (single dice roll). New
round-based minigames (currently only ``compatibility_quiz``) bypass that path
and use the shared harness in ``docs/minigame-system.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, cast

from src.game.engine.audience import player_couple
from src.game.engine.state_access import apply_relationship_delta, find_heartbreaker
from src.game.state.models import Challenge, GameState, RelationshipDelta
from src.game.state.rng import SeededRng

ChallengeStat = Literal["charm", "banter", "eq", "spark", "loyalty", "combined"]


class MinigameKind(StrEnum):
    """Canonical minigame discriminator."""

    COMPATIBILITY_QUIZ = "compatibility_quiz"
    HEART_RATE = "heart_rate"
    COUPLES_QUIZ = "couples_quiz"
    LIE_DETECTOR = "lie_detector"
    KISS_WED_PASS = "kiss_wed_pass"
    FINAL_COUPLES = "final_couples"


ROUND_BASED_MINIGAMES: set[str] = {
    MinigameKind.COMPATIBILITY_QUIZ.value,
    MinigameKind.HEART_RATE.value,
    MinigameKind.KISS_WED_PASS.value,
    MinigameKind.COUPLES_QUIZ.value,
    MinigameKind.LIE_DETECTOR.value,
    MinigameKind.FINAL_COUPLES.value,
}


@dataclass(frozen=True)
class ChallengeDef:
    """Static challenge schedule entry."""

    id: str
    day: int
    kind: str
    stat_tested: str


DAILY_CHALLENGE_SCHEDULE: dict[int, ChallengeDef] = {
    1: ChallengeDef("compatibility_quiz", 1, "compatibility_quiz", "eq"),
    2: ChallengeDef("heart_rate", 2, "heart_rate", "charm"),
    3: ChallengeDef("couples_quiz", 3, "couples_quiz", "banter"),
    4: ChallengeDef("lie_detector", 4, "lie_detector", "loyalty"),
    5: ChallengeDef("kiss_wed_pass", 5, "kiss_wed_pass", "banter"),
    6: ChallengeDef("final_couples", 6, "final_couples", "combined"),
}

CHOICE_REQUIRED_CHALLENGES = ROUND_BASED_MINIGAMES


def apply_recovery_floor(state: GameState, audience_delta: int, classification: str) -> int:
    """Shared minigame audience floor; see docs/minigame-system.md §5.2."""
    from src.game.content.minigame_balance import load_minigame_balance
    floor = load_minigame_balance().recovery_floor
    if state.player.public_perception >= floor.audience_threshold:
        return audience_delta
    if classification == "partial":
        return audience_delta + floor.partial_audience_bonus
    if classification == "failure":
        return min(0, audience_delta + floor.failure_audience_dampener)
    return audience_delta


def schedule_challenge(day: int) -> Challenge | None:
    """Create the challenge for ``day`` without resolving it."""
    definition = DAILY_CHALLENGE_SCHEDULE.get(day)
    if definition is None:
        return None
    return Challenge(
        id=definition.id,
        day=day,
        kind=definition.kind,
        stat_tested=cast(ChallengeStat, definition.stat_tested),
        participants=["player"],
    )


def resolve_challenge(
    state: GameState,
    challenge: Challenge,
    rng: SeededRng,
    *,
    choice: str | None = None,
) -> Challenge:
    """Legacy single-roll resolution (kept for non-migrated minigames)."""
    if challenge.result is not None:
        return challenge
    if challenge.kind in CHOICE_REQUIRED_CHALLENGES and not choice:
        return challenge
    target_id = _challenge_target_id(state, choice)
    chance = _challenge_success_chance(state, challenge)
    success = rng.randint(1, 100) <= chance
    delta = _challenge_delta(challenge.kind, success)
    target = find_heartbreaker(state, target_id)
    apply_relationship_delta(target, delta)
    state.player.public_perception = max(
        0,
        min(100, state.player.public_perception + _perception_delta(challenge.kind, success)),
    )
    return challenge.model_copy(
        update={
            "participants": ["player", target_id],
            "player_choice": choice,
            "result": "success" if success else "failure",
            "deltas": {target_id: delta},
        }
    )


def challenge_event_message(challenge: Challenge) -> str:
    """Return a concise narratable challenge event message."""
    if challenge.classification is not None:
        return (
            f"{_challenge_label(challenge.kind)} ended in {challenge.classification} "
            f"({challenge.total_points} pts)."
        )
    result = "is still pending" if challenge.result is None else f"ended in {challenge.result}"
    return f"{_challenge_label(challenge.kind)} tested {_stat_label(challenge.stat_tested)} and {result}."


def _challenge_label(kind: str) -> str:
    labels = {
        "compatibility_quiz": "Compatibility Quiz",
        "final_couples": "Final Couples Challenge",
        "heart_rate": "Pulse Race",
        "lie_detector": "Lie Detector",
        "couples_quiz": "The Couples Quiz",
        "kiss_wed_pass": "Kiss Wed Pass",
    }
    return labels.get(kind, kind.replace("_", " ").title())


def _stat_label(stat: str) -> str:
    if stat == "combined":
        return "combined couple energy"
    return stat.replace("_", " ").title()


def _challenge_success_chance(state: GameState, challenge: Challenge) -> int:
    stats = state.player.stats
    if challenge.stat_tested == "combined":
        value = (stats.charm + stats.banter) // 2
    else:
        value = getattr(stats, challenge.stat_tested)
    return max(10, min(90, 35 + value * 7))


def _challenge_delta(kind: str, success: bool) -> RelationshipDelta:
    if kind == "compatibility_quiz":
        return RelationshipDelta(affection=5 if success else 0, trust=2 if success else -1)
    if kind == "heart_rate":
        return RelationshipDelta(chemistry=6 if success else 1)
    if kind == "couples_quiz":
        return RelationshipDelta(friendship=5 if success else -2)
    if kind == "lie_detector":
        return RelationshipDelta(trust=6 if success else -6)
    if kind == "kiss_wed_pass":
        return RelationshipDelta(chemistry=3 if success else 0, friendship=0 if success else -3)
    if kind == "final_couples":
        return RelationshipDelta(affection=8 if success else 2, trust=2 if success else 0)
    raise ValueError(f"unknown challenge kind: {kind}")


def _perception_delta(kind: str, success: bool) -> int:
    success_values = {
        "compatibility_quiz": 3,
        "heart_rate": 4,
        "couples_quiz": 5,
        "lie_detector": 4,
        "kiss_wed_pass": 2,
        "final_couples": 6,
    }
    failure_values = {
        "compatibility_quiz": -1,
        "heart_rate": -2,
        "couples_quiz": -3,
        "lie_detector": -3,
        "kiss_wed_pass": -1,
        "final_couples": -2,
    }
    return (success_values if success else failure_values)[kind]


def _challenge_target_id(state: GameState, choice: str | None) -> str:
    if choice:
        find_heartbreaker(state, choice)
        return choice
    couple = player_couple(state)
    if couple is not None:
        return couple.partner_b_id if couple.partner_a_id == "player" else couple.partner_a_id
    return "chloe"
