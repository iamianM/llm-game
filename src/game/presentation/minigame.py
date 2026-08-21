"""Typed display-safe minigame projection contracts and adapter."""

from __future__ import annotations

from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.game.engine.challenges import MinigameKind
from src.game.engine.final_couples import FACETS
from src.game.state.event_models import Challenge, MinigameRound

MinigameClassification = Literal["success", "partial", "failure"]


class AnsweredMinigameRoundView(BaseModel):
    """Display-safe outcome of one completed minigame round."""

    model_config = ConfigDict(extra="forbid")

    round_index: int = Field(ge=0)
    chosen_label: str | None
    correct_label: str | None
    is_correct: bool
    points: int
    reaction_line: str | None


class CompatibilityQuizBoardView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal[MinigameKind.COMPATIBILITY_QUIZ]
    latest_answer: AnsweredMinigameRoundView | None = None


class CouplesQuizBoardView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal[MinigameKind.COUPLES_QUIZ]
    player_answer: str | None = None
    partner_answer: str | None = None
    aligned: bool | None = None


class PulseReadingView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    performer_id: str
    observer_id: str
    bpm: int = Field(ge=0)
    chemistry: int = Field(ge=0, le=100)


class PulseRaceBoardView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal[MinigameKind.HEART_RATE]
    readings: list[PulseReadingView] = Field(default_factory=list)


class LieDetectorBoardView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal[MinigameKind.LIE_DETECTOR]
    subject_id: str | None = None
    verdict: Literal["truth_told", "truth_suspected", "lie_caught", "lie_believed"] | None = None
    needle_percent: int | None = Field(default=None, ge=0, le=100)


class AllocationView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["kiss", "wed", "pass"]
    subject_id: str


class KissWedPassBoardView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal[MinigameKind.KISS_WED_PASS]
    allocations: list[AllocationView] = Field(default_factory=list)


class FacetScoreView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    facet: str
    score: int


class FinalCouplesBoardView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal[MinigameKind.FINAL_COUPLES]
    facets: list[FacetScoreView] = Field(default_factory=list)
    final_tally: int | None = None


MinigameBoardView: TypeAlias = Annotated[
    CompatibilityQuizBoardView
    | CouplesQuizBoardView
    | PulseRaceBoardView
    | LieDetectorBoardView
    | KissWedPassBoardView
    | FinalCouplesBoardView,
    Field(discriminator="kind"),
]


class MinigameRoundView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["round"]
    kind: MinigameKind
    round_index: int = Field(ge=0)
    round_count: int = Field(ge=1)
    narration: str
    question: str = Field(min_length=1)
    target_id: str | None
    answered_rounds: list[AnsweredMinigameRoundView] = Field(default_factory=list)
    board: MinigameBoardView

    @model_validator(mode="after")
    def board_matches_kind(self) -> MinigameRoundView:
        if self.board.kind != self.kind:
            raise ValueError("minigame board kind must match the round kind")
        return self


class MinigameWrapView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["wrap"]
    kind: MinigameKind
    round_count: int = Field(ge=1)
    narration: str
    classification: MinigameClassification
    total_points: int
    audience_delta: int
    answered_rounds: list[AnsweredMinigameRoundView] = Field(default_factory=list)
    board: MinigameBoardView

    @model_validator(mode="after")
    def board_matches_kind(self) -> MinigameWrapView:
        if self.board.kind != self.kind:
            raise ValueError("minigame board kind must match the wrap kind")
        return self


MinigameView: TypeAlias = Annotated[
    MinigameRoundView | MinigameWrapView,
    Field(discriminator="status"),
]


def project_minigame(
    challenge: Challenge,
    *,
    narration: str,
    question: str | None,
) -> MinigameView:
    """Project canonical challenge state through the minigame presentation seam.

    The caller supplies narration and the concise question as separate typed
    values. This adapter never extracts a question from prose. Legal choices
    remain outside this view in ``available_actions``.
    """

    try:
        kind = MinigameKind(challenge.kind)
    except ValueError as exc:
        raise ValueError(f"unsupported minigame kind: {challenge.kind}") from exc
    if not challenge.rounds:
        raise ValueError("minigame projection requires at least one round")
    if challenge.current_round_index > len(challenge.rounds):
        raise ValueError("minigame round index exceeds the recorded round count")

    answered = [_answered_round(round_) for round_ in challenge.rounds if round_.chosen_id is not None]
    board = _board_view(challenge, kind, answered)
    if challenge.current_round_index < len(challenge.rounds):
        if question is None or not question.strip():
            raise ValueError("active minigame projection requires a concise question")
        return MinigameRoundView(
            status="round",
            kind=kind,
            round_index=challenge.current_round_index,
            round_count=len(challenge.rounds),
            narration=narration,
            question=question,
            target_id=challenge.rounds[challenge.current_round_index].target_id,
            answered_rounds=answered,
            board=board,
        )

    if question is not None:
        raise ValueError("completed minigame projection cannot carry a stale question")
    if challenge.classification is None:
        raise ValueError("completed minigame projection requires a classification")
    return MinigameWrapView(
        status="wrap",
        kind=kind,
        round_count=len(challenge.rounds),
        narration=narration,
        classification=challenge.classification,
        total_points=challenge.total_points,
        audience_delta=challenge.audience_delta,
        answered_rounds=answered,
        board=board,
    )


def _answered_round(round_: MinigameRound) -> AnsweredMinigameRoundView:
    chosen = next((choice for choice in round_.choices if choice.id == round_.chosen_id), None)
    if chosen is None:
        raise ValueError(f"round {round_.index} records an unknown chosen_id")
    correct = next((choice for choice in round_.choices if choice.is_correct), None)
    reaction_line = next(
        (
            str(reveal.payload["line"])
            for reveal in round_.reveals
            if reveal.kind == "reaction" and "line" in reveal.payload
        ),
        None,
    )
    return AnsweredMinigameRoundView(
        round_index=round_.index,
        chosen_label=chosen.label,
        correct_label=None if correct is None else correct.label,
        is_correct=chosen.is_correct,
        points=round_.points,
        reaction_line=reaction_line,
    )


def _board_view(
    challenge: Challenge,
    kind: MinigameKind,
    answered: list[AnsweredMinigameRoundView],
) -> MinigameBoardView:
    if kind is MinigameKind.COMPATIBILITY_QUIZ:
        return CompatibilityQuizBoardView(kind=kind, latest_answer=answered[-1] if answered else None)
    if kind is MinigameKind.COUPLES_QUIZ:
        return _couples_quiz_board(challenge, kind)
    if kind is MinigameKind.HEART_RATE:
        return _pulse_race_board(challenge, kind)
    if kind is MinigameKind.LIE_DETECTOR:
        return _lie_detector_board(challenge, kind)
    if kind is MinigameKind.KISS_WED_PASS:
        return _kiss_wed_pass_board(challenge, kind)
    if kind is MinigameKind.FINAL_COUPLES:
        return _final_couples_board(challenge, kind)
    raise AssertionError(f"unhandled minigame kind: {kind}")


def _couples_quiz_board(
    challenge: Challenge,
    kind: Literal[MinigameKind.COUPLES_QUIZ],
) -> CouplesQuizBoardView:
    answered = [round_ for round_ in challenge.rounds if round_.chosen_id is not None]
    if not answered:
        return CouplesQuizBoardView(kind=kind)
    latest = answered[-1]
    chosen = next(choice for choice in latest.choices if choice.id == latest.chosen_id)
    reveal = next(
        (
            item
            for item in latest.reveals
            if item.kind == "fact" and "partner_guess_label" in item.payload
        ),
        None,
    )
    partner_answer = (
        str(reveal.payload["partner_guess_label"])
        if reveal is not None
        else next((choice.label for choice in latest.choices if choice.is_correct), None)
    )
    aligned = (
        chosen.fact_value == reveal.payload.get("partner_guess")
        if reveal is not None
        else chosen.is_correct
    )
    return CouplesQuizBoardView(
        kind=kind,
        player_answer=chosen.label,
        partner_answer=partner_answer,
        aligned=aligned,
    )


def _pulse_race_board(
    challenge: Challenge,
    kind: Literal[MinigameKind.HEART_RATE],
) -> PulseRaceBoardView:
    readings: list[PulseReadingView] = []
    for round_ in challenge.rounds:
        for reveal in round_.reveals:
            if reveal.kind != "chemistry_rank":
                continue
            readings.append(
                PulseReadingView(
                    performer_id=reveal.subject_id,
                    observer_id=str(reveal.payload["observer_id"]),
                    bpm=int(reveal.payload["bpm"]),
                    chemistry=int(reveal.payload["chemistry"]),
                )
            )
    return PulseRaceBoardView(kind=kind, readings=readings)


def _lie_detector_board(
    challenge: Challenge,
    kind: Literal[MinigameKind.LIE_DETECTOR],
) -> LieDetectorBoardView:
    for round_ in reversed(challenge.rounds):
        for reveal in reversed(round_.reveals):
            if reveal.kind not in {"truth_told", "lie_caught"}:
                continue
            belief = str(reveal.payload["belief"])
            if reveal.kind == "truth_told":
                verdict = "truth_suspected" if belief == "suspected" else "truth_told"
            else:
                verdict = "lie_caught" if belief == "caught" else "lie_believed"
            return LieDetectorBoardView(
                kind=kind,
                subject_id=reveal.subject_id,
                verdict=verdict,
                needle_percent=int(reveal.payload["roll"]),
            )
    return LieDetectorBoardView(kind=kind)


def _kiss_wed_pass_board(
    challenge: Challenge,
    kind: Literal[MinigameKind.KISS_WED_PASS],
) -> KissWedPassBoardView:
    roles: tuple[Literal["kiss", "wed", "pass"], ...] = ("kiss", "wed", "pass")
    allocations: list[AllocationView] = []
    for round_ in challenge.rounds:
        if round_.chosen_id is None:
            continue
        chosen = next(choice for choice in round_.choices if choice.id == round_.chosen_id)
        if chosen.fact_value is None:
            raise ValueError("Kiss Wed Pass choice requires a target id")
        allocations.append(AllocationView(role=roles[round_.index], subject_id=chosen.fact_value))
    return KissWedPassBoardView(kind=kind, allocations=allocations)


def _final_couples_board(
    challenge: Challenge,
    kind: Literal[MinigameKind.FINAL_COUPLES],
) -> FinalCouplesBoardView:
    facets = []
    if challenge.classification is not None:
        facets = [
            FacetScoreView(facet=FACETS[round_.index], score=round_.points)
            for round_ in challenge.rounds
            if round_.chosen_id is not None
        ]
    return FinalCouplesBoardView(
        kind=kind,
        facets=facets,
        final_tally=challenge.total_points if challenge.classification is not None else None,
    )
