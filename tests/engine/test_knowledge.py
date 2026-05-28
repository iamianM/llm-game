"""Knowledge foundation mechanics."""

from __future__ import annotations

from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.character_creation import create_character
from src.game.engine.gossip import share_gossip
from src.game.engine.intents import get_intent
from src.game.engine.knowledge import emit_fact_reveal
from src.game.engine.option_defaults import OPTION_TEMPLATES
from src.game.engine.rules import apply_action
from src.game.engine.turn import run_turn
from src.game.state.models import Conversation, Gender, Phase, PlayerStats, new_game
from src.game.state.phase_clock import PhaseClock
from src.game.state.rng import SeededRng
from src.game.state.traits import KnownFact


def _skip_intros(state) -> None:
    """Fast-forward past the Day-1 greeting circle for tests that begin at First Spark."""
    state.phase = Phase.MORNING
    state.phase_clock = PhaseClock(phase=Phase.MORNING.value, budget_minutes=120)
    state.intro_completed_ids = [
        islander.id for islander in state.islanders if not islander.eliminated
    ]
    state.intro_memory_created = True


def test_starting_cast_has_distinct_trait_cards() -> None:
    state = new_game(1)
    engines = [islander.trait_card.persona.secret_engine for islander in state.islanders]
    assert len(engines) == 8
    assert len(set(engines)) == 8
    assert all("hidden_secret" in islander.trait_card.core_traits for islander in state.islanders)
    assert all(len(islander.trait_card.flavor_traits) >= 6 for islander in state.islanders)


def test_opening_coupling_reveals_partner_surface_facts() -> None:
    state = new_game(1)
    create_character(
        state,
        archetype_id="heartthrob",
        gender=Gender.MAN,
        stats=PlayerStats(charm=9, banter=6, eq=5, graft=5, loyalty=5),
    )
    _skip_intros(state)
    run_turn(
        state,
        PlayerAction(kind=ActionKind.RECOUPLE, target_id="chloe"),
        SeededRng(1),
    )
    assert {"chloe.occupation", "chloe.hometown", "chloe.age"} <= set(state.player.known_facts)


def test_successful_proposal_reveals_new_partner_surface_facts() -> None:
    state = new_game(1)
    create_character(
        state,
        archetype_id="heartthrob",
        gender=Gender.MAN,
        stats=PlayerStats(charm=9, banter=6, eq=5, graft=5, loyalty=5),
    )
    _skip_intros(state)
    run_turn(state, PlayerAction(kind=ActionKind.RECOUPLE, target_id="chloe"), SeededRng(1))
    maya = next(islander for islander in state.islanders if islander.id == "maya")
    maya.relationship.affection = 100
    maya.relationship.chemistry = 100
    state.active_conversation = Conversation(target_id="maya", started_on_turn=state.turn_index, started_on_day=state.day)

    apply_action(state, PlayerAction(kind=ActionKind.PROPOSE_RECOUPLE, target_id="maya"), SeededRng(1))

    assert {"maya.occupation", "maya.hometown", "maya.age"} <= set(state.player.known_facts)


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


def test_gossip_shares_non_secret_known_fact() -> None:
    state = new_game(2)
    speaker = next(islander for islander in state.islanders if islander.id == "maya")
    speaker.known_facts.clear()
    speaker.known_facts["chloe.occupation"] = KnownFact(
        fact_key="chloe.occupation",
        value="primary school teacher",
        source="witnessed",
        learned_on_day=1,
        learned_on_turn=1,
        confidence=1.0,
        citation="test",
    )
    shared = share_gossip(state, "maya", "chloe")
    assert shared is not None
    assert shared.source == "gossip"
    assert shared.source_npc_id == "maya"
    assert shared.confidence in {0.6, 0.35}
    assert state.player.known_facts["chloe.occupation"] == shared


def test_follow_up_templates_continue_fact_reveals() -> None:
    assert OPTION_TEMPLATES["honest_vulnerable"].reveal_tier == 3
    assert OPTION_TEMPLATES["go_deeper"].reveal_tier == 3
    assert OPTION_TEMPLATES["ask_about_topic"].reveal_tier == 1
    assert OPTION_TEMPLATES["supportive_validate"].reveal_tier == 2


def test_conversation_close_emits_known_fact() -> None:
    state = new_game(1)
    target = next(islander for islander in state.islanders if islander.id == "chloe")
    target.relationship.affection = 50
    target.familiarity_with_player = 50
    rng = SeededRng(1)
    run_turn(
        state,
        PlayerAction(kind=ActionKind.START_CONVERSATION, target_id="chloe", intent_id="deep_ask_life"),
        rng,
    )
    # Facts are curated when the conversation closes; in mock mode the player
    # has to walk away explicitly because no LLM is deciding when the NPC bows
    # out.
    run_turn(state, PlayerAction(kind=ActionKind.END_CONVERSATION), rng)
    assert any(key.startswith("chloe.") for key in state.player.known_facts)
