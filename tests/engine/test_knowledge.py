"""Knowledge foundation mechanics."""

from __future__ import annotations

from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.gossip import share_gossip
from src.game.engine.intents import get_intent
from src.game.engine.knowledge import emit_fact_reveal
from src.game.engine.rules import apply_action
from src.game.engine.turn import run_turn
from src.game.state.models import Phase, new_game
from src.game.state.rng import SeededRng
from src.game.state.traits import KnownFact


def test_starting_cast_has_distinct_trait_cards() -> None:
    state = new_game(1)
    engines = [islander.trait_card.persona.secret_engine for islander in state.islanders]
    assert len(engines) == 8
    assert len(set(engines)) == 8
    assert all("hidden_secret" in islander.trait_card.core_traits for islander in state.islanders)


def test_intro_reveals_tier_one_known_facts() -> None:
    state = new_game(1)
    state.phase = Phase.INTROS
    apply_action(
        state,
        PlayerAction(kind=ActionKind.INTRODUCE_TO, target_id="maya", intent_id="intro_deep"),
        SeededRng(1),
    )
    assert state.player.known_facts["maya.occupation"].source == "direct"
    assert state.player.known_facts["maya.hometown"].confidence == 1.0


def test_deep_intent_reveals_tier_three_fact_at_familiarity() -> None:
    state = new_game(1)
    target = next(islander for islander in state.islanders if islander.id == "chloe")
    target.familiarity_with_player = 50
    fact = emit_fact_reveal(state, target, get_intent("deep_ask_life"))
    assert fact is not None
    assert fact.fact_key.startswith("chloe.")
    assert fact.fact_key in state.player.known_facts


def test_gossip_distortion_never_shares_hidden_secret() -> None:
    state = new_game(1)
    speaker = next(islander for islander in state.islanders if islander.id == "maya")
    speaker.known_facts.clear()
    speaker.known_facts["chloe.hidden_secret"] = KnownFact(
        fact_key="chloe.hidden_secret",
        value="secret",
        source="direct",
        learned_on_day=1,
        learned_on_turn=1,
        confidence=1.0,
        citation="test",
    )
    assert share_gossip(state, "maya", "chloe") is None


def test_conversation_close_emits_known_fact() -> None:
    state = new_game(1)
    target = next(islander for islander in state.islanders if islander.id == "chloe")
    target.relationship.affection = 50
    target.familiarity_with_player = 50
    action = PlayerAction(kind=ActionKind.START_CONVERSATION, target_id="chloe", intent_id="deep_ask_life")
    run_turn(state, action, SeededRng(1))
    assert any(key.startswith("chloe.") for key in state.player.known_facts)
