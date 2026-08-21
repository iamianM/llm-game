import pytest
from pydantic import TypeAdapter, ValidationError

from src.game.engine.challenges import MinigameKind
from src.game.presentation.daily_recap import DailyRecapItemView, DailyRecapView
from src.game.presentation.minigame import (
    CompatibilityQuizBoardView,
    MinigameRoundView,
    MinigameView,
    PulseRaceBoardView,
)


def test_daily_recap_view_limits_items_to_five() -> None:
    item = DailyRecapItemView(
        section="your_day",
        speaker_label="Chloe",
        content="You made Chloe laugh.",
        emphasis="standard",
    )

    with pytest.raises(ValidationError):
        DailyRecapView(
            day=1,
            resort_id="main",
            resort_label="Sunset Bay",
            items=[item] * 6,
        )


def test_minigame_view_uses_status_and_kind_discriminators() -> None:
    payload = {
        "status": "round",
        "kind": "compatibility_quiz",
        "round_index": 0,
        "round_count": 3,
        "narration": "The first card turns over.",
        "question": "What is Chloe's dream trip?",
        "target_id": "chloe",
        "answered_rounds": [],
        "board": {"kind": "compatibility_quiz", "latest_answer": None},
    }

    parsed = TypeAdapter(MinigameView).validate_python(payload)

    assert isinstance(parsed, MinigameRoundView)
    assert isinstance(parsed.board, CompatibilityQuizBoardView)


def test_minigame_view_rejects_a_board_for_another_kind() -> None:
    with pytest.raises(ValidationError, match="board kind must match"):
        MinigameRoundView(
            status="round",
            kind=MinigameKind.COMPATIBILITY_QUIZ,
            round_index=0,
            round_count=3,
            narration="The first card turns over.",
            question="What is Chloe's dream trip?",
            target_id="chloe",
            board=PulseRaceBoardView(kind=MinigameKind.HEART_RATE),
        )
