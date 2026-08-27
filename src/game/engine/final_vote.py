"""Final Pulse vote resolution."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from src.game.engine.audience import ranked_audience_couples
from src.game.state.models import Couple, GameState, RunOutcome


class FinalVoteResult(BaseModel):
    """Resolved final vote outcome."""

    model_config = ConfigDict(extra="forbid")

    winner: Couple | None
    runner_up: Couple | None
    ranked_couples: list[Couple]
    player_rank: int | None
    outcome: RunOutcome


def final_vote(state: GameState) -> FinalVoteResult:
    """Resolve the final Pulse vote and assign ``state.outcome``."""
    if state.outcome is RunOutcome.ELIMINATED:
        return FinalVoteResult(
            winner=None,
            runner_up=None,
            ranked_couples=[],
            player_rank=None,
            outcome=RunOutcome.ELIMINATED,
        )
    if state.player.eliminated:
        state.outcome = RunOutcome.ELIMINATED
        return FinalVoteResult(
            winner=None,
            runner_up=None,
            ranked_couples=[],
            player_rank=None,
            outcome=RunOutcome.ELIMINATED,
        )
    ranked = ranked_audience_couples(state)
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
        ranked_couples=ranked,
        player_rank=player_rank,
        outcome=state.outcome,
    )


def final_vote_message(result: FinalVoteResult, state: GameState) -> str:
    """Return a concise, player-facing ceremony message.

    This string is surfaced verbatim in mock/static mode (the event narrator
    only runs in real-LLM mode), so it must already read in display terms — the
    player's name and the partner's display name, never the raw "the player"
    label or a lowercase heartbreaker id.

    The nameless player carries the placeholder name "You", so the verb has to
    agree in the second person ("You finish", not "You finishes"). A player who
    set a real name via the character creator is a third-person subject ("Alex
    finishes"). The plural WON clause ("X and Y win") reads correctly either way.
    """
    player = state.player.name
    second_person = player.strip().lower() == "you"
    if result.outcome is RunOutcome.WON_AS_COUPLE:
        partner = _player_partner(result.winner, state)
        outcome = f"{player} and {partner} win as the top couple."
    elif result.outcome is RunOutcome.RUNNER_UP_COUPLE:
        verb = "finish" if second_person else "finishes"
        outcome = f"{player} {verb} as a runner-up couple."
    elif result.outcome is RunOutcome.LEFT_SINGLE:
        verb = "reach" if second_person else "reaches"
        outcome = f"{player} {verb} the finale single."
    else:
        verb = "were" if second_person else "was"
        outcome = f"{player} {verb} already Heart Out."
    ranking = _ranking_message(result.ranked_couples, state)
    return f"Pulse vote: {ranking} {outcome}" if ranking else f"Pulse vote: {outcome}"


def _ranking_message(ranked: list[Couple], state: GameState) -> str:
    placements = ("first", "second", "third", "fourth")
    entries = [
        f"{placements[index]} {_couple_names(couple, state)}"
        for index, couple in enumerate(ranked[: len(placements)])
    ]
    return f"Final ranking: {'; '.join(entries)}." if entries else ""


def _couple_names(couple: Couple, state: GameState) -> str:
    return " and ".join(
        state.player.name if actor_id == state.player.id else _heartbreaker_name(state, actor_id)
        for actor_id in (couple.partner_a_id, couple.partner_b_id)
    )


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
    return _heartbreaker_name(state, partner_id)


def _heartbreaker_name(state: GameState, heartbreaker_id: str) -> str:
    for heartbreaker in state.heartbreakers:
        if heartbreaker.id == heartbreaker_id:
            return heartbreaker.name
    return heartbreaker_id
