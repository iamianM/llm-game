"""Pairing proposal mechanics."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict

from src.game.engine.couples import couple_strength, partner_for
from src.game.engine.knowledge import reveal_partner_surface_facts
from src.game.engine.results import MechanicalResult
from src.game.state.memory import GossipSeed, MemoryBatch, MemoryDraft
from src.game.state.models import (
    Couple,
    GameState,
    HeartbreakerState,
    Mood,
    NPCNPCConversation,
    PendingPairProposal,
    RelationshipDelta,
    RelationshipState,
    clamp_relationship,
)
from src.game.state.rng import SeededRng

if TYPE_CHECKING:
    from src.game.engine.actions import PlayerAction

PROPOSAL_CHEMISTRY_THRESHOLD = 60
PROPOSAL_AFFECTION_THRESHOLD = 50


class ProposalOutcome(BaseModel):
    """Structured result of one pairing proposal."""

    model_config = ConfigDict(extra="forbid")

    proposer_id: str
    target_id: str
    accepted: bool
    chance: int
    roll: int
    old_player_partner_id: str | None = None
    old_target_partner_id: str | None = None


def player_proposal_eligible(state: GameState, target_id: str) -> bool:
    """Return whether the player can ask ``target_id`` to pair."""
    target = _heartbreaker(state, target_id)
    if target.eliminated or target.gender == state.player.gender or _partner_id(state, state.player.id) == target.id:
        return False
    rel = target.relationship
    return rel.chemistry >= PROPOSAL_CHEMISTRY_THRESHOLD and rel.affection >= PROPOSAL_AFFECTION_THRESHOLD


def apply_player_proposal(state: GameState, target_id: str, rng: SeededRng) -> tuple[MechanicalResult, ProposalOutcome]:
    """Resolve a player-initiated pairing proposal and mutate state."""
    if not player_proposal_eligible(state, target_id):
        raise ValueError(f"pairing proposal is not available: {target_id}")
    target = _heartbreaker(state, target_id)
    chance = proposal_accept_chance(state, proposer_id=state.player.id, target_id=target.id)
    roll = rng.randint(1, 100)
    accepted = roll <= chance
    old_player_partner_id = _partner_id(state, state.player.id)
    old_target_partner_id = _partner_id(state, target.id)
    outcome = ProposalOutcome(
        proposer_id=state.player.id,
        target_id=target.id,
        accepted=accepted,
        chance=chance,
        roll=roll,
        old_player_partner_id=old_player_partner_id,
        old_target_partner_id=old_target_partner_id,
    )
    before_public = state.player.public_perception
    if accepted:
        _apply_successful_player_steal(state, target, old_player_partner_id, old_target_partner_id)
        delta = RelationshipDelta(affection=3, chemistry=2, trust=1)
        target.relationship = _add_delta(target.relationship, delta)
        public_delta = _successful_player_audience_delta(state)
        reason = "they saw it as bold" if public_delta >= 0 else "they thought it looked snakey"
        tags = ["pair_proposal", "accepted", "steal"]
    else:
        delta = RelationshipDelta(affection=-5, chemistry=-5, trust=-2)
        target.relationship = _add_delta(target.relationship, delta)
        if old_player_partner_id is not None:
            old_partner = _heartbreaker(state, old_player_partner_id)
            old_partner.relationship = _add_delta(old_partner.relationship, RelationshipDelta(trust=-4))
        public_delta = -4
        reason = "they thought the spark looked desperate"
        tags = ["pair_proposal", "rejected", "failed_steal"]
    state.player.public_perception = clamp_relationship(state.player.public_perception + public_delta)
    result = MechanicalResult(
        action=_proposal_action(target.id),
        success=accepted,
        roll=roll,
        success_chance=chance,
        relationship_deltas={target.id: delta},
        tags=tags,
        audience_delta=state.player.public_perception - before_public,
        audience_reason=reason,
        proposal_outcome=outcome.model_dump(mode="json"),
    )
    return result, outcome


def maybe_trigger_npc_player_proposal(state: GameState, rng: SeededRng) -> ProposalOutcome | None:
    """Create a pending NPC proposal when a drifting NPC is ready to spark."""
    if state.pending_pair_proposal is not None or state.active_conversation is not None:
        return None
    candidates = [
        heartbreaker
        for heartbreaker in state.heartbreakers
        if not heartbreaker.eliminated
        and heartbreaker.gender != state.player.gender
        and _partner_id(state, state.player.id) != heartbreaker.id
        and heartbreaker.relationship.chemistry >= PROPOSAL_CHEMISTRY_THRESHOLD
        and heartbreaker.relationship.affection >= PROPOSAL_AFFECTION_THRESHOLD
        and _current_strength(state, heartbreaker.id) <= 50
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda npc: (npc.relationship.chemistry + npc.relationship.affection, npc.id), reverse=True)
    proposer = candidates[0]
    chance = proposal_accept_chance(state, proposer_id=proposer.id, target_id=proposer.id)
    if rng.randint(1, 100) > max(20, min(80, chance)):
        return None
    state.pending_pair_proposal = PendingPairProposal(
        proposer_id=proposer.id,
        chance=chance,
        audience_hint_accept=_audience_hint_for_accept(state),
    )
    return ProposalOutcome(
        proposer_id=proposer.id,
        target_id=state.player.id,
        accepted=False,
        chance=chance,
        roll=0,
        old_player_partner_id=_partner_id(state, state.player.id),
        old_target_partner_id=_partner_id(state, proposer.id),
    )


def apply_npc_proposal_response(state: GameState, intent_id: str) -> tuple[MechanicalResult, ProposalOutcome]:
    """Resolve the player's response to a pending NPC proposal."""
    pending = state.pending_pair_proposal
    if pending is None:
        raise ValueError("no NPC proposal is waiting")
    proposer = _heartbreaker(state, pending.proposer_id)
    accepted = intent_id == "accept"
    old_player_partner_id = _partner_id(state, state.player.id)
    old_target_partner_id = _partner_id(state, proposer.id)
    outcome = ProposalOutcome(
        proposer_id=proposer.id,
        target_id=state.player.id,
        accepted=accepted,
        chance=pending.chance,
        roll=0,
        old_player_partner_id=old_player_partner_id,
        old_target_partner_id=old_target_partner_id,
    )
    before_public = state.player.public_perception
    if accepted:
        _form_proposal_couple(state, state.player.id, proposer.id, rebound=False)
        delta = RelationshipDelta(affection=3, chemistry=3, trust=1)
        proposer.relationship = _add_delta(proposer.relationship, delta)
        audience_delta = -3 if state.player.stats.loyalty <= 5 else 0
        tags = ["npc_proposal_response", "accepted", "steal"]
        reason = "they thought accepting was bold" if audience_delta >= 0 else "they thought accepting looked snakey"
    else:
        delta = RelationshipDelta(affection=-2, chemistry=-3)
        if intent_id == "decline_harshly":
            delta = RelationshipDelta(affection=-5, chemistry=-5, trust=-2)
        proposer.relationship = _add_delta(proposer.relationship, delta)
        audience_delta = 1 if intent_id == "decline_politely" else -1
        tags = ["npc_proposal_response", intent_id]
        reason = "they respected the clear answer" if audience_delta > 0 else "they thought the rejection was harsh"
    state.pending_pair_proposal = None
    state.player.public_perception = clamp_relationship(state.player.public_perception + audience_delta)
    from src.game.engine.actions import ActionKind, PlayerAction

    result = MechanicalResult(
        action=PlayerAction(kind=ActionKind.NPC_PROPOSAL_RESPONSE, target_id=proposer.id, intent_id=intent_id),
        success=accepted,
        success_chance=pending.chance,
        relationship_deltas={proposer.id: delta},
        tags=tags,
        audience_delta=state.player.public_perception - before_public,
        audience_reason=reason,
        proposal_outcome=outcome.model_dump(mode="json"),
    )
    return result, outcome


def maybe_form_single_npc_couple_from_conversation(
    state: GameState,
    conversation: NPCNPCConversation,
) -> MemoryBatch | None:
    """Let two single NPCs organically couple after a flirty background conversation."""
    first_id, second_id = conversation.participants
    first = _heartbreaker(state, first_id)
    second = _heartbreaker(state, second_id)
    if first.gender == second.gender or _partner_id(state, first.id) is not None or _partner_id(state, second.id) is not None:
        return None
    if len(conversation.exchanges) < 2 or not any("flirt" in exchange.tone.lower() for exchange in conversation.exchanges):
        return None
    _form_proposal_couple(state, first.id, second.id, rebound=True)
    gist = f"{first.name} and {second.name} quietly decided to couple up after their chats."
    return MemoryBatch(
        kind="background",
        memories=[
            MemoryDraft(
                holder_id=first.id,
                subject_id=second.id,
                content=gist,
                source="direct",
                emotional_weight=7,
                tags=["npc_proposal", "single_drift"],
            ),
            MemoryDraft(
                holder_id=second.id,
                subject_id=first.id,
                content=gist,
                source="direct",
                emotional_weight=7,
                tags=["npc_proposal", "single_drift"],
            ),
        ],
        summary=gist,
        gossip_seeds=[
            GossipSeed(
                subject_id=first.id,
                holder_id=second.id,
                gist=gist,
                emotional_weight=7,
                tags=["npc_proposal", "single_drift"],
            )
        ],
    )

def proposal_accept_chance(state: GameState, *, proposer_id: str, target_id: str) -> int:
    """Return deterministic acceptance chance for ``target_id``."""
    target = _heartbreaker(state, target_id)
    rel = target.relationship
    current = _couple_for_actor(state, target_id)
    current_strength = 0 if current is None else couple_strength(state, current)
    raw = int((rel.chemistry * 0.4) + (rel.affection * 0.3) - (current_strength * 0.3))
    if proposer_id != state.player.id:
        raw += _npc_persona_bias(target)
    return max(5, min(95, raw))


def proposal_memory_batch(state: GameState, outcome: ProposalOutcome) -> MemoryBatch:
    """Create deterministic memories and gossip seeds for a proposal."""
    npc_id = outcome.proposer_id if outcome.target_id == state.player.id else outcome.target_id
    npc = _heartbreaker(state, npc_id)
    actor = npc.name if outcome.target_id == state.player.id else "Player"
    target_name = "player" if outcome.target_id == state.player.id else npc.name
    status = "accepted" if outcome.accepted else "rejected"
    gist = f"{actor} proposed to pair with {target_name}, and {target_name} {status}."
    drafts = [
        MemoryDraft(
            holder_id="player",
            subject_id=npc.id,
            content=gist,
            source="direct",
            emotional_weight=8 if outcome.accepted else 7,
            tags=["pair_proposal", status],
        ),
        MemoryDraft(
            holder_id=npc.id,
            subject_id="player",
            content=gist,
            source="direct",
            emotional_weight=8 if outcome.accepted else 7,
            tags=["pair_proposal", status],
        ),
    ]
    for former_partner_id in [outcome.old_player_partner_id, outcome.old_target_partner_id]:
        if former_partner_id is not None and former_partner_id not in {outcome.target_id, "player"}:
            drafts.append(
                MemoryDraft(
                    holder_id=former_partner_id,
                    subject_id="player",
                    content=gist,
                    source="witnessed",
                    emotional_weight=8,
                    tags=["pair_proposal", "former_partner"],
                )
            )
    return MemoryBatch(
        kind="player",
        memories=drafts,
        summary=gist,
        gossip_seeds=[
            GossipSeed(
                subject_id="player",
                holder_id=npc.id,
                gist=gist,
                emotional_weight=8,
                tags=["pair_proposal", status],
            )
        ],
    )


def _apply_successful_player_steal(
    state: GameState,
    target: HeartbreakerState,
    old_player_partner_id: str | None,
    old_target_partner_id: str | None,
) -> None:
    _form_proposal_couple(state, state.player.id, target.id, rebound=False)
    for former_partner_id in [old_player_partner_id, old_target_partner_id]:
        if former_partner_id is not None and former_partner_id != target.id:
            former_partner = _heartbreaker(state, former_partner_id)
            former_partner.mood = Mood.UPSET
            former_partner.public_perception = clamp_relationship(former_partner.public_perception + 2)
    target.public_perception = clamp_relationship(target.public_perception - 3)


def _form_proposal_couple(state: GameState, first_id: str, second_id: str, *, rebound: bool) -> None:
    state.couples = [
        couple
        for couple in state.couples
        if first_id not in {couple.partner_a_id, couple.partner_b_id}
        and second_id not in {couple.partner_a_id, couple.partner_b_id}
    ]
    state.couples.append(
        Couple(
            partner_a_id=first_id,
            partner_b_id=second_id,
            formed_on_day=state.day,
            formed_via="proposal",
            rebound=rebound,
        )
    )
    if state.player.id == first_id:
        reveal_partner_surface_facts(state, second_id)
    elif state.player.id == second_id:
        reveal_partner_surface_facts(state, first_id)


def _successful_player_audience_delta(state: GameState) -> int:
    if state.player.stats.loyalty <= 4:
        return -2
    if state.player.public_perception >= 60:
        return 2
    return 0


def _audience_hint_for_accept(state: GameState) -> Literal["+", "-", ""]:
    if state.player.stats.loyalty <= 5:
        return "-"
    if state.player.public_perception >= 60:
        return "+"
    return ""


def _current_strength(state: GameState, actor_id: str) -> int:
    couple = _couple_for_actor(state, actor_id)
    return 0 if couple is None else couple_strength(state, couple)


def _partner_id(state: GameState, actor_id: str) -> str | None:
    couple = _couple_for_actor(state, actor_id)
    if couple is None:
        return None
    return partner_for(couple, actor_id)


def _couple_for_actor(state: GameState, actor_id: str) -> Couple | None:
    for couple in state.couples:
        if actor_id in {couple.partner_a_id, couple.partner_b_id}:
            return couple
    return None


def _heartbreaker(state: GameState, heartbreaker_id: str) -> HeartbreakerState:
    for heartbreaker in state.heartbreakers:
        if heartbreaker.id == heartbreaker_id and not heartbreaker.eliminated:
            return heartbreaker
    raise ValueError(f"unknown active heartbreaker: {heartbreaker_id}")


def _add_delta(rel: RelationshipState, delta: RelationshipDelta) -> RelationshipState:
    rel.affection = clamp_relationship(rel.affection + delta.affection)
    rel.chemistry = clamp_relationship(rel.chemistry + delta.chemistry)
    rel.trust = clamp_relationship(rel.trust + delta.trust)
    rel.friendship = clamp_relationship(rel.friendship + delta.friendship)
    return rel


def _npc_persona_bias(target: HeartbreakerState) -> int:
    if target.archetype in {"heart_throb", "joker"}:
        return 10
    if target.archetype in {"sweetheart"}:
        return -15
    return 0


def _proposal_action(target_id: str) -> PlayerAction:
    from src.game.engine.actions import ActionKind, PlayerAction

    return PlayerAction(kind=ActionKind.PROPOSE_PAIR, target_id=target_id)
