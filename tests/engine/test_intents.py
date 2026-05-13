"""Tests for the tiered intent catalog."""

from __future__ import annotations

from src.game.engine.intents import IntentCategory, available_intents_for, load_intents
from src.game.state.models import Gender, new_game


def test_load_intents_contains_all_categories() -> None:
    """The catalog covers the core and same-sex social categories."""
    categories = {intent.category for intent in load_intents()}

    assert categories == {
        IntentCategory.FRIENDLY,
        IntentCategory.FLIRTY,
        IntentCategory.DEEP,
        IntentCategory.BANTER,
        IntentCategory.BROMANCE,
        IntentCategory.GOSSIP_RING,
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


def test_intent_filter_blocks_flirty_on_same_sex_pair() -> None:
    state = new_game(1)
    state.player.gender = Gender.MAN
    liam = next(islander for islander in state.islanders if islander.id == "liam")
    liam.location_id = state.location_id
    liam.relationship.affection = 40

    ids = {intent.id for intent in available_intents_for(state, "liam")}

    assert "flirty_compliment_looks" not in ids
    assert "bromance_rib" in ids


def test_intent_filter_blocks_bromance_on_opposite_sex_pair() -> None:
    state = new_game(1)
    state.player.gender = Gender.MAN
    chloe = next(islander for islander in state.islanders if islander.id == "chloe")
    chloe.relationship.affection = 40

    ids = {intent.id for intent in available_intents_for(state, "chloe")}

    assert "flirty_compliment_looks" in ids
    assert "bromance_rib" not in ids
    assert "gossip_ring_dish_about_him" not in ids


def test_intent_filter_blocks_gossip_ring_on_men() -> None:
    state = new_game(1)
    state.player.gender = Gender.MAN
    liam = next(islander for islander in state.islanders if islander.id == "liam")
    liam.location_id = state.location_id
    liam.relationship.affection = 40

    ids = {intent.id for intent in available_intents_for(state, "liam")}

    assert "gossip_ring_dish_about_him" not in ids


def test_woman_same_sex_pair_gets_gossip_ring_not_flirty() -> None:
    state = new_game(1)
    state.player.gender = Gender.WOMAN
    chloe = next(islander for islander in state.islanders if islander.id == "chloe")
    chloe.relationship.affection = 40

    ids = {intent.id for intent in available_intents_for(state, "chloe")}

    assert "gossip_ring_dish_about_him" in ids
    assert "flirty_compliment_looks" not in ids
