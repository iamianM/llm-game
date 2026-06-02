"""Tests for final Pulse vote resolution."""

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
    """The final Pulse vote resolves after the mandatory day-six evening gather."""
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
    state.heartbreakers[0].relationship.affection = 60
    state.heartbreakers[0].relationship.trust = 40
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

    chloe = next(heartbreaker for heartbreaker in state.heartbreakers if heartbreaker.id == "chloe")
    assert chloe.name in message
    assert state.player.name in message
    # The raw, name-agnostic label and lowercase ids never reach the player.
    assert "the player" not in message
    assert "chloe" not in message


def test_final_vote_message_uses_second_person_verbs_for_nameless_player() -> None:
    """The "You" placeholder must conjugate in the second person, not "You finishes"."""
    runner_up = new_game(1)
    runner_up.player.public_perception = 10
    runner_up.couples = [
        Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=5),
        Couple(partner_a_id="maya", partner_b_id="liam", formed_on_day=5),
    ]
    runner_up_msg = final_vote_message(final_vote(runner_up), runner_up)
    assert runner_up_msg == "Pulse vote: You finish as a runner-up couple."

    single = new_game(1)
    single.couples = [Couple(partner_a_id="maya", partner_b_id="liam", formed_on_day=5)]
    single_msg = final_vote_message(final_vote(single), single)
    assert single_msg == "Pulse vote: You reach the finale single."

    sent_home_state = new_game(1)
    sent_home_state.outcome = RunOutcome.ELIMINATED
    sent_home_msg = final_vote_message(final_vote(sent_home_state), sent_home_state)
    assert sent_home_msg == "Pulse vote: You were already Heart Out."

    # No agreement slip in any branch.
    for message in (runner_up_msg, single_msg, sent_home_msg):
        assert "You finishes" not in message
        assert "You reaches" not in message
        assert "You was" not in message


def test_final_vote_message_uses_third_person_verbs_for_named_player() -> None:
    """A player who set a real name stays a third-person subject ("Alex finishes")."""
    state = new_game(1)
    state.player.name = "Alex"
    state.player.public_perception = 10
    state.couples = [
        Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=5),
        Couple(partner_a_id="maya", partner_b_id="liam", formed_on_day=5),
    ]

    message = final_vote_message(final_vote(state), state)

    assert message == "Pulse vote: Alex finishes as a runner-up couple."


def test_final_vote_emits_ceremony_event() -> None:
    """Ceremony wrapper produces a narratable event."""
    state = new_game(1)
    state.couples = [Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=5)]

    event = final_vote_ceremony(state)

    assert event.kind == "final_vote"
    assert state.outcome is not None
