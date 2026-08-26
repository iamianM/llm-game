"""Deterministic memory records for pairing proposals."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.game.state.memory import GossipSeed, MemoryBatch, MemoryDraft
from src.game.state.models import GameState, HeartbreakerState

if TYPE_CHECKING:
    from src.game.engine.proposals import ProposalOutcome


def proposal_memory_batch(state: GameState, outcome: ProposalOutcome) -> MemoryBatch:
    """Record a proposal from each participant's point of view."""
    npc_id = outcome.proposer_id if outcome.target_id == state.player.id else outcome.target_id
    npc = _heartbreaker(state, npc_id)
    status = "accepted" if outcome.accepted else "rejected"
    if outcome.proposer_id == "player":
        player_memory = f"I asked {npc.name} to pair with me, and {npc.name} {status}."
        npc_memory = f"The player asked me to pair, and I {status}."
        summary = f"The player asked {npc.name} to pair, and {npc.name} {status}."
        witness_memory = f"I saw the player ask {npc.name} to pair, and {npc.name} {status}."
    else:
        player_verb = "accepted" if outcome.accepted else "declined"
        player_memory = f"{npc.name} asked me to pair, and I {player_verb}."
        npc_memory = f"I asked the player to pair, and the player {player_verb}."
        summary = f"{npc.name} asked the player to pair, and the player {player_verb}."
        witness_memory = f"I saw {npc.name} ask the player to pair, and the player {player_verb}."
    drafts = [
        MemoryDraft(
            holder_id="player",
            subject_id=npc.id,
            content=player_memory,
            source="direct",
            emotional_weight=8 if outcome.accepted else 7,
            tags=["pair_proposal", status],
        ),
        MemoryDraft(
            holder_id=npc.id,
            subject_id="player",
            content=npc_memory,
            source="direct",
            emotional_weight=8 if outcome.accepted else 7,
            tags=["pair_proposal", status],
        ),
    ]
    for former_partner_id in [outcome.old_player_partner_id, outcome.old_target_partner_id]:
        if former_partner_id is None or former_partner_id in {outcome.target_id, "player"}:
            continue
        former_partner = _heartbreaker(state, former_partner_id)
        if former_partner.location_id != state.location_id:
            continue
        drafts.append(
            MemoryDraft(
                holder_id=former_partner_id,
                subject_id="player",
                content=witness_memory,
                source="witnessed",
                emotional_weight=8,
                tags=["pair_proposal", "former_partner"],
            )
        )
    return MemoryBatch(
        kind="player",
        memories=drafts,
        summary=summary,
        gossip_seeds=[
            GossipSeed(
                subject_id="player",
                holder_id=npc.id,
                gist=summary,
                emotional_weight=8,
                tags=["pair_proposal", status],
            )
        ],
    )


def _heartbreaker(state: GameState, heartbreaker_id: str) -> HeartbreakerState:
    for heartbreaker in state.heartbreakers:
        if heartbreaker.id == heartbreaker_id and not heartbreaker.eliminated:
            return heartbreaker
    raise ValueError(f"unknown active heartbreaker: {heartbreaker_id}")
