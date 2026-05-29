"""Tests for final public vote resolution."""

from __future__ import annotations

from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.ceremonies import final_vote_ceremony
from src.game.engine.final_vote import final_vote, final_vote_message
from src.game.engine.turn import run_turn
from src.game.state.models import Couple, Phase, RunOutcome, new_game
from src.game.state.rng import SeededRng


def test_final_vote_assigns_winner_couple_outcome() -> None:
    """The top-ranked player couple wins."""
    state = new_game(1)
    state.player.public_perception = 95
    state.couples = [
        Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=5),
        Couple(partner_a_id="maya", partner_b_id="liam", formed_on_day=5),
    ]

    result = final_vote(state)

    assert result.outcome is RunOutcome.WON_AS_COUPLE
    assert state.outcome is RunOutcome.WON_AS_COUPLE


def test_final_vote_assigns_runner_up_outcome() -> None:
    """A non-winning player couple becomes runner-up."""
    state = new_game(1)
    state.player.public_perception = 10
    state.couples = [
        Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=5),
        Couple(partner_a_id="maya", partner_b_id="liam", formed_on_day=5),
    ]

    result = final_vote(state)

    assert result.outcome is RunOutcome.RUNNER_UP_COUPLE


def test_final_vote_player_left_single_outcome() -> None:
    """A player outside all couples reaches the finale single."""
    state = new_game(1)
    state.couples = [Couple(partner_a_id="maya", partner_b_id="liam", formed_on_day=5)]

    result = final_vote(state)

    assert result.outcome is RunOutcome.LEFT_SINGLE


def test_final_vote_does_not_override_existing_elimination() -> None:
    """Eliminated player state remains terminal."""
    state = new_game(1)
    state.outcome = RunOutcome.ELIMINATED

    result = final_vote(state)

    assert result.outcome is RunOutcome.ELIMINATED


def test_final_vote_fires_only_on_day_six_evening() -> None:
    """The final vote resolves after the mandatory day-six evening gather."""
    state = new_game(1)
    state.day = 6
    state.phase = Phase.EVENING
    state.couples = [Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=5)]

    scheduled = run_turn(state, PlayerAction(kind=ActionKind.AMBIENT, target_id="ambient_wait"), SeededRng(1))
    assert scheduled.state.pending_gather is not None
    result = run_turn(state, PlayerAction(kind=ActionKind.JOIN_GATHER), SeededRng(1))

    assert any(event.kind == "final_vote" for event in result.ceremony_events)
    assert result.state.outcome is not None


def test_final_vote_uses_audience_score_plus_couple_strength() -> None:
    """Strong player relationships can break a public-perception tie."""
    state = new_game(1)
    state.islanders[0].relationship.affection = 60
    state.islanders[0].relationship.trust = 40
    state.couples = [
        Couple(partner_a_id="maya", partner_b_id="liam", formed_on_day=5),
        Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=5),
    ]

    result = final_vote(state)

    assert result.winner is not None
    assert "player" in {result.winner.partner_a_id, result.winner.partner_b_id}


def test_final_vote_ties_break_deterministically_by_couple_key() -> None:
    """Equal scores sort by a stable couple key."""
    state = new_game(1)
    state.couples = [
        Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=5),
        Couple(partner_a_id="liam", partner_b_id="maya", formed_on_day=5),
    ]

    result = final_vote(state)

    assert result.winner is not None
    assert result.winner.partner_a_id == "player"


def test_final_vote_message_names_player_partner() -> None:
    """Winning message names the player and partner by display name, never raw ids."""
    state = new_game(1)
    state.player.public_perception = 95
    state.couples = [Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=5)]

    result = final_vote(state)
    message = final_vote_message(result, state)

    chloe = next(islander for islander in state.islanders if islander.id == "chloe")
    assert chloe.name in message
    assert state.player.name in message
    # The raw, name-agnostic label and lowercase ids never reach the player.
    assert "the player" not in message
    assert "chloe" not in message


def test_final_vote_emits_ceremony_event() -> None:
    """Ceremony wrapper produces a narratable event."""
    state = new_game(1)
    state.couples = [Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=5)]

    event = final_vote_ceremony(state)

    assert event.kind == "final_vote"
    assert state.outcome is not None
