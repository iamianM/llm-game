"""Tests for deterministic intent rules."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.intents import Intent, IntentCategory, IntentDeltaTable, get_intent
from src.game.engine.rules import (
    apply_action,
    follow_up_success_chance,
    intent_success_breakdown,
    intent_success_chance,
)
from src.game.state.models import (
    Conversation,
    FollowUpMenu,
    FollowUpOption,
    RelationshipDelta,
    new_game,
)
from src.game.state.rng import SeededRng


def test_intent_success_chance_uses_configured_stat_and_affection() -> None:
    """F1 intent math uses the intent's configured player stat."""
    state = new_game(1)
    intent = get_intent("friendly_chat_villa")

    assert intent_success_chance(state, state.islanders[0], intent) == 80


def test_initial_intent_chance_capped_by_category_default() -> None:
    """Initial conversation risk caps keep friendly/banter rolls from reaching 95."""
    state = new_game(1)
    state.player.stats.banter = 9
    state.islanders[0].relationship.affection = 100
    intent = get_intent("banter_tell_joke")

    assert intent_success_chance(state, state.islanders[0], intent) == 80


def test_intent_success_breakdown_names_formula_terms() -> None:
    """Initial intent results carry a reviewable chance formula."""
    state = new_game(1)
    state.player.stats.banter = 9
    state.islanders[0].relationship.affection = 100
    intent = get_intent("banter_tell_joke")

    breakdown = intent_success_breakdown(state, state.islanders[0], intent)

    assert breakdown.base == 50
    assert breakdown.stat_name == "banter"
    assert breakdown.stat_contribution == 45
    assert breakdown.affection_contribution == 25
    assert breakdown.risk == "low"
    assert breakdown.risk_modifier == 5
    assert breakdown.pre_cap == 129
    assert breakdown.cap == 80
    assert breakdown.final_chance == 80


def test_intent_success_chance_includes_compatibility_bonus() -> None:
    """Compatibility bonus appears in the chance breakdown."""
    state = new_game(1)
    state.player.archetype_id = "loyal_friend"
    target = state.islanders[0]
    intent = get_intent("friendly_chat_villa")

    breakdown = intent_success_breakdown(state, target, intent)

    assert breakdown.compatibility_bonus > 0


def test_intent_success_chance_includes_dealbreaker_penalty() -> None:
    """Dealbreaker tags reduce chance."""
    state = new_game(1)
    target = state.islanders[0]
    target.type_on_paper.dealbreakers = ["friendly"]
    intent = get_intent("friendly_chat_villa")

    breakdown = intent_success_breakdown(state, target, intent)

    assert breakdown.dealbreaker_penalty == 15


def test_initial_intent_explicit_risk_overrides_default() -> None:
    """Explicit intent risk overrides category defaults."""
    state = new_game(1)
    state.player.stats.banter = 9
    state.islanders[0].relationship.affection = 100
    intent = Intent(
        id="test_high_risk_joke",
        category=IntentCategory.BANTER,
        label="Risky joke",
        stat_used="banter",
        unlock_affection=0,
        risk="high",
        relationship_deltas=IntentDeltaTable(
            success=RelationshipDelta(friendship=1),
            miss=RelationshipDelta(friendship=-1),
        ),
    )

    assert intent_success_chance(state, state.islanders[0], intent) == 50


def test_friendly_intent_applies_success_delta() -> None:
    """A successful intent applies the configured success delta."""
    state = new_game(1)

    result = apply_action(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_villa",
        ),
        SeededRng(1),
    )

    assert result.success is True
    assert result.roll == 18
    assert result.chance_breakdown is not None
    assert result.chance_breakdown.final_chance == result.success_chance
    assert result.relationship_deltas == {
        "chloe": RelationshipDelta(affection=2, friendship=1)
    }
    assert state.islanders[0].relationship.affection == 12
    assert state.islanders[0].relationship.friendship == 1


def test_locked_intent_fails_loud() -> None:
    """Locked intent ids cannot bypass menu filtering."""
    state = new_game(1)

    with pytest.raises(ValueError, match="locked"):
        apply_action(
            state,
            PlayerAction(
                kind=ActionKind.START_CONVERSATION,
                target_id="chloe",
                intent_id="deep_share_feelings",
            ),
            SeededRng(1),
        )


def test_relationship_delta_rejects_unknown_field() -> None:
    """RelationshipDelta catches misspelled stat names."""
    with pytest.raises(ValidationError):
        RelationshipDelta.model_validate({"affection": 1, "chemsitry": 2})


def test_follow_up_honest_vulnerable_builds_trust() -> None:
    """Successful vulnerable follow-ups build trust mechanically."""
    state = _state_with_follow_up("honest_vulnerable", risk="medium", stat_used="eq")

    result = apply_action(
        state,
        PlayerAction(kind=ActionKind.RESPOND_WITH, intent_id="honest_vulnerable"),
        SeededRng(1),
    )

    assert result.success is True
    assert result.relationship_deltas == {"chloe": RelationshipDelta(affection=2, trust=6)}
    assert state.islanders[0].relationship.trust == 6


def test_follow_up_escalate_flirt_miss_drops_chemistry() -> None:
    """Missed flirt follow-ups can backfire."""
    state = _state_with_follow_up("escalate_flirt", risk="medium", stat_used="charm")
    state.islanders[0].relationship.chemistry = 5
    state.islanders[0].relationship.trust = 5

    result = apply_action(
        state,
        PlayerAction(kind=ActionKind.RESPOND_WITH, intent_id="escalate_flirt"),
        SeededRng(19),
    )

    assert result.success is False
    assert result.relationship_deltas == {
        "chloe": RelationshipDelta(chemistry=-3, trust=-1)
    }
    assert state.islanders[0].relationship.chemistry == 2
    assert state.islanders[0].relationship.trust == 4


def test_follow_up_unknown_intent_raises() -> None:
    """Unmapped follow-up intent kinds fail loud."""
    state = _state_with_follow_up("invented_intent", risk="medium", stat_used="banter")

    with pytest.raises(ValueError, match="unknown follow-up intent_kind"):
        apply_action(
            state,
            PlayerAction(kind=ActionKind.RESPOND_WITH, intent_id="invented_intent"),
            SeededRng(1),
        )


def test_follow_up_high_risk_scales_deltas() -> None:
    """Risk level scales follow-up deltas."""
    state = _state_with_follow_up("go_deeper", risk="high", stat_used="eq")

    result = apply_action(
        state,
        PlayerAction(kind=ActionKind.RESPOND_WITH, intent_id="go_deeper"),
        SeededRng(1),
    )

    assert result.success is True
    assert result.relationship_deltas == {"chloe": RelationshipDelta(affection=5, trust=7)}


def test_follow_up_success_chance_is_capped_by_risk() -> None:
    """Risk labels remain meaningful even with high stats and affection."""
    state = new_game(1)
    target = state.islanders[0]
    target.relationship.affection = 100
    state.player.stats.banter = 9

    assert follow_up_success_chance(state, target, "banter", "safe") == 90
    assert follow_up_success_chance(state, target, "banter", "low") == 80
    assert follow_up_success_chance(state, target, "banter", "medium") == 65
    assert follow_up_success_chance(state, target, "banter", "high") == 50


def _state_with_follow_up(
    intent_kind: str,
    *,
    risk: str,
    stat_used: str | None,
):
    state = new_game(1)
    state.active_conversation = Conversation(
        target_id="chloe",
        started_on_turn=0,
        started_on_day=1,
        pending_options=FollowUpMenu(
            options=[
                FollowUpOption(
                    label="Test option",
                    category="deep",
                    intent_kind=intent_kind,
                    stat_used=stat_used,
                    risk=risk,
                    tone="sincere",
                ),
                FollowUpOption(
                    label="End softly",
                    category="exit",
                    intent_kind="end_softly",
                    stat_used=None,
                    risk="safe",
                    tone="warm",
                ),
            ],
            npc_will_leave=False,
        ),
    )
    return state
