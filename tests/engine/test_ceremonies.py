"""Tests for deterministic ceremony mechanics."""

from __future__ import annotations

from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.ceremonies import arrive_heart_throb, pairing
from src.game.engine.rules import apply_action
from src.game.state.models import Gender, new_game
from src.game.state.rng import SeededRng


def test_pairing_pairs_player_with_top_relationship() -> None:
    """Player gets the highest-scored active heartbreaker."""
    state = new_game(1)
    state.heartbreakers[1].relationship.affection = 40

    result = pairing(state)

    assert result.couples[0].partner_a_id == "player"
    assert result.couples[0].partner_b_id == "maya"


def test_pairing_eliminates_leftover_heartbreaker() -> None:
    """An odd active cast leaves one heartbreaker sent home."""
    state = new_game(1)
    state.heartbreakers[-1].eliminated = True
    arrive_heart_throb(state)

    result = pairing(state)

    assert result.eliminated_id is not None
    assert any(heartbreaker.eliminated for heartbreaker in state.heartbreakers)


def test_pairing_keeps_npc_couples_opposite_gender() -> None:
    """Later ceremony matching uses the same gender constraint as opening coupling."""
    state = new_game(1)
    state.day = 3
    state.player.gender = Gender.MAN
    for heartbreaker in state.heartbreakers:
        heartbreaker.relationship.affection = 10
        heartbreaker.relationship.chemistry = 10
        heartbreaker.relationship.trust = 10

    result = pairing(state, "chloe")

    genders = {heartbreaker.id: heartbreaker.gender for heartbreaker in state.heartbreakers}
    genders[state.player.id] = state.player.gender
    for couple in result.couples:
        assert genders[couple.partner_a_id] != genders[couple.partner_b_id]


def test_pairing_rejects_same_gender_player_choice() -> None:
    """A player cannot choose a same-gender pairing partner in v0."""
    state = new_game(1)
    state.day = 3
    state.player.gender = Gender.MAN

    try:
        pairing(state, "liam")
    except ValueError as exc:
        assert "opposite sex" in str(exc)
    else:
        raise AssertionError("same-gender pairing choice should fail")


def test_heart_throb_arrival_is_idempotent() -> None:
    """The day-four heart_throb is inserted once."""
    state = new_game(1)

    first = arrive_heart_throb(state)
    second = arrive_heart_throb(state)

    assert first.id == "aisha"
    assert second.id == "aisha"
    assert [heartbreaker.id for heartbreaker in state.heartbreakers].count("aisha") == 1


def test_pairing_pick_surfaces_eligible_partners() -> None:
    """When a pairing gather is pending, the action menu offers partner picks."""
    from src.game.engine.actions import available_actions
    from src.game.state.models import Location, PendingGather

    state = new_game(2)
    state.day = 3
    state.player.gender = Gender.MAN
    state.pending_gather = PendingGather(
        kind="ceremony",
        event_id="pairing_day_3",
        gather_location=Location.FLAME_DECK,
        fires_on_turn=state.turn_index,
    )
    state.location_id = Location.FLAME_DECK

    actions = available_actions(state)

    # Every action should be PAIR (no JOIN_GATHER) and target an
    # opposite-sex heartbreaker.
    kinds = {spec.action.kind for spec in actions}
    assert kinds == {ActionKind.PAIR}
    targets = {spec.action.target_id for spec in actions}
    expected_women = {
        heartbreaker.id
        for heartbreaker in state.heartbreakers
        if heartbreaker.gender == Gender.WOMAN and not heartbreaker.eliminated
    }
    assert targets == expected_women


def test_pairing_pick_applies_player_choice() -> None:
    """Applying a PAIR during a pending pairing gather resolves it."""
    from src.game.agents.turn_agents import mock_turn_agents
    from src.game.engine.turn import run_turn
    from src.game.state.models import Location, PendingGather

    state = new_game(2)
    state.day = 3
    state.player.gender = Gender.MAN
    state.phase_clock.elapsed_minutes = state.phase_clock.budget_minutes
    from src.game.state.models import Phase

    state.phase = Phase.EVENING
    state.pending_gather = PendingGather(
        kind="ceremony",
        event_id="pairing_day_3",
        gather_location=Location.FLAME_DECK,
        fires_on_turn=state.turn_index,
    )
    state.location_id = Location.FLAME_DECK

    # Pick Maya (any opposite-sex heartbreaker)
    turn = run_turn(
        state,
        PlayerAction(kind=ActionKind.PAIR, target_id="maya"),
        SeededRng(99),
        mock_turn_agents(),
    )

    assert turn.state.pending_gather is None
    player_couple = next(
        couple
        for couple in turn.state.couples
        if "player" in {couple.partner_a_id, couple.partner_b_id}
    )
    other = (
        player_couple.partner_b_id
        if player_couple.partner_a_id == "player"
        else player_couple.partner_a_id
    )
    assert other == "maya"


def test_pairing_events_emit_display_safe_messages() -> None:
    """Ceremony event producers resolve ids to display names at the source.

    Regression for the leak where mock/static-mode surfaces a pairing event
    message verbatim: a steal attempt, partner-stolen, and elimination built
    from raw starting-cast ids (``blake`` etc.) must render bare display
    names — never a raw id, the meta phrase "the player", or the internal
    ``(roll X vs Y)`` dice digits (ENGINEERING R7 — typed at the source).
    """
    from src.game.engine.ceremonies import PairingResult
    from src.game.engine.couples import StealAttempt
    from src.game.engine.turn_events import pairing_events
    from src.game.state.models import Couple

    state = new_game(1)
    state.player.name = "Demo"
    ceremony = PairingResult(
        couples=[Couple(partner_a_id="blake", partner_b_id="sophie", formed_on_day=3)],
        eliminated_id="nia",
        steal_attempts=[
            StealAttempt(
                heart_throb_id="blake",
                target_id="sophie",
                abandoned_id="jordan",
                chance=55,
                roll=20,
                success=True,
            )
        ],
    )

    messages = " || ".join(event.message for event in pairing_events(state, ceremony))

    for raw_id in ("blake", "sophie", "jordan", "nia"):
        assert raw_id not in messages
    assert "the player" not in messages.lower()
    assert "(roll" not in messages
    # Bare display names are present.
    assert "Blake" in messages
    assert "Sophie" in messages
    assert "Jordan" in messages
    assert "Nia" in messages


def test_public_perception_bounds() -> None:
    """Perception changes stay in the 0-100 range."""
    state = new_game(1)
    state.player.public_perception = 1

    state.heartbreakers[0].relationship.affection = 20
    apply_action(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="flirty_compliment_looks",
        ),
        SeededRng(19),
    )

    assert state.player.public_perception == 0
