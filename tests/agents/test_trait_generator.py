"""Trait Generator validation."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.game.agents.trait_generator import (
    OpenAITraitGenerator,
    TraitCardBatch,
    mock_opening_trait_cards,
    opening_generation_seeds,
    validate_trait_cards,
)
from src.game.content.trait_library import heart_throb_trait_cards
from src.game.state.models import new_game


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


def test_openai_trait_generator_retries_with_schema_feedback() -> None:
    cards = mock_opening_trait_cards()
    valid_output = TraitCardBatch.model_validate({"cast": {"chloe": cards["chloe"].model_dump()}}).model_dump_json()
    fake_responses = _FakeResponses(valid_output)
    generator = OpenAITraitGenerator()
    generator.__dict__["_client"] = SimpleNamespace(responses=fake_responses)

    result = generator.generate_opening_cast(opening_generation_seeds(new_game(1).islanders[:1]))

    assert result["chloe"].persona.secret_engine == cards["chloe"].persona.secret_engine
    assert len(fake_responses.inputs) == 2
    assert "Previous output failed validation" in fake_responses.inputs[1]


class _FakeResponses:
    def __init__(self, valid_output: str) -> None:
        self.valid_output = valid_output
        self.inputs: list[str] = []

    def create(self, **kwargs: object) -> object:
        self.inputs.append(str(kwargs["input"]))
        if len(self.inputs) == 1:
            raise ValueError("TraitCard chloe must have 6-10 flavor traits")
        return SimpleNamespace(output_text=self.valid_output)
