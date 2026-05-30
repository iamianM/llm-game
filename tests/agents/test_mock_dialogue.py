"""Invariants for the deterministic demo-mode dialogue pool.

Demo mode is the default browser experience when no LLM key is configured, so
these mock lines are the first — and often only — conversation a player sees.
The properties tested here are the contract the report tooling and replay
parity rely on: determinism, mock-detectability, name interpolation, and just
enough rotation that repeated play does not feel word-for-word identical.
"""

from __future__ import annotations

import pytest

from src.game.agents.islander_voice import VALID_TONES, mock_islander_voice
from src.game.agents.mock_dialogue import (
    _DEFAULT,
    _LINES,
    MOCK_NPC_LINES,
    Tone,
    mock_exchange_fields,
)
from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.results import MechanicalResult
from src.game.state.models import Mood, new_game

# Every dialogue slot the pool exposes, including the catch-all fallback.
_ALL_LINES = [line for table in (*_LINES.values(), _DEFAULT) for line in table.values()]


def test_player_and_npc_tuples_are_index_matched() -> None:
    """A reply at npc[i] must answer the opener at player[i], so both tuples
    must be the same length or the roll index could pair mismatched lines."""
    for line in _ALL_LINES:
        assert len(line.player) == len(line.npc)
        assert len(line.player) >= 2  # at least two phrasings, or there is no rotation


def test_mock_npc_lines_covers_every_reply() -> None:
    """Report tooling flags a trace as mock by membership in MOCK_NPC_LINES, so
    every reply the pool can emit must appear in it."""
    for line in _ALL_LINES:
        for reply in line.npc:
            assert reply in MOCK_NPC_LINES


@pytest.mark.parametrize("category", [*_LINES.keys(), None, "totally-unknown-category"])
@pytest.mark.parametrize("success", [True, False])
def test_exchange_is_deterministic(category: str | None, success: bool) -> None:
    """Same state -> same line is required for replay parity."""
    first = mock_exchange_fields(category=category, success=success, target_name="Chloe", roll=3)
    second = mock_exchange_fields(category=category, success=success, target_name="Chloe", roll=3)
    assert first == second


@pytest.mark.parametrize("category", list(_LINES.keys()))
@pytest.mark.parametrize("success", [True, False])
def test_roll_rotates_to_a_distinct_pair(category: str, success: bool) -> None:
    """Two different rolls should be able to surface two different (player, npc)
    pairs, so flirting twice does not return word-for-word the same reply."""
    pairs = {
        mock_exchange_fields(category=category, success=success, target_name="Chloe", roll=roll)[:2]
        for roll in range(4)
    }
    assert len(pairs) >= 2


def test_player_line_interpolates_target_name() -> None:
    """The opener carries a {name} slot; the literal placeholder must never leak."""
    player, _npc, _tone, _mood = mock_exchange_fields(
        category="flirty", success=True, target_name="Marisol", roll=0
    )
    assert "Marisol" in player
    assert "{name}" not in player


def test_every_reply_is_detectable_and_well_typed() -> None:
    """Returned tone is always a valid Exchange tone and the reply is a mock sentinel."""
    for category in (*_LINES.keys(), None):
        for success in (True, False):
            for roll in range(4):
                _player, npc, tone, mood = mock_exchange_fields(
                    category=category, success=success, target_name="Chloe", roll=roll
                )
                assert npc in MOCK_NPC_LINES
                assert tone in VALID_TONES
                assert isinstance(mood, Mood)
                assert isinstance(tone, str)  # Tone is a Literal[str] alias
                _ = Tone  # exported alias is importable for callers


def test_none_roll_is_treated_as_zero() -> None:
    """A missing roll must not crash; it falls back to the first phrasing."""
    with_none = mock_exchange_fields(category="deep", success=True, target_name="Chloe", roll=None)
    with_zero = mock_exchange_fields(category="deep", success=True, target_name="Chloe", roll=0)
    assert with_none == with_zero


def test_mock_islander_voice_returns_valid_exchange() -> None:
    """End-to-end: the agent entry point yields an in-character, mock-detectable
    exchange that names the target and carries a valid tone/mood."""
    state = new_game(1)
    result = MechanicalResult(
        action=PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="flirty_compliment_looks",
        ),
        success=True,
        tags=["flirty"],
        roll=1,
    )

    exchange = mock_islander_voice(state, result)

    assert "Chloe" in exchange.player_dialogue
    assert exchange.npc_dialogue in MOCK_NPC_LINES
    assert exchange.npc_tone in VALID_TONES
    assert isinstance(exchange.npc_mood_after, Mood)
