"""Opt-in tests for real narrator output."""

from __future__ import annotations

import re

import pytest

from src.game.agents.narrator import OpenAINarrator
from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.rules import MechanicalResult
from src.game.state.models import new_game


@pytest.mark.llm
@pytest.mark.parametrize(
    "result",
    [
        MechanicalResult(action=PlayerAction(kind=ActionKind.TALK, target_id="chloe"), success=True),
        MechanicalResult(action=PlayerAction(kind=ActionKind.FLIRT, target_id="chloe"), success=True),
        MechanicalResult(action=PlayerAction(kind=ActionKind.LISTEN, target_id="chloe"), success=True),
        MechanicalResult(action=PlayerAction(kind=ActionKind.BOLD_FLIRT, target_id="chloe"), success=False),
        MechanicalResult(action=PlayerAction(kind=ActionKind.LEAVE), success=True),
    ],
)
def test_narrator_output_contract(result: MechanicalResult) -> None:
    """Real narration stays bounded and visible-context-safe."""
    narrator = OpenAINarrator(budget_usd=1.0)
    prose = narrator.narrate(new_game(1), result)

    assert 20 <= len(prose.split()) <= 150
    assert not re.search(r"\d", prose)
    assert "Maya" not in prose
    assert "Liam" not in prose
