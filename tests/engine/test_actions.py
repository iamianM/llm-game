"""Tests for available action generation and validation."""

from __future__ import annotations

import pytest

from src.game.engine.actions import ActionKind, PlayerAction, available_actions, validate_action
from src.game.state.models import new_game


def test_available_actions_include_visible_conversation_targets_and_ambient() -> None:
    """Visible islanders get categorized START_CONVERSATION openers, movement, and ambient."""
    state = new_game(1)

    actions = [spec.action for spec in available_actions(state)]

    # Free-time openers carry an intent_id so the CharacterMenu category tree
    # populates from real intents. Friendly intents (unlock 0) are always
    # surfaced for a co-located target; nobody who is elsewhere is targetable.
    chloe_starts = [
        action
        for action in actions
        if action.kind is ActionKind.START_CONVERSATION and action.target_id == "chloe"
    ]
    assert chloe_starts, "co-located target should surface conversation openers"
    assert all(action.intent_id is not None for action in chloe_starts)
    assert "friendly_chat_villa" in {action.intent_id for action in chloe_starts}
    assert not any(
        action.kind is ActionKind.START_CONVERSATION and action.target_id == "maya"
        for action in actions
    )
    assert PlayerAction(kind=ActionKind.MOVE, target_id="kitchen") in actions
    assert PlayerAction(kind=ActionKind.MOVE, target_id="terrace") in actions
    assert PlayerAction(kind=ActionKind.AMBIENT, target_id="ambient_wait") in actions
    assert any(action.kind is ActionKind.AMBIENT for action in actions)
    assert PlayerAction(kind=ActionKind.END_CONVERSATION) not in actions


def test_validate_action_rejects_hidden_target() -> None:
    """Targets outside the visible action set fail loudly."""
    state = new_game(1)

    with pytest.raises(ValueError, match="target is not visible"):
        validate_action(
            state,
            PlayerAction(
                kind=ActionKind.START_CONVERSATION,
                target_id="unknown",
                intent_id="friendly_chat_villa",
            ),
        )


def test_validate_action_rejects_other_location_target() -> None:
    """Other-location islanders are not targetable."""
    state = new_game(1)

    with pytest.raises(ValueError, match="target is not visible"):
        validate_action(
            state,
            PlayerAction(
                kind=ActionKind.START_CONVERSATION,
                target_id="maya",
                intent_id="friendly_chat_villa",
            ),
        )


def test_round_based_challenge_actions_target_the_named_islander_not_the_partner() -> None:
    """Round-based minigame options carry the islander they name as target_id.

    Round-based minigames resolve purely via ``payload.choice_id``, so target_id
    is advisory. It used to be hardcoded to the player's partner for *every*
    option (``participants[1]``), which misled the LLM agents/decider (all
    options looked like they pointed at one person) and polluted telemetry.
    Each Snog/Wed/Pass option must instead point at the islander it names.
    """
    from src.game.engine.challenges import schedule_challenge
    from src.game.engine.snog_marry_pie import build_rounds
    from src.game.state.rng import SeededRng

    state = new_game(1)
    challenge = schedule_challenge(5)
    assert challenge is not None and challenge.kind == "snog_marry_pie"
    rounds = build_rounds(state, SeededRng(1))
    # participants[1]="chloe" is the historic partner stand-in that used to leak
    # onto every option; the fix must not reproduce it blindly.
    state.pending_challenge = challenge.model_copy(
        update={"rounds": rounds, "participants": ["player", "chloe"]}
    )

    specs = [
        spec
        for spec in available_actions(state)
        if spec.action.kind is ActionKind.CHALLENGE_RESPONSE
    ]
    assert specs, "a pending round-based challenge should surface response actions"

    islander_ids = {islander.id for islander in state.islanders}
    first_round = state.pending_challenge.rounds[0]
    target_for_choice = {choice.id: choice.fact_value for choice in first_round.choices}
    for spec in specs:
        choice_id = spec.action.payload["choice_id"]
        assert spec.action.target_id == target_for_choice[choice_id]
        assert spec.action.target_id in islander_ids

    # The options must not all collapse onto a single partner id (the old bug);
    # each Snog/Wed/Pass pick names a distinct islander.
    targets = {spec.action.target_id for spec in specs}
    assert len(targets) == len(specs)
