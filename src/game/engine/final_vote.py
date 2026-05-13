"""Final public vote resolution."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from src.game.engine.audience import couple_audience_score
from src.game.state.models import Couple, GameState, RunOutcome


class FinalVoteResult(BaseModel):
    """Resolved final vote outcome."""

    model_config = ConfigDict(extra="forbid")

    winner: Couple | None
    runner_up: Couple | None
    player_rank: int | None
    outcome: RunOutcome


def final_vote(state: GameState) -> FinalVoteResult:
    """Resolve the final public vote and assign ``state.outcome``."""
    if state.outcome is RunOutcome.ELIMINATED:
        return FinalVoteResult(winner=None, runner_up=None, player_rank=None, outcome=RunOutcome.ELIMINATED)
    if state.player.eliminated:
        state.outcome = RunOutcome.ELIMINATED
        return FinalVoteResult(winner=None, runner_up=None, player_rank=None, outcome=RunOutcome.ELIMINATED)
    ranked = sorted(state.couples, key=lambda couple: (-couple_audience_score(state, couple), _couple_key(couple)))
    player_rank: int | None = None
    for index, couple in enumerate(ranked, start=1):
        if state.player.id in {couple.partner_a_id, couple.partner_b_id}:
            player_rank = index
            break
    if player_rank == 1:
        state.outcome = RunOutcome.WON_AS_COUPLE
    elif player_rank == 2:
        state.outcome = RunOutcome.RUNNER_UP_COUPLE
    elif player_rank is None:
        state.outcome = RunOutcome.LEFT_SINGLE
    else:
        state.outcome = RunOutcome.RUNNER_UP_COUPLE
    return FinalVoteResult(
        winner=ranked[0] if ranked else None,
        runner_up=ranked[1] if len(ranked) > 1 else None,
        player_rank=player_rank,
        outcome=state.outcome,
    )


def final_vote_message(result: FinalVoteResult) -> str:
    """Return a concise ceremony message."""
    if result.outcome is RunOutcome.WON_AS_COUPLE:
        partner = _player_partner(result.winner)
        return f"Final vote: the player and {partner} win as the top couple."
    if result.outcome is RunOutcome.RUNNER_UP_COUPLE:
        return "Final vote: the player finishes as a runner-up couple."
    if result.outcome is RunOutcome.LEFT_SINGLE:
        return "Final vote: the player reaches the finale single."
    return "Final vote: the player was already dumped from the island."


def _couple_key(couple: Couple) -> str:
    return "|".join(sorted([couple.partner_a_id, couple.partner_b_id]))


def _player_partner(couple: Couple | None) -> str:
    if couple is None:
        return "their partner"
    if couple.partner_a_id == "player":
        return couple.partner_b_id
    if couple.partner_b_id == "player":
        return couple.partner_a_id
    return "their partner"
