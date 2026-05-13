"""Personality state models."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class AttachmentStyle(StrEnum):
    """How an islander responds to intimacy and setbacks."""

    SECURE = "secure"
    ANXIOUS = "anxious"
    AVOIDANT = "avoidant"
    FEARFUL = "fearful"


class Big5(BaseModel):
    """Fixed OCEAN personality scores for an islander."""

    model_config = ConfigDict(extra="forbid")

    openness: int = Field(ge=1, le=10)
    conscientiousness: int = Field(ge=1, le=10)
    extraversion: int = Field(ge=1, le=10)
    agreeableness: int = Field(ge=1, le=10)
    neuroticism: int = Field(ge=1, le=10)


class TypeOnPaper(BaseModel):
    """Hidden preferences revealed as familiarity grows."""

    model_config = ConfigDict(extra="forbid")

    physical_type: str
    personality_type: list[str]
    values: list[str]
    dealbreakers: list[str]
