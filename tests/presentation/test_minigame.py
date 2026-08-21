"""Tests for the display-safe minigame presentation seam."""

from __future__ import annotations

import pytest

from src.game.presentation.minigame import (
    CompatibilityQuizBoardView,
    CouplesQuizBoardView,
    FinalCouplesBoardView,
    KissWedPassBoardView,
    LieDetectorBoardView,
    MinigameRoundView,
    MinigameWrapView,
    PulseRaceBoardView,
    project_minigame,
)
from src.game.state.event_models import Challenge, MinigameChoice, MinigameReveal, MinigameRound


def _choice(
    id_: str,
    label: str,
    *,
    value: str | None = None,
    correct: bool = False,
) -> MinigameChoice:
    return MinigameChoice(id=id_, label=label, fact_value=value, is_correct=correct)


def _round(
    index: int,
    *,
    chosen_id: str | None = None,
    choices: list[MinigameChoice] | None = None,
    reveals: list[MinigameReveal] | None = None,
    points: int = 0,
) -> MinigameRound:
    return MinigameRound(
        index=index,
        prompt_id=f"round-{index}",
        target_id="chloe",
        stem="Legacy combined copy is not used by the presentation adapter.",
        choices=choices or [_choice("yes", "Yes", correct=True), _choice("no", "No")],
        chosen_id=chosen_id,
        points=points,
        reveals=reveals or [],
    )


def _challenge(
    kind: str,
    rounds: list[MinigameRound],
    *,
    complete: bool = False,
    total_points: int = 0,
) -> Challenge:
    return Challenge(
        id=kind,
        day=1,
        kind=kind,
        stat_tested="eq",
        rounds=rounds,
        current_round_index=len(rounds) if complete else 0,
        classification="success" if complete else None,
        total_points=total_points,
        audience_delta=3 if complete else 0,
    )


def test_projection_keeps_narration_and_question_separate() -> None:
    challenge = _challenge("compatibility_quiz", [_round(0)])

    view = project_minigame(
        challenge,
        narration="The host turns over the first card.",
        question="What is Chloe's dream trip?",
    )

    assert isinstance(view, MinigameRoundView)
    assert view.narration == "The host turns over the first card."
    assert view.question == "What is Chloe's dream trip?"
    assert "Legacy combined copy" not in view.question


def test_compatibility_board_uses_recorded_answer_and_reaction() -> None:
    reaction = MinigameReveal(
        kind="reaction",
        subject_id="chloe",
        payload={"line": "Chloe smiles because you remembered."},
    )
    challenge = _challenge(
        "compatibility_quiz",
        [_round(0, chosen_id="yes", reveals=[reaction], points=3)],
    )
    challenge.current_round_index = 1
    challenge.rounds.append(_round(1))

    view = project_minigame(challenge, narration="Next card.", question="What comes next?")

    assert isinstance(view, MinigameRoundView)
    assert isinstance(view.board, CompatibilityQuizBoardView)
    assert view.board.latest_answer is not None
    assert view.board.latest_answer.chosen_label == "Yes"
    assert view.board.latest_answer.reaction_line == "Chloe smiles because you remembered."


def test_couples_board_uses_partner_guess_reveal() -> None:
    reveal = MinigameReveal(
        kind="fact",
        subject_id="chloe",
        payload={"partner_guess": "quiet", "partner_guess_label": "A quiet morning"},
    )
    choices = [
        _choice("quiet", "A quiet morning", value="quiet"),
        _choice("party", "A wild party", value="party"),
    ]
    challenge = _challenge(
        "couples_quiz",
        [_round(0, chosen_id="quiet", choices=choices, reveals=[reveal], points=4), _round(1)],
    )
    challenge.current_round_index = 1

    view = project_minigame(challenge, narration="Answers up.", question="Did you align?")

    assert isinstance(view.board, CouplesQuizBoardView)
    assert view.board.player_answer == "A quiet morning"
    assert view.board.partner_answer == "A quiet morning"
    assert view.board.aligned is True


def test_pulse_board_exposes_only_recorded_engine_readings() -> None:
    reveal = MinigameReveal(
        kind="chemistry_rank",
        subject_id="player",
        payload={"observer_id": "chloe", "bpm": 117, "chemistry": 82},
    )
    challenge = _challenge("heart_rate", [_round(0, reveals=[reveal])])

    view = project_minigame(challenge, narration="Monitors live.", question="Who spiked?")

    assert isinstance(view.board, PulseRaceBoardView)
    assert [reading.model_dump() for reading in view.board.readings] == [
        {"performer_id": "player", "observer_id": "chloe", "bpm": 117, "chemistry": 82}
    ]


def test_lie_detector_board_uses_recorded_roll_and_verdict() -> None:
    reveal = MinigameReveal(
        kind="lie_caught",
        subject_id="chloe",
        payload={"belief": "caught", "roll": 23, "chance": 61, "severity": "high"},
    )
    challenge = _challenge("lie_detector", [_round(0, chosen_id="no", reveals=[reveal])])
    challenge.current_round_index = 1
    challenge.rounds.append(_round(1))

    view = project_minigame(challenge, narration="The needle settles.", question="Truth or lie?")

    assert isinstance(view.board, LieDetectorBoardView)
    assert view.board.verdict == "lie_caught"
    assert view.board.needle_percent == 23


def test_kiss_wed_pass_board_uses_recorded_allocations() -> None:
    rounds = []
    for index, target in enumerate(("liam", "chloe", "maya")):
        rounds.append(
            _round(
                index,
                chosen_id=target,
                choices=[_choice(target, target.title(), value=target, correct=True)],
            )
        )
    challenge = _challenge("kiss_wed_pass", rounds, complete=True, total_points=8)

    view = project_minigame(challenge, narration="The cards are locked.", question=None)

    assert isinstance(view, MinigameWrapView)
    assert isinstance(view.board, KissWedPassBoardView)
    assert [(item.role, item.subject_id) for item in view.board.allocations] == [
        ("kiss", "liam"),
        ("wed", "chloe"),
        ("pass", "maya"),
    ]


def test_final_couples_board_uses_scored_facets_and_tally() -> None:
    rounds = [
        _round(index, chosen_id="yes", points=score)
        for index, score in enumerate((3, 4, 2, 5, 1))
    ]
    challenge = _challenge("final_couples", rounds, complete=True, total_points=15)

    view = project_minigame(challenge, narration="The final tally lands.", question=None)

    assert isinstance(view.board, FinalCouplesBoardView)
    assert [(item.facet, item.score) for item in view.board.facets] == [
        ("knowledge", 3),
        ("chemistry", 4),
        ("honesty", 2),
        ("banter", 5),
        ("audacity", 1),
    ]
    assert view.board.final_tally == 15


@pytest.mark.parametrize(
    "challenge,question,error",
    [
        (_challenge("compatibility_quiz", [_round(0)]), None, "concise question"),
        (_challenge("not_a_minigame", [_round(0)]), "Question?", "unsupported minigame kind"),
        (
            Challenge(
                id="compatibility_quiz",
                day=1,
                kind="compatibility_quiz",
                stat_tested="eq",
                rounds=[_round(0, chosen_id="yes")],
                current_round_index=1,
            ),
            None,
            "requires a classification",
        ),
    ],
)
def test_projection_rejects_incomplete_or_unknown_state(
    challenge: Challenge,
    question: str | None,
    error: str,
) -> None:
    with pytest.raises(ValueError, match=error):
        project_minigame(challenge, narration="Narration.", question=question)
