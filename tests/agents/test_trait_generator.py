"""Trait Generator validation."""

from __future__ import annotations

import pytest

from src.game.agents.trait_generator import mock_opening_trait_cards, validate_trait_cards
from src.game.content.trait_library import heart_throb_trait_cards


def test_mock_trait_cards_validate() -> None:
    cards = mock_opening_trait_cards()
    validate_trait_cards(cards)
    assert all(len(card.flavor_traits) >= 6 for card in cards.values())
    assert all(len(card.flavor_traits) >= 6 for card in heart_throb_trait_cards().values())
    assert len(cards) == 8


def test_trait_card_validation_rejects_duplicate_secret_engine() -> None:
    cards = mock_opening_trait_cards()
    first, second = list(cards)[:2]
    cards[second] = cards[second].model_copy(
        update={"persona": cards[second].persona.model_copy(update={"secret_engine": cards[first].persona.secret_engine})}
    )
    with pytest.raises(ValueError, match="duplicate"):
        validate_trait_cards(cards)
