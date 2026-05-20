"""Tests for development checkpoint persistence."""

from __future__ import annotations

import json

import pytest

from src.game.state.models import SCHEMA_VERSION, Conversation, new_game
from src.game.state.rng import SeededRng
from src.game.state.snapshot import load_checkpoint, save_named_checkpoint


def test_save_named_checkpoint_round_trips_state_and_trace(tmp_path, monkeypatch) -> None:
    state = new_game(1)
    state.active_conversation = Conversation(target_id="chloe", started_on_turn=2, started_on_day=1)
    records = [{"turn": 1, "action": {"kind": "advance_phase"}}]
    monkeypatch.chdir(tmp_path)

    path = save_named_checkpoint(state, "pre-recoupling", records, seed=1)
    loaded_state, loaded_records, seed, rng_state = load_checkpoint("pre-recoupling")

    assert path.exists()
    assert seed == 1
    assert rng_state is None
    assert loaded_records == records
    assert loaded_state.active_conversation is not None
    assert loaded_state.active_conversation.target_id == "chloe"


def test_save_named_checkpoint_can_persist_rng_state(tmp_path, monkeypatch) -> None:
    state = new_game(1)
    monkeypatch.chdir(tmp_path)

    path = save_named_checkpoint(state, "branch-point", [], seed=1, rng_state=[3, [1, 2], None])
    _loaded_state, _records, _seed, rng_state = load_checkpoint("branch-point")

    assert '"rng_state"' in path.read_text(encoding="utf-8")
    assert rng_state == [3, [1, 2], None]


def test_checkpoint_rng_state_restores_next_roll(tmp_path, monkeypatch) -> None:
    state = new_game(1)
    rng = SeededRng(1)
    rng.randint(1, 100)
    monkeypatch.chdir(tmp_path)

    save_named_checkpoint(state, "branch-point", [], seed=1, rng_state=rng.snapshot())
    _state, _records, seed, rng_state = load_checkpoint("branch-point")
    assert rng_state is not None
    restored = SeededRng.from_snapshot(seed, rng_state)

    assert restored.randint(1, 100) == rng.randint(1, 100)


def test_load_checkpoint_rejects_old_schema(tmp_path, monkeypatch) -> None:
    state = new_game(1)
    monkeypatch.chdir(tmp_path)
    path = save_named_checkpoint(state, "old", [], seed=1)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["state"]["schema_version"] = SCHEMA_VERSION - 1
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="schema_version"):
        load_checkpoint("old")
