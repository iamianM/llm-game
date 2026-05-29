"""Tests for memory-backed gossip follow-up options."""

from __future__ import annotations

from src.game.agents.contextual_options import (
    mock_contextual_bespoke,
    mock_follow_up_menu,
    with_gossip_options,
)
from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.memory import add_memory, create_memory
from src.game.engine.turn import run_turn
from src.game.state.models import Conversation, RelationshipState, new_game
from src.game.state.rng import SeededRng
from src.game.state.snapshot import state_hash, state_hash_payload


def test_gossip_appears_when_target_has_witnessed_memory() -> None:
    """A trusted NPC can surface eligible memories as gossip wheel options."""
    state = _state_with_chloe_gossip(affection=25)

    turn = _start_chloe_conversation(state)

    assert turn.follow_up_menu is not None
    gossip_options = [
        option for option in turn.follow_up_menu.options if option.category == "gossip"
    ]
    assert len(gossip_options) == 1
    assert gossip_options[0].intent_kind.startswith("ask_gossip:")
    assert gossip_options[0].label == "Ask about Maya"


def test_gossip_pick_transfers_memory_to_player() -> None:
    """Choosing gossip records the heard memory and builds trust with the source."""
    state = _state_with_chloe_gossip(affection=25)
    rng = SeededRng(2)
    first_turn = run_turn(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_villa",
        ),
        rng,
        contextual_options=lambda *_args: mock_follow_up_menu(),
    )
    assert first_turn.follow_up_menu is not None
    gossip_option = next(
        option for option in first_turn.follow_up_menu.options if option.category == "gossip"
    )

    run_turn(
        state,
        PlayerAction(kind=ActionKind.RESPOND_WITH, intent_id=gossip_option.intent_kind),
        rng,
        contextual_options=lambda *_args: mock_follow_up_menu(),
    )

    heard = [
        memory
        for memory in state.player.memories
        if memory.source == "told_by" and memory.source_id == "chloe"
    ]
    assert len(heard) == 1
    assert heard[0].subject_id == "maya"
    assert any(tag.startswith("source_memory:") for tag in heard[0].tags)
    assert state.islanders[0].relationship.trust == 2


def test_share_gossip_pick_transfers_player_memory_to_target() -> None:
    """Choosing share gossip records a told-by-player memory on the target."""
    state = new_game(1)
    add_memory(
        state,
        create_memory(
            holder_id="player",
            subject_id="maya",
            source="witnessed",
            day=1,
            turn=1,
            weight=7,
            tags=["gossip"],
            content="Maya looked rattled after Liam pulled away.",
        ),
    )
    first_turn = run_turn(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_villa",
        ),
        SeededRng(1),
        contextual_options=lambda *_args: mock_contextual_bespoke(npc_will_leave=False),
    )
    assert first_turn.follow_up_menu is not None
    share_option = next(
        option for option in first_turn.follow_up_menu.options if option.intent_kind.startswith("share_gossip:")
    )

    run_turn(
        state,
        PlayerAction(kind=ActionKind.RESPOND_WITH, intent_id=share_option.intent_kind),
        SeededRng(1),
        contextual_options=lambda *_args: mock_follow_up_menu(),
    )

    chloe = next(islander for islander in state.islanders if islander.id == "chloe")
    assert any(
        memory.subject_id == "maya" and memory.source_id == "player"
        for memory in chloe.memories
    )


def test_share_gossip_miss_still_suppresses_reoffer() -> None:
    """A failed share records a lighter 'unconvinced' memory on the target so the
    same gossip is not re-offered (the live turn-3/turn-6 duplicate-share defect)."""
    from src.game.engine.gossip import apply_share_gossip_follow_up
    from src.game.engine.option_defaults import _player_shareable_memory

    state = new_game(1)
    memory = create_memory(
        holder_id="player",
        subject_id="maya",
        source="witnessed",
        day=1,
        turn=1,
        weight=7,
        tags=["gossip"],
        content="Maya turned the pool flirting into a kiss challenge with Jordan.",
    )
    add_memory(state, memory)
    state.active_conversation = Conversation(target_id="chloe", started_on_turn=1, started_on_day=1)

    assert _player_shareable_memory(state, "chloe") is not None

    delta = apply_share_gossip_follow_up(
        state, "chloe", f"share_gossip:{memory.id}", success=False
    )

    assert delta.trust == -1
    chloe = next(islander for islander in state.islanders if islander.id == "chloe")
    recorded = [m for m in chloe.memories if f"source_memory:{memory.id}" in m.tags]
    assert recorded and "gossip_unconvinced" in recorded[0].tags
    assert recorded[0].emotional_weight < memory.emotional_weight
    # The same gossip must no longer be surfaced to chloe.
    assert _player_shareable_memory(state, "chloe") is None


def test_gossip_locked_below_affection_threshold() -> None:
    """NPCs do not share gossip before enough affection is built."""
    state = _state_with_chloe_gossip(affection=22)

    turn = _start_chloe_conversation(state)

    assert turn.follow_up_menu is not None
    assert all(option.category != "gossip" for option in turn.follow_up_menu.options)


def test_gossip_offer_content_does_not_affect_state_hash() -> None:
    """LLM-facing gossip prose is excluded from mechanical hashes."""
    state = _state_with_chloe_gossip(affection=25)
    state.active_conversation = Conversation(
        target_id="chloe",
        started_on_turn=0,
        started_on_day=1,
        gossip_offers=[state.islanders[0].memories[0]],
    )
    first_hash = state_hash(state_hash_payload(state))

    state.active_conversation.gossip_offers[0].content = "Different wording."

    assert state_hash(state_hash_payload(state)) == first_hash


def test_gossip_injection_is_idempotent_for_recorded_replay() -> None:
    """Recorded menus that already contain gossip do not gain a second gossip option."""
    state = _state_with_chloe_gossip(affection=25)
    first_turn = _start_chloe_conversation(state)
    assert first_turn.follow_up_menu is not None

    replay_menu = with_gossip_options(first_turn.follow_up_menu, state)

    assert sum(option.category == "gossip" for option in replay_menu.options) == 1


def _state_with_chloe_gossip(*, affection: int):
    state = new_game(1)
    chloe = state.islanders[0]
    chloe.relationship = RelationshipState(affection=affection)
    chloe.memories.append(
        create_memory(
            holder_id="chloe",
            subject_id="maya",
            source="witnessed",
            day=1,
            turn=3,
            weight=6,
            tags=["background", "gossip"],
            content="Maya was flirting with Liam by the kitchen.",
        )
    )
    return state


def _start_chloe_conversation(state):
    return run_turn(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_villa",
        ),
        SeededRng(1),
        contextual_options=lambda *_args: mock_follow_up_menu(),
    )
