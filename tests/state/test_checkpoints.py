"""Tests for development checkpoint persistence."""

from __future__ import annotations

from src.game.state.models import Conversation, new_game
from src.game.state.snapshot import load_checkpoint, save_named_checkpoint


def test_save_named_checkpoint_round_trips_state_and_trace(tmp_path, monkeypatch) -> None:
    state = new_game(1)
    state.active_conversation = Conversation(target_id="chloe", started_on_turn=2, started_on_day=1)
    records = [{"turn": 1, "action": {"kind": "advance_phase"}}]
    monkeypatch.chdir(tmp_path)

    path = save_named_checkpoint(state, "pre-recoupling", records, seed=1)
    loaded_state, loaded_records, seed = load_checkpoint("pre-recoupling")

    assert path.exists()
    assert seed == 1
    assert loaded_records == records
    assert loaded_state.active_conversation is not None
    assert loaded_state.active_conversation.target_id == "chloe"
