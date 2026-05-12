"""Tests for canonical game state and snapshot invariants."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from src.game.state.models import (
    Conversation,
    ExchangeRecord,
    GameState,
    Mood,
    PlayerStats,
    clamp_relationship,
    new_game,
)
from src.game.state.snapshot import load_snapshot, save_snapshot, state_hash, state_hash_payload


def test_game_state_forbids_extra_fields() -> None:
    """Unknown state fields fail validation instead of drifting silently."""
    payload = new_game(1).model_dump(mode="json") | {"surprise": True}

    with pytest.raises(ValidationError):
        GameState.model_validate(payload)


def test_player_stats_rejects_budget_over_30() -> None:
    """The starting stat allocation cannot exceed the 30-point budget."""
    with pytest.raises(ValidationError):
        PlayerStats(charm=9, banter=9, eq=6, graft=6, loyalty=6)


def test_clamp_relationship_boundaries() -> None:
    """Relationship helpers keep values inside the legal range."""
    assert clamp_relationship(-5) == 0
    assert clamp_relationship(42) == 42
    assert clamp_relationship(101) == 100


def test_state_hash_is_stable_across_dumps() -> None:
    """The same state payload hashes identically across repeated dumps."""
    state = new_game(1)

    assert state_hash(state_hash_payload(state)) == state_hash(state_hash_payload(state))


def test_dialogue_does_not_affect_hash() -> None:
    """F2 keeps prose out of the mechanical state hash."""
    state = new_game(1)
    state.active_conversation = Conversation(
        target_id="chloe",
        started_on_turn=0,
        started_on_day=1,
        exchanges=[
            ExchangeRecord(
                turn_index=1,
                intent_id="friendly_chat_villa",
                player_dialogue="Original player line.",
                npc_dialogue="Original NPC line.",
                npc_tone="warm",
                npc_mood_after=Mood.CONTENT,
                success=True,
            )
        ],
    )
    first = state_hash(state_hash_payload(state))
    state.active_conversation.exchanges[0].player_dialogue = "Changed player line."
    state.active_conversation.exchanges[0].npc_dialogue = "Changed NPC line."

    assert state_hash(state_hash_payload(state)) == first


def test_save_load_roundtrip_preserves_hash(tmp_path: Path) -> None:
    """Snapshot save/load preserves the canonical JSON payload hash."""
    payload = new_game(1).model_dump(mode="json")
    path = tmp_path / "snapshot.json"

    save_snapshot(path, payload)
    loaded = load_snapshot(path)

    assert loaded == payload
    assert state_hash(loaded) == state_hash(payload)


def test_load_snapshot_rejects_non_object(tmp_path: Path) -> None:
    """Snapshot files must contain JSON objects."""
    path = tmp_path / "bad.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="JSON object"):
        load_snapshot(path)
