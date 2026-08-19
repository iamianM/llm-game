"""Turn pipeline helpers for pairing proposal side effects."""

from __future__ import annotations

from src.game.agents.conversation_curator import ConversationCuratorFn
from src.game.engine.ceremonies import CeremonyEvent
from src.game.engine.conversation import close_conversation
from src.game.engine.memory import add_memory_batch, propagate_gossip_seeds
from src.game.engine.proposals import ProposalOutcome, proposal_memory_batch
from src.game.engine.results import MechanicalResult
from src.game.engine.state_access import display_name
from src.game.engine.turn_curator import curate_player_conversation
from src.game.state.models import GameState, MemoryBatch


def proposal_event(state: GameState, result: MechanicalResult) -> CeremonyEvent | None:
    """Return the visible event for a proposal result."""
    if result.proposal_outcome is None:
        return None
    proposal = ProposalOutcome.model_validate(result.proposal_outcome)
    sub_kind = "accepted" if proposal.accepted else "rejected"
    kind = "npc_proposal_response" if "npc_proposal_response" in result.tags else "pair_proposal"
    heartbreaker_id = proposal.proposer_id if proposal.proposer_id != "player" else proposal.target_id
    return CeremonyEvent(
        kind=kind,
        sub_kind=sub_kind,
        message=(
            f"Pairing proposal {sub_kind}: {display_name(state, proposal.proposer_id)} "
            f"asked {display_name(state, proposal.target_id)}."
        ),
        heartbreaker_id=heartbreaker_id,
    )


def close_proposal_conversation(
    state: GameState,
    result: MechanicalResult,
    curator: ConversationCuratorFn | None,
) -> list[MemoryBatch]:
    """Curate the proposal moment and close the active conversation if present."""
    if result.proposal_outcome is None:
        return []
    proposal = ProposalOutcome.model_validate(result.proposal_outcome)
    batches: list[MemoryBatch] = []
    if state.active_conversation is not None:
        batches.append(curate_player_conversation(state, state.active_conversation, curator))
    batch = proposal_memory_batch(state, proposal)
    add_memory_batch(state, batch, day=state.day, turn=state.turn_index)
    propagate_gossip_seeds(state, batch.gossip_seeds, day=state.day, turn=state.turn_index)
    batches.append(batch)
    if state.active_conversation is not None:
        close_conversation(state, "proposal")
    return batches
