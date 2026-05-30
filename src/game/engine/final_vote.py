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


def final_vote_message(result: FinalVoteResult, state: GameState) -> str:
    """Return a concise, player-facing ceremony message.

    This string is surfaced verbatim in mock/static mode (the event narrator
    only runs in real-LLM mode), so it must already read in display terms — the
    player's name and the partner's display name, never the raw "the player"
    label or a lowercase islander id.

    The nameless player carries the placeholder name "You", so the verb has to
    agree in the second person ("You finish", not "You finishes"). A player who
    set a real name via the character creator is a third-person subject ("Alex
    finishes"). The plural WON clause ("X and Y win") reads correctly either way.
    """
    player = state.player.name
    second_person = player.strip().lower() == "you"
    if result.outcome is RunOutcome.WON_AS_COUPLE:
        partner = _player_partner(result.winner, state)
        return f"Final vote: {player} and {partner} win as the top couple."
    if result.outcome is RunOutcome.RUNNER_UP_COUPLE:
        verb = "finish" if second_person else "finishes"
        return f"Final vote: {player} {verb} as a runner-up couple."
    if result.outcome is RunOutcome.LEFT_SINGLE:
        verb = "reach" if second_person else "reaches"
        return f"Final vote: {player} {verb} the finale single."
    verb = "were" if second_person else "was"
    return f"Final vote: {player} {verb} already dumped from the island."


def _couple_key(couple: Couple) -> str:
    return "|".join(sorted([couple.partner_a_id, couple.partner_b_id]))


def _player_partner(couple: Couple | None, state: GameState) -> str:
    if couple is None:
        return "their partner"
    partner_id: str | None = None
    if couple.partner_a_id == state.player.id:
        partner_id = couple.partner_b_id
    elif couple.partner_b_id == state.player.id:
        partner_id = couple.partner_a_id
    if partner_id is None:
        return "their partner"
    return _islander_name(state, partner_id)


def _islander_name(state: GameState, islander_id: str) -> str:
    for islander in state.islanders:
        if islander.id == islander_id:
            return islander.name
    return islander_id
