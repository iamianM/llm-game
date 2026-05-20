"""Paradise Hearts display translation tests."""

from __future__ import annotations

from src.api.display import display
from src.api.serializers import available_actions_api, memory_api
from src.game.engine.memory import create_memory
from src.game.state.models import Conversation, FollowUpMenu, FollowUpOption, new_game


def test_display_translates_protected_terms() -> None:
    assert display("recoupling") == "Pairing Ceremony"
    assert display("snog_marry_pie") == "Kiss Wed Pass"
    assert display("casa_amor") == "Flush of Hearts"
    assert display("casa_amor_return_reveal") == "Sunset Bay Return"
    assert display("opening") == "First Spark"
    assert display("intros") == "Day-1 Introductions"
    assert display("main") == "Sunset Bay"
    assert display("bombshell") == "Heart Throb"


def test_follow_up_actions_are_player_facing_and_hide_capped_pulse() -> None:
    state = new_game(1)
    state.player.public_perception = 100
    state.active_conversation = Conversation(
        target_id="chloe",
        started_on_turn=1,
        started_on_day=1,
        pending_options=FollowUpMenu(
            npc_will_leave=False,
            options=[
                FollowUpOption(
                    label="Ask what she is not saying",
                    category="deep",
                    intent_kind="go_deeper",
                    stat_used="eq",
                    risk="medium",
                    tone="vulnerable",
                    audience_hint="+",
                ),
                FollowUpOption(
                    label="End on a warm note",
                    category="exit",
                    intent_kind="end_softly",
                    stat_used=None,
                    risk="safe",
                    tone="warm",
                ),
            ],
        ),
    )

    actions = available_actions_api(state)
    follow_up = next(action for action in actions if action.intent_id == "go_deeper")

    assert follow_up.label == "Ask what she is not saying"
    assert follow_up.description == "Deep"
    assert follow_up.audience_hint == ""
    assert follow_up.stat_used == "Eq"


def test_memory_api_exposes_stable_identity() -> None:
    memory = create_memory(
        holder_id="player",
        subject_id="chloe",
        source="direct",
        day=1,
        turn=7,
        weight=5,
        tags=["supportive"],
        content="Chloe trusted the player after a careful chat.",
    )

    assert memory_api(memory).id == memory.id
