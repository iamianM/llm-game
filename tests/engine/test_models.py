"""Tests for canonical game state and snapshot invariants."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from src.game.state.models import (
    AttachmentStyle,
    BackgroundExchangeRecord,
    Conversation,
    DailyRecap,
    DailyRecapItem,
    ExchangeRecord,
    GameState,
    Gender,
    Location,
    Memory,
    Mood,
    NPCNPCConversation,
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


def test_player_stats_allows_runtime_growth_above_starting_budget() -> None:
    """Runtime stat growth can exceed the starting 30-point creation budget."""
    stats = PlayerStats(charm=9, banter=9, eq=6, graft=6, loyalty=6)

    assert stats.charm + stats.banter + stats.eq + stats.graft + stats.loyalty == 36


def test_new_game_assigns_personality_per_npc() -> None:
    """Starting islanders have deterministic personality profiles."""
    state = new_game(1)

    assert state.islanders[0].big5.extraversion == 9
    assert state.islanders[1].attachment is AttachmentStyle.ANXIOUS
    assert state.islanders[2].type_on_paper.values == ["steadiness", "depth"]


def test_new_game_assigns_canonical_gender_per_islander() -> None:
    """Starting islanders carry the H9 gender model used by intent filtering."""
    state = new_game(1)

    genders = {islander.id: islander.gender for islander in state.islanders}

    assert genders == {
        "chloe": Gender.WOMAN,
        "maya": Gender.WOMAN,
        "liam": Gender.MAN,
        "sophie": Gender.WOMAN,
        "nia": Gender.WOMAN,
        "marcus": Gender.MAN,
        "blake": Gender.MAN,
        "jordan": Gender.MAN,
    }


def test_new_game_has_8_starting_islanders() -> None:
    state = new_game(1)

    assert len(state.islanders) == 8


def test_backstory_loaded_per_islander() -> None:
    state = new_game(1)

    assert all(islander.backstory for islander in state.islanders)
    assert "primary school teacher" in next(
        islander.backstory for islander in state.islanders if islander.id == "chloe"
    )


def test_new_game_gender_balance_4_men_4_women() -> None:
    state = new_game(1)

    assert [islander.gender for islander in state.islanders].count(Gender.MAN) == 4
    assert [islander.gender for islander in state.islanders].count(Gender.WOMAN) == 4


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


def test_memory_content_does_not_affect_hash() -> None:
    """Memory prose stays out of the deterministic state hash."""
    state = new_game(1)
    state.player.memories.append(
        Memory(
            id="mem_test",
            holder_id="player",
            subject_id="chloe",
            content="Original memory text.",
            source="direct",
            formed_on_day=1,
            formed_on_turn=1,
            emotional_weight=4,
            tags=["friendly"],
        )
    )
    first = state_hash(state_hash_payload(state))
    state.player.memories[0].content = "Changed memory text."

    assert state_hash(state_hash_payload(state)) == first


def test_background_dialogue_does_not_affect_hash() -> None:
    """NPC-NPC dialogue prose stays out of the mechanical hash."""
    state = new_game(1)
    state.npc_conversations.append(
        NPCNPCConversation(
            id="npcconv_test",
            participants=["chloe", "maya"],
            location_id=Location.POOL,
            topic="Original topic.",
            started_on_turn=1,
            exchanges=[
                BackgroundExchangeRecord(
                    turn_index=1,
                    speaker_a_id="chloe",
                    speaker_b_id="maya",
                    speaker_a_line="Original line from Chloe.",
                    speaker_b_line="Original line from Maya.",
                    tone="warm",
                )
            ],
        )
    )
    first = state_hash(state_hash_payload(state))
    state.npc_conversations[0].topic = "Changed topic."
    state.npc_conversations[0].exchanges[0].speaker_a_line = "Changed Chloe line."
    state.npc_conversations[0].exchanges[0].speaker_b_line = "Changed Maya line."

    assert state_hash(state_hash_payload(state)) == first


def test_daily_recap_content_does_not_affect_hash() -> None:
    """Daily recap prose stays out of deterministic hashes."""
    state = new_game(1)

    state.daily_recaps.append(
        DailyRecap(
            day=1,
            items=[
                DailyRecapItem(
                    holder_id="chloe",
                    subject_id="maya",
                    content="Original recap.",
                    emotional_weight=8,
                    tags=["background"],
                )
            ],
        )
    )
    first = state_hash(state_hash_payload(state))
    state.daily_recaps[0].items[0].content = "Changed recap."

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
