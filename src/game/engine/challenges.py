"""Deterministic daily challenge resolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

from src.game.engine.audience import player_couple
from src.game.engine.state_access import apply_relationship_delta, find_islander
from src.game.state.models import Challenge, GameState, RelationshipDelta
from src.game.state.rng import SeededRng

ChallengeStat = Literal["charm", "banter", "eq", "graft", "loyalty", "combined"]


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
    3: ChallengeDef("mr_and_mrs", 3, "mr_and_mrs", "banter"),
    4: ChallengeDef("lie_detector", 4, "lie_detector", "loyalty"),
    5: ChallengeDef("snog_marry_pie", 5, "snog_marry_pie", "banter"),
    6: ChallengeDef("final_couples", 6, "final_couples", "combined"),
}

CHOICE_REQUIRED_CHALLENGES = {"snog_marry_pie"}


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
    """Resolve and apply one scheduled challenge."""
    if challenge.result is not None:
        return challenge
    if challenge.kind in CHOICE_REQUIRED_CHALLENGES and not choice:
        return challenge
    target_id = _challenge_target_id(state, choice)
    chance = _challenge_success_chance(state, challenge)
    success = rng.randint(1, 100) <= chance
    delta = _challenge_delta(challenge.kind, success)
    target = find_islander(state, target_id)
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
    result = "is still pending" if challenge.result is None else f"ended in {challenge.result}"
    return f"{_challenge_label(challenge.kind)} tested {_stat_label(challenge.stat_tested)} and {result}."


def _challenge_label(kind: str) -> str:
    labels = {
        "compatibility_quiz": "Compatibility Quiz",
        "final_couples": "Final Couples Challenge",
        "heart_rate": "Pulse Race",
        "lie_detector": "Lie Detector",
        "mr_and_mrs": "The Couples Quiz",
        "snog_marry_pie": "Kiss Wed Pass",
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
    if kind == "mr_and_mrs":
        return RelationshipDelta(friendship=5 if success else -2)
    if kind == "lie_detector":
        return RelationshipDelta(trust=6 if success else -6)
    if kind == "snog_marry_pie":
        return RelationshipDelta(chemistry=3 if success else 0, friendship=0 if success else -3)
    if kind == "final_couples":
        return RelationshipDelta(affection=8 if success else 2, trust=2 if success else 0)
    raise ValueError(f"unknown challenge kind: {kind}")


def _perception_delta(kind: str, success: bool) -> int:
    success_values = {
        "compatibility_quiz": 3,
        "heart_rate": 4,
        "mr_and_mrs": 5,
        "lie_detector": 4,
        "snog_marry_pie": 2,
        "final_couples": 6,
    }
    failure_values = {
        "compatibility_quiz": -1,
        "heart_rate": -2,
        "mr_and_mrs": -3,
        "lie_detector": -3,
        "snog_marry_pie": -1,
        "final_couples": -2,
    }
    return (success_values if success else failure_values)[kind]


def _challenge_target_id(state: GameState, choice: str | None) -> str:
    if choice:
        find_islander(state, choice)
        return choice
    couple = player_couple(state)
    if couple is not None:
        return couple.partner_b_id if couple.partner_a_id == "player" else couple.partner_a_id
    return "chloe"
