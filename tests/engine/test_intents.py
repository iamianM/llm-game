"""Tests for the tiered intent catalog."""

from __future__ import annotations

from src.game.engine.intents import IntentCategory, available_intents_for, load_intents
from src.game.state.models import new_game


def test_load_intents_contains_all_categories() -> None:
    """The catalog covers the four core intent categories."""
    categories = {intent.category for intent in load_intents()}

    assert categories == {
        IntentCategory.FRIENDLY,
        IntentCategory.FLIRTY,
        IntentCategory.DEEP,
        IntentCategory.BANTER,
    }


def test_available_intents_filter_by_affection_unlocks() -> None:
    """Fresh relationships show Friendly/Banter but lock Flirty/Deep."""
    state = new_game(1)

    intents = available_intents_for(state, "chloe")
    ids = {intent.id for intent in intents}

    assert "friendly_chat_villa" in ids
    assert "banter_tell_joke" in ids
    assert "flirty_compliment_looks" not in ids
    assert "deep_share_feelings" not in ids


def test_flirty_unlocks_at_affection_threshold() -> None:
    """Flirty intents unlock once relationship reaches the configured threshold."""
    state = new_game(1)
    state.islanders[0].relationship.affection = 20

    ids = {intent.id for intent in available_intents_for(state, "chloe")}

    assert "flirty_compliment_looks" in ids
