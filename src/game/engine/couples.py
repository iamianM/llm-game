"""Couple strength and Heart Throb steal mechanics."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from src.game.state.models import Couple, GameState, HeartbreakerState, clamp_relationship
from src.game.state.rng import SeededRng


class StealAttempt(BaseModel):
    """One Heart Throb attempt to steal a coupled contestant."""

    model_config = ConfigDict(extra="forbid")

    heart_throb_id: str
    target_id: str
    abandoned_id: str
    chance: int
    roll: int
    success: bool


def player_couple(state: GameState) -> Couple | None:
    """Return the player's active couple, if any."""
    for couple in state.couples:
        if state.player.id in {couple.partner_a_id, couple.partner_b_id}:
            return couple
    return None


def partner_for(couple: Couple, actor_id: str) -> str:
    """Return the other member of ``couple``."""
    if couple.partner_a_id == actor_id:
        return couple.partner_b_id
    if couple.partner_b_id == actor_id:
        return couple.partner_a_id
    raise ValueError(f"{actor_id} is not in couple {couple.model_dump()}")


def couple_strength(state: GameState, couple: Couple) -> int:
    """Compute derived couple strength on a 0-100 scale."""
    first = _relationship_score(state, couple.partner_a_id, couple.partner_b_id)
    second = _relationship_score(state, couple.partner_b_id, couple.partner_a_id)
    return clamp_relationship((first + second) // 4)


def ranked_couples(state: GameState) -> list[tuple[Couple, int]]:
    """Rank active couples by strength, then public perception."""
    rows = [(couple, couple_strength(state, couple)) for couple in state.couples]
    rows.sort(key=lambda row: (-row[1], -_couple_public_perception(state, row[0]), _couple_key(row[0])))
    return rows


def steal_chance(state: GameState, heart_throb: HeartbreakerState, target_id: str, couple: Couple) -> int:
    """Chance that a Heart Throb steals ``target_id`` from ``couple``."""
    chemistry = heart_throb.relationship.chemistry
    modifier = 10 if heart_throb.archetype in {"heart_throb", "joker"} else 0
    chance = 50 + (chemistry * 3) - couple_strength(state, couple) + modifier
    return max(10, min(90, chance))


def resolve_steal_attempt(
    state: GameState,
    heart_throb_id: str,
    target_couple: Couple,
    rng: SeededRng,
) -> StealAttempt:
    """Resolve a Heart Throb steal roll and mutate couples on success."""
    heart_throb = _heartbreaker(state, heart_throb_id)
    target_id = _steal_target(state, heart_throb, target_couple)
    abandoned_id = partner_for(target_couple, target_id)
    chance = steal_chance(state, heart_throb, target_id, target_couple)
    roll = rng.randint(1, 100)
    success = roll <= chance
    target_couple.last_steal_attempt_chance = chance
    if success:
        _replace_couple(state, target_couple, Couple(
            partner_a_id=heart_throb.id,
            partner_b_id=target_id,
            formed_on_day=state.day,
            formed_via="ceremony",
        ))
    return StealAttempt(
        heart_throb_id=heart_throb.id,
        target_id=target_id,
        abandoned_id=abandoned_id,
        chance=chance,
        roll=roll,
        success=success,
    )


def _relationship_score(state: GameState, actor_id: str, other_id: str) -> int:
    if actor_id == state.player.id:
        rel = _heartbreaker(state, other_id).relationship
        return rel.affection + rel.trust
    if other_id == state.player.id:
        rel = _heartbreaker(state, actor_id).relationship
        return rel.affection + rel.trust
    rel = _heartbreaker(state, actor_id).relationship
    return rel.affection + rel.trust


def _steal_target(state: GameState, heart_throb: HeartbreakerState, couple: Couple) -> str:
    candidates = [couple.partner_a_id, couple.partner_b_id]
    candidates.sort(key=lambda actor_id: (_target_draw(state, heart_throb, actor_id), actor_id), reverse=True)
    return candidates[0]


def _target_draw(state: GameState, heart_throb: HeartbreakerState, actor_id: str) -> int:
    if actor_id == state.player.id:
        return heart_throb.relationship.chemistry
    return _heartbreaker(state, actor_id).relationship.chemistry


def _replace_couple(state: GameState, old: Couple, new: Couple) -> None:
    state.couples = [new if couple is old else couple for couple in state.couples]


def _couple_public_perception(state: GameState, couple: Couple) -> int:
    return sum(_public_perception(state, actor_id) for actor_id in (couple.partner_a_id, couple.partner_b_id))


def _public_perception(state: GameState, actor_id: str) -> int:
    if actor_id == state.player.id:
        return state.player.public_perception
    return _heartbreaker(state, actor_id).public_perception


def _couple_key(couple: Couple) -> str:
    return "|".join(sorted([couple.partner_a_id, couple.partner_b_id]))


def _heartbreaker(state: GameState, heartbreaker_id: str) -> HeartbreakerState:
    for heartbreaker in state.heartbreakers:
        if heartbreaker.id == heartbreaker_id and not heartbreaker.eliminated:
            return heartbreaker
    raise ValueError(f"unknown active heartbreaker: {heartbreaker_id}")
