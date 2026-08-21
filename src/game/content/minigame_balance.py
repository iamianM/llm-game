"""Typed minigame balance data loaded from ``data/balance/minigames.yaml``.

Per-minigame models. See ``docs/systems/minigames.md`` §5 and each minigame
spec under ``docs/systems/minigames/`` for what the numbers mean.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field


class RecoveryFloor(BaseModel):
    model_config = ConfigDict(extra="forbid")
    audience_threshold: int = Field(ge=0, le=100)
    partial_audience_bonus: int = Field(ge=0)
    failure_audience_dampener: int = Field(ge=0)


# --- Compatibility Quiz ---


class CompatQuizPoints(BaseModel):
    model_config = ConfigDict(extra="forbid")
    correct_tier1: int
    correct_tier2: int
    correct_tier3: int
    correct_tier4: int
    correct_flavor: int
    incorrect: int


class _Thresholds(BaseModel):
    model_config = ConfigDict(extra="forbid")
    success: int
    partial: int


class _ThreeAudience(BaseModel):
    model_config = ConfigDict(extra="forbid")
    success: int
    partial: int
    failure: int


class CompatibilityQuizBalance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rounds: int = Field(ge=1)
    per_round_points: CompatQuizPoints
    thresholds: _Thresholds
    audience: _ThreeAudience


# --- Pulse Race ---


class PulseRacePoints(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lean_in: int
    play_cool: int
    apologize: int


class PulseRaceThresholds(BaseModel):
    model_config = ConfigDict(extra="forbid")
    surprise_chemistry: int


class PulseRaceAudience(BaseModel):
    model_config = ConfigDict(extra="forbid")
    success: int
    partial: int
    failure: int
    lean_in_bonus: int
    apologize_penalty: int


class PulseRaceBalance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reaction_rounds: int = Field(ge=0)
    thresholds: PulseRaceThresholds
    per_round_points: PulseRacePoints
    audience: PulseRaceAudience


# --- Kiss Wed Pass ---


class KissWedPassPoints(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kiss_partner: int
    kiss_chemistry: int
    kiss_friend: int
    wed_partner: int
    wed_chemistry: int
    wed_friend: int
    pass_rival: int
    pass_friend: int
    pass_partner: int


class KissWedPassAudience(BaseModel):
    model_config = ConfigDict(extra="forbid")
    success: int
    partial: int
    failure: int
    pass_partner_extra: int


class KissWedPassBalance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rounds: int = Field(ge=1)
    per_round_points: KissWedPassPoints
    thresholds: _Thresholds
    audience: KissWedPassAudience


# --- Couples Quiz (Couples Quiz) ---


class CouplesQuizPoints(BaseModel):
    model_config = ConfigDict(extra="forbid")
    both_match: int
    one_correct: int
    mismatch: int


class CouplesQuizAudience(BaseModel):
    model_config = ConfigDict(extra="forbid")
    success: int
    partial: int
    failure: int
    streak_three_mismatch_penalty: int


class CouplesQuizBalance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rounds: int = Field(ge=1)
    per_round_points: CouplesQuizPoints
    thresholds: _Thresholds
    audience: CouplesQuizAudience


# --- Lie Detector ---


class LieDetectorPoints(BaseModel):
    model_config = ConfigDict(extra="forbid")
    truth_verified: int
    truth_unverified: int
    lie_undetected: int
    lie_caught: int
    lie_caught_high_stakes_extra: int


class LieDetectorAudience(BaseModel):
    model_config = ConfigDict(extra="forbid")
    success: int
    partial: int
    failure: int
    truth_unverified_bonus: int


class LieDetectorDetection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_chance: int
    familiarity_factor_max: int
    visibility_factor_max: int
    floor: int
    ceiling: int


class LieDetectorBalance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rounds: int = Field(ge=1)
    per_round_points: LieDetectorPoints
    thresholds: _Thresholds
    audience: LieDetectorAudience
    detection: LieDetectorDetection


# --- Final Couples ---


class FinalCouplesWeights(BaseModel):
    model_config = ConfigDict(extra="forbid")
    knowledge: int
    chemistry: int
    honesty: int
    banter: int
    audacity: int


class FinalCouplesPoints(BaseModel):
    model_config = ConfigDict(extra="forbid")
    knowledge_correct: int
    knowledge_incorrect: int
    chemistry_high: int
    chemistry_low: int
    honesty_truth: int
    honesty_lie_undetected: int
    honesty_lie_caught: int
    banter_match: int
    banter_miss: int
    audacity_rival_callout: int
    audacity_friend_callout: int
    audacity_partner_callout: int


class FinalCouplesBalance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rounds: int = Field(ge=1)
    facet_weights: FinalCouplesWeights
    per_round_points: FinalCouplesPoints
    thresholds: _Thresholds
    audience: _ThreeAudience


# --- Top-level ---


class MinigameBalance(BaseModel):
    """Top-level minigame balance contract."""

    model_config = ConfigDict(extra="forbid")

    recovery_floor: RecoveryFloor
    compatibility_quiz: CompatibilityQuizBalance
    heart_rate: PulseRaceBalance
    kiss_wed_pass: KissWedPassBalance
    couples_quiz: CouplesQuizBalance
    lie_detector: LieDetectorBalance
    final_couples: FinalCouplesBalance


_PATH = Path("data/balance/minigames.yaml")
_CACHE: MinigameBalance | None = None


def load_minigame_balance() -> MinigameBalance:
    global _CACHE
    if _CACHE is None:
        _CACHE = MinigameBalance.model_validate(
            yaml.safe_load(_PATH.read_text(encoding="utf-8"))
        )
    return _CACHE


def reset_balance_cache() -> None:
    global _CACHE
    _CACHE = None
