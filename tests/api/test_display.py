"""Paradise Hearts display translation tests."""

from __future__ import annotations

import pytest

from src.api.display import display
from src.api.serializers import action_label, available_actions_api, hide_redundant_hint, memory_api
from src.game.engine.actions import ActionKind, ActionSpec, PlayerAction
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


@pytest.mark.parametrize(
    "kind,target_id,intent_id,expected",
    [
        (ActionKind.MOVE, "pool", None, "Move to Pool"),
        (ActionKind.START_CONVERSATION, "chloe", None, "Talk to Chloe"),
        (ActionKind.END_CONVERSATION, None, None, "Walk away"),
        (ActionKind.RECOUPLE, "liam", None, "Pair with Liam"),
        (ActionKind.PROPOSE_RECOUPLE, "liam", None, "Ask Liam for a Heart Swap"),
        (ActionKind.NPC_PROPOSAL_RESPONSE, "liam", "accept", "Accept Liam's Heart Swap proposal"),
        (ActionKind.NPC_PROPOSAL_RESPONSE, "liam", "decline_politely", "Decline Liam politely"),
        (ActionKind.NPC_PROPOSAL_RESPONSE, "liam", "decline_harshly", "Decline Liam harshly"),
        (ActionKind.INTRODUCE_TO, "chloe", "intro_flirty", "Spark flirty with Chloe"),
        (ActionKind.INTRODUCE_TO, "chloe", "intro_deep", "Spark deep with Chloe"),
        (ActionKind.INTRODUCE_TO, "chloe", None, "Spark warmly with Chloe"),
        (ActionKind.CASA_DECISION, None, "return_with_original", "Return loyal"),
        (ActionKind.CASA_DECISION, "liam", "return_with_new", "Return with Liam"),
        (ActionKind.CASA_DECISION, None, "return_single", "Return solo"),
    ],
)
def test_action_label_covers_every_player_action(
    kind: ActionKind, target_id: str | None, intent_id: str | None, expected: str
) -> None:
    state = new_game(1)
    spec = ActionSpec(
        action=PlayerAction(kind=kind, target_id=target_id, intent_id=intent_id),
        label="fallback",
    )

    assert action_label(state, spec) == expected


def test_action_label_falls_back_to_spec_label_for_unmatched_branches() -> None:
    state = new_game(1)
    spec = ActionSpec(
        action=PlayerAction(kind=ActionKind.AMBIENT),
        label="Wait by the pool",
    )

    assert action_label(state, spec) == "Wait by the pool"


def test_hide_redundant_hint_drops_both_pinned_ends() -> None:
    state = new_game(1)

    state.player.public_perception = 95
    assert hide_redundant_hint(state, "+") == ""
    assert hide_redundant_hint(state, "-") == "-"

    state.player.public_perception = 5
    assert hide_redundant_hint(state, "-") == ""
    assert hide_redundant_hint(state, "+") == "+"

    state.player.public_perception = 50
    assert hide_redundant_hint(state, "+") == "+"
    assert hide_redundant_hint(state, "-") == "-"


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
