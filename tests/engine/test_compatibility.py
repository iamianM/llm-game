"""Tests for personality compatibility mechanics."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.game.engine.compatibility import (
    apply_familiarity,
    attachment_delta_modifier,
    compatibility_bonus,
    dealbreaker_penalty,
    revealed_preferences,
)
from src.game.state.models import AttachmentStyle, Big5, TypeOnPaper, new_game


def test_compatibility_bonus_increases_with_matching_values() -> None:
    state = new_game(1)
    state.player.archetype_id = "loyal_friend"

    assert compatibility_bonus(state, state.islanders[0], ["loyalty"]) > 0


def test_compatibility_bonus_capped_at_20() -> None:
    state = new_game(1)
    target = state.islanders[0]
    target.type_on_paper.personality_type = ["a", "b", "c", "d", "e", "f"]

    assert compatibility_bonus(state, target, ["a", "b", "c", "d", "e", "f"]) == 20


def test_dealbreaker_penalty_applied_when_player_carries_tag() -> None:
    state = new_game(1)

    assert dealbreaker_penalty(state.islanders[0], ["arrogance"]) == 15


def test_dealbreaker_penalty_not_double_counted() -> None:
    state = new_game(1)

    assert dealbreaker_penalty(state.islanders[0], ["arrogance", "arrogance"]) == 15


def test_attachment_secure_deep_success_bonus() -> None:
    state = new_game(1)

    delta = attachment_delta_modifier(state.islanders[0], "honest_vulnerable", True)

    assert delta.trust == 1


def test_attachment_anxious_amplifies_miss_trust_loss() -> None:
    state = new_game(1)

    delta = attachment_delta_modifier(state.islanders[1], "escalate_flirt", False)

    assert delta.trust == -3


def test_attachment_avoidant_reduces_chemistry_growth() -> None:
    state = new_game(1)
    target = state.islanders[1]
    target.attachment = AttachmentStyle.AVOIDANT

    delta = attachment_delta_modifier(target, "escalate_flirt", True)

    assert delta.chemistry == -1


def test_familiarity_increments_and_caps() -> None:
    state = new_game(1)
    target = state.islanders[0]
    target.familiarity_with_player = 99

    apply_familiarity(target, 5)

    assert target.familiarity_with_player == 100


def test_revealed_preferences_unlock_by_threshold() -> None:
    state = new_game(1)
    target = state.islanders[0]
    target.familiarity_with_player = 50

    revealed = revealed_preferences(target)

    assert set(revealed) == {"physical_type", "personality_type"}


def test_big5_rejects_out_of_range_value() -> None:
    with pytest.raises(ValidationError):
        Big5(openness=11, conscientiousness=5, extraversion=5, agreeableness=5, neuroticism=5)


def test_type_on_paper_required_fields() -> None:
    prefs = TypeOnPaper(
        physical_type="kind eyes",
        personality_type=["funny"],
        values=["loyalty"],
        dealbreakers=["arrogance"],
    )

    assert prefs.values == ["loyalty"]
