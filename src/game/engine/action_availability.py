"""Action menu helpers split out of the core action model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.game.engine.flush_of_hearts import location_resort
from src.game.state.models import GameState, HeartbreakerState, Phase

if TYPE_CHECKING:
    from src.game.engine.actions import ActionSpec


def pending_pair_proposal_actions(state: GameState) -> list[ActionSpec]:
    from src.game.engine.actions import ActionKind, ActionSpec, PlayerAction

    if state.pending_pair_proposal is None:
        return []
    proposer = find_heartbreaker(state, state.pending_pair_proposal.proposer_id)
    return [
        ActionSpec(
            action=PlayerAction(kind=ActionKind.NPC_PROPOSAL_RESPONSE, target_id=proposer.id, intent_id="accept"),
            label=f"Accept {proposer.name}'s pairing proposal",
        ),
        ActionSpec(
            action=PlayerAction(
                kind=ActionKind.NPC_PROPOSAL_RESPONSE,
                target_id=proposer.id,
                intent_id="decline_politely",
            ),
            label=f"Decline {proposer.name} politely",
        ),
        ActionSpec(
            action=PlayerAction(
                kind=ActionKind.NPC_PROPOSAL_RESPONSE,
                target_id=proposer.id,
                intent_id="decline_harshly",
            ),
            label=f"Decline {proposer.name} harshly",
        ),
    ]


def needs_initial_coupling(state: GameState) -> bool:
    return (
        state.day == 1
        and state.phase is Phase.MORNING
        and not state.couples
        and state.character_creation is not None
    )


def initial_coupling_targets(state: GameState) -> list[HeartbreakerState]:
    targets = [
        heartbreaker
        for heartbreaker in state.heartbreakers
        if not heartbreaker.eliminated
        and heartbreaker.gender != state.player.gender
        and location_resort(heartbreaker.location_id) is state.resort
    ]
    return sorted(targets, key=lambda heartbreaker: (heartbreaker.name, heartbreaker.id))


def intro_actions(state: GameState) -> list[ActionSpec]:
    from src.game.engine.actions import ActionKind, ActionSpec, PlayerAction

    labels = {
        "intro_friendly": "Friendly introduction",
        "intro_flirty": "Flirty introduction",
        "intro_deep": "Deep introduction",
        "intro_banter": "Banter introduction",
    }
    actions: list[ActionSpec] = []
    partner_ids = {
        other_id
        for couple in state.couples
        for other_id in (couple.partner_a_id, couple.partner_b_id)
        if state.player.id in {couple.partner_a_id, couple.partner_b_id} and other_id != state.player.id
    }
    for heartbreaker in state.heartbreakers:
        if heartbreaker.eliminated or heartbreaker.id in state.intro_completed_ids or heartbreaker.id in partner_ids:
            continue
        for intent_id, label in labels.items():
            if intent_id == "intro_flirty" and heartbreaker.gender == state.player.gender:
                continue
            actions.append(
                ActionSpec(
                    action=PlayerAction(
                        kind=ActionKind.INTRODUCE_TO,
                        target_id=heartbreaker.id,
                        intent_id=intent_id,
                    ),
                    label=f"{heartbreaker.name}: {label}",
                )
            )
    return actions


def player_proposal_eligible(state: GameState, target_id: str) -> bool:
    target = find_heartbreaker(state, target_id)
    if target.eliminated or target.gender == state.player.gender:
        return False
    for couple in state.couples:
        if state.player.id in {couple.partner_a_id, couple.partner_b_id} and target.id in {
            couple.partner_a_id,
            couple.partner_b_id,
        }:
            return False
    rel = target.relationship
    return rel.chemistry >= 60 and rel.affection >= 50


def find_heartbreaker(state: GameState, target_id: str) -> HeartbreakerState:
    for heartbreaker in state.heartbreakers:
        if heartbreaker.id == target_id:
            return heartbreaker
    raise ValueError(f"unknown heartbreaker: {target_id}")
