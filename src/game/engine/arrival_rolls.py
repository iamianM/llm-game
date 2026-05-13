"""Arrival interruption and pull-away rolls."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.game.engine.couples import couple_strength, partner_for
from src.game.state.models import GameState, IslanderState
from src.game.state.rng import SeededRng


class ArrivalRoll(BaseModel):
    """One roll pair made when an NPC arrives during a player conversation."""

    model_config = ConfigDict(extra="forbid")

    arriving_npc_id: str
    target_id: str
    interruption_chance: int = Field(ge=5, le=75)
    interruption_roll: int = Field(ge=1, le=100)
    interruption_hit: bool
    pull_chance: int = Field(ge=3, le=60)
    pull_roll: int = Field(ge=1, le=100)
    pull_hit: bool


def interruption_chance(state: GameState, arriving: IslanderState) -> int:
    """Chance that an arriving NPC interrupts to talk to the player."""
    target_id = state.active_conversation.target_id if state.active_conversation else ""
    chance = 12 + (arriving.relationship.chemistry * 2)
    chance += _recent_gossip_count(arriving) * 5
    chance += _jealousy_modifier(state, arriving.id, target_id)
    chance += _mood_modifier(arriving)
    if target_id and _public_perception(state, target_id) >= 70:
        chance -= 10
    return max(5, min(75, chance))


def pull_chance(state: GameState, arriving: IslanderState, target_id: str) -> int:
    """Chance that an arriving NPC pulls the player's target away."""
    target = _islander(state, target_id)
    chance = 8 + (max(arriving.relationship.chemistry, target.relationship.chemistry) * 2)
    chance += _recent_drama_count(arriving) * 4
    chance -= _target_couple_strength(state, target_id)
    chance += _jealousy_modifier(state, arriving.id, target_id, partner_only=True)
    return max(3, min(60, chance))


def roll_arrival(state: GameState, arriving: IslanderState, rng: SeededRng) -> ArrivalRoll:
    """Roll interruption and pull-away attempts for one arriving NPC."""
    if state.active_conversation is None:
        raise ValueError("arrival rolls require an active player conversation")
    target_id = state.active_conversation.target_id
    interrupt_chance = interruption_chance(state, arriving)
    interrupt_roll = rng.randint(1, 100)
    target_pull_chance = pull_chance(state, arriving, target_id)
    target_pull_roll = rng.randint(1, 100)
    return ArrivalRoll(
        arriving_npc_id=arriving.id,
        target_id=target_id,
        interruption_chance=interrupt_chance,
        interruption_roll=interrupt_roll,
        interruption_hit=interrupt_roll <= interrupt_chance,
        pull_chance=target_pull_chance,
        pull_roll=target_pull_roll,
        pull_hit=target_pull_roll <= target_pull_chance,
    )


def _recent_gossip_count(islander: IslanderState) -> int:
    return sum(1 for memory in islander.memories[-5:] if memory.emotional_weight >= 5)


def _recent_drama_count(islander: IslanderState) -> int:
    return sum(
        1
        for memory in islander.memories[-5:]
        if memory.emotional_weight >= 6 or any(tag in {"drama", "gossip", "witnessed"} for tag in memory.tags)
    )


def _jealousy_modifier(
    state: GameState,
    arriving_id: str,
    target_id: str,
    *,
    partner_only: bool = False,
) -> int:
    if not target_id:
        return 0
    for couple in state.couples:
        ids = {couple.partner_a_id, couple.partner_b_id}
        if arriving_id in ids and target_id in ids:
            return 10 if partner_only else 15
    return 0


def _mood_modifier(islander: IslanderState) -> int:
    if islander.mood.value in {"angry", "upset", "anxious"}:
        return 5
    if islander.mood.value == "happy":
        return -5
    return 0


def _target_couple_strength(state: GameState, target_id: str) -> int:
    for couple in state.couples:
        if target_id in {couple.partner_a_id, couple.partner_b_id}:
            if partner_for(couple, target_id) == state.player.id:
                return couple_strength(state, couple)
            return couple_strength(state, couple) // 2
    return 0


def _public_perception(state: GameState, actor_id: str) -> int:
    if actor_id == state.player.id:
        return state.player.public_perception
    return _islander(state, actor_id).public_perception


def _islander(state: GameState, islander_id: str) -> IslanderState:
    for islander in state.islanders:
        if islander.id == islander_id and not islander.eliminated:
            return islander
    raise ValueError(f"unknown active islander: {islander_id}")
