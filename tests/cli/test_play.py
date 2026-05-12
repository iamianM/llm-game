"""Tests for the interactive CLI rendering helpers."""

from __future__ import annotations

from src.game.agents.background_dialogue import BackgroundExchange
from src.game.agents.villa_orchestrator import (
    ContinueConversation,
    NewConversation,
    NPCMovement,
    VillaUpdate,
)
from src.game.cli.commands.play import _print_state, _print_villa_update
from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.rules import MechanicalResult
from src.game.engine.turn import TurnResult
from src.game.engine.villa import AgentCommits
from src.game.state.models import Location, NPCNPCConversation, new_game


def test_print_state_shows_villa_map_and_active_conversations(capsys) -> None:
    """The CLI state view shows where islanders actually are."""
    state = new_game(1)
    state.islanders[1].location_id = Location.TERRACE
    state.npc_conversations.append(
        NPCNPCConversation(
            id="npcconv_test",
            participants=["maya", "liam"],
            location_id=Location.TERRACE,
            topic="playful breakfast competition",
            started_on_turn=1,
        )
    )

    _print_state(state)

    output = capsys.readouterr().out
    assert "You are at the POOL." in output
    assert "Pool      -> you, Chloe" in output
    assert 'Terrace   -> Maya, Liam -- Maya & Liam chatting about "playful breakfast competition"' in output
    assert "Chloe   affection 10" in output


def test_print_villa_update_names_movements_and_background_dialogue(capsys) -> None:
    """Villa updates are shown as named events instead of opaque counts."""
    state = new_game(1)
    state.islanders[0].location_id = Location.KITCHEN
    state.npc_conversations.append(
        NPCNPCConversation(
            id="npcconv_test",
            participants=["maya", "liam"],
            location_id=Location.TERRACE,
            topic="breakfast flirting",
            started_on_turn=1,
        )
    )
    turn = TurnResult(
        state=state,
        mechanical_result=MechanicalResult(
            action=PlayerAction(kind=ActionKind.ADVANCE_PHASE),
            success=True,
        ),
        available_actions=[],
        state_hash="hash",
        agent_commits=AgentCommits(
            villa_update=VillaUpdate(
                npc_movements=[
                    NPCMovement(
                        npc_id="chloe",
                        target_location=Location.POOL,
                        reason="drawn_to_player",
                    )
                ],
                conversation_starts=[
                    NewConversation(
                        participants=["maya", "liam"],
                        location=Location.TERRACE,
                        topic="breakfast flirting",
                    )
                ],
                conversation_continues=[
                    ContinueConversation(
                        conversation_id="npcconv_test",
                        nudge="keep it playful",
                    )
                ],
            ),
            background_dialogues=[
                BackgroundExchange(
                    speaker_a_line="*grins* Your pancake game better match the confidence.",
                    speaker_b_line="*laughs* Only one way to find out.",
                    tone="flirty",
                )
            ],
        ),
    )

    _print_villa_update(turn)

    output = capsys.readouterr().out
    assert "While you talked:" in output
    assert "Chloe joined you at the pool (drawn_to_player)" in output
    assert 'Maya & Liam started chatting at the terrace: "breakfast flirting"' in output
    assert 'Maya & Liam at the terrace kept talking: "keep it playful"' in output
    assert 'Background (flirty): "*grins* Your pancake game better match the confidence."' in output
