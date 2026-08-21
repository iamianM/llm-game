"""Typed display-safe minigame projection contracts."""

from __future__ import annotations

from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.game.engine.challenges import MinigameKind

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

    subject_id: str
    bpm: int | None = Field(default=None, ge=0)
    rank: int | None = Field(default=None, ge=1)


class PulseRaceBoardView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal[MinigameKind.HEART_RATE]
    readings: list[PulseReadingView] = Field(default_factory=list)


class LieDetectorBoardView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal[MinigameKind.LIE_DETECTOR]
    subject_id: str | None = None
    verdict: Literal["truth_told", "lie_caught", "lie_believed"] | None = None
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
