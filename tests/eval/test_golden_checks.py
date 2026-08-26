from types import SimpleNamespace

import pytest

from src.game.agents.runtime import AgentTrace
from src.game.eval.golden_checks import _validate_contextual_options_preserved
from src.game.state.models import FollowUpMenu, FollowUpOption


def test_contextual_options_check_rejects_a_bespoke_intent_dropped_by_assembly() -> None:
    final_menu = FollowUpMenu(
        npc_will_leave=False,
        options=[
            FollowUpOption(
                label="End on a good note",
                category="exit",
                intent_kind="end_softly",
                stat_used=None,
                risk="safe",
                tone="warm",
            ),
            FollowUpOption(
                label="Ask about that",
                category="friendly",
                intent_kind="ask_about_topic",
                stat_used="eq",
                risk="low",
                tone="curious",
            ),
        ],
    )
    trace = AgentTrace(
        agent_name="contextual_options",
        model="test-model",
        reasoning_effort="low",
        attempt=1,
        prompt_path="test",
        output_type="ContextualBespoke",
        output={"options": [{"label": "Name the pressure", "intent_kind": "supportive_validate"}]},
    )

    with pytest.raises(ValueError, match="supportive_validate"):
        _validate_contextual_options_preserved(
            SimpleNamespace(follow_up_menu=final_menu, agent_traces=[trace])
        )
