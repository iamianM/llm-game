"""Action menu helpers split out of the core action model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.game.engine.casa_amor import location_villa
from src.game.state.models import GameState, IslanderState, Phase

if TYPE_CHECKING:
    from src.game.engine.actions import ActionSpec


def pending_recouple_proposal_actions(state: GameState) -> list[ActionSpec]:
    from src.game.engine.actions import ActionKind, ActionSpec, PlayerAction

    if state.pending_recouple_proposal is None:
        return []
    proposer = find_islander(state, state.pending_recouple_proposal.proposer_id)
    return [
        ActionSpec(
            action=PlayerAction(kind=ActionKind.NPC_PROPOSAL_RESPONSE, target_id=proposer.id, intent_id="accept"),
            label=f"Accept {proposer.name}'s recoupling proposal",
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


def initial_coupling_targets(state: GameState) -> list[IslanderState]:
    targets = [
        islander
        for islander in state.islanders
        if not islander.eliminated
        and islander.gender != state.player.gender
        and location_villa(islander.location_id) is state.villa
    ]
    return sorted(targets, key=lambda islander: (islander.name, islander.id))


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
    for islander in state.islanders:
        if islander.eliminated or islander.id in state.intro_completed_ids or islander.id in partner_ids:
            continue
        for intent_id, label in labels.items():
            if intent_id == "intro_flirty" and islander.gender == state.player.gender:
                continue
            actions.append(
                ActionSpec(
                    action=PlayerAction(
                        kind=ActionKind.INTRODUCE_TO,
                        target_id=islander.id,
                        intent_id=intent_id,
                    ),
                    label=f"{islander.name}: {label}",
                )
            )
    return actions


def player_proposal_eligible(state: GameState, target_id: str) -> bool:
    target = find_islander(state, target_id)
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


def find_islander(state: GameState, target_id: str) -> IslanderState:
    for islander in state.islanders:
        if islander.id == target_id:
            return islander
    raise ValueError(f"unknown islander: {target_id}")
