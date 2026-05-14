"""State-conditioned Heart Throb brief selection."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from src.game.engine.couples import couple_strength, player_couple
from src.game.state.models import GameState


class ThreatMode(StrEnum):
    TEMPT_PLAYER = "tempt_player"
    STEAL_PARTNER = "steal_partner"
    BREAK_RIVAL = "break_rival"
    SHAKE_ALLIANCE = "shake_alliance"
    EXPOSE_HISTORY = "expose_history"
    INJECT_CHAOS = "inject_chaos"


class HeartThrobBrief(BaseModel):
    """Internal producer brief for generating a Heart Throb."""

    model_config = ConfigDict(extra="forbid")

    target_npc_id: str
    threat_mode: ThreatMode
    archetype: str
    persona_hook: str


def pick_heart_throb_brief(state: GameState) -> HeartThrobBrief:
    """Pick a deterministic disruption brief from current state."""
    couple = player_couple(state)
    if couple is None:
        return HeartThrobBrief(
            target_npc_id="player",
            threat_mode=ThreatMode.TEMPT_PLAYER,
            archetype="sweetheart",
            persona_hook="arrives as a clean second-chance match for the player",
        )
    strength = couple_strength(state, couple)
    partner_id = couple.partner_b_id if couple.partner_a_id == "player" else couple.partner_a_id
    if strength >= 70:
        return HeartThrobBrief(
            target_npc_id=partner_id,
            threat_mode=ThreatMode.STEAL_PARTNER,
            archetype="sweetheart",
            persona_hook="threatens to be what the player's partner was waiting for",
        )
    stable_npc = _strongest_npc_couple_target(state)
    if stable_npc is not None:
        return HeartThrobBrief(
            target_npc_id=stable_npc,
            threat_mode=ThreatMode.BREAK_RIVAL,
            archetype="alpha",
            persona_hook="targets the strongest non-player couple",
        )
    return HeartThrobBrief(
        target_npc_id=partner_id,
        threat_mode=ThreatMode.INJECT_CHAOS,
        archetype="joker",
        persona_hook="enters loud and flirts indiscriminately",
    )


def _strongest_npc_couple_target(state: GameState) -> str | None:
    best_id: str | None = None
    best_strength = -1
    for couple in state.couples:
        if "player" in {couple.partner_a_id, couple.partner_b_id}:
            continue
        strength = couple_strength(state, couple)
        if strength > best_strength:
            best_strength = strength
            best_id = couple.partner_a_id
    return best_id
