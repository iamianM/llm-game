"""State models for scheduled events."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RelationshipDelta(BaseModel):
    """Typed relationship changes for one target."""

    model_config = ConfigDict(extra="forbid")

    affection: int = 0
    chemistry: int = 0
    trust: int = 0
    friendship: int = 0


class AudienceEntry(BaseModel):
    """One ranked audience score row."""

    model_config = ConfigDict(extra="forbid")

    rank: int
    couple: list[str]
    score: int
    is_player_couple: bool = False


class AudienceSnapshot(BaseModel):
    """End-of-day audience ranking surfaced to traces and reports."""

    model_config = ConfigDict(extra="forbid")

    day: int
    entries: list[AudienceEntry] = Field(default_factory=list)


class MinigameChoice(BaseModel):
    """One legal player choice in a minigame round.

    See ``docs/minigame-system.md`` §3.1.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    fact_value: str | None = None
    is_correct: bool = False
    distractor_source: Literal["trait_card", "other_npc", "generator", "lie"] = "generator"


class MinigameReveal(BaseModel):
    """A visible side effect surfaced after a minigame round.

    See ``docs/minigame-system.md`` §3.1.
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["fact", "chemistry_rank", "reaction", "lie_caught", "truth_told"]
    subject_id: str
    payload: dict[str, str | int] = Field(default_factory=dict)


class MinigameRound(BaseModel):
    """One scored unit inside a minigame.

    See ``docs/minigame-system.md`` §3.1.
    """

    model_config = ConfigDict(extra="forbid")

    index: int
    prompt_id: str
    target_id: str | None = None
    trait_key: str | None = None
    tier: int = 0
    mechanical: bool = True
    stem: str = ""
    choices: list[MinigameChoice] = Field(default_factory=list)
    chosen_id: str | None = None
    points: int = 0
    reveals: list[MinigameReveal] = Field(default_factory=list)


class Challenge(BaseModel):
    """One scheduled daily challenge and its mechanical result.

    Legacy single-roll fields (``result``, ``player_choice``, ``deltas``) keep
    their meaning for minigames that still resolve via the old
    ``engine/challenges.py:resolve_challenge`` path. Round-based fields
    (``rounds``, ``classification``, ``total_points``, ``audience_delta``)
    are populated by minigames migrated to the shared harness defined in
    ``docs/minigame-system.md``.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    day: int
    kind: str
    stat_tested: Literal["charm", "banter", "eq", "graft", "loyalty", "combined"]
    participants: list[str] = Field(default_factory=list)
    player_choice: str | None = None
    result: Literal["success", "failure"] | None = None
    deltas: dict[str, RelationshipDelta] = Field(default_factory=dict)
    rounds: list[MinigameRound] = Field(default_factory=list)
    current_round_index: int = 0
    total_points: int = 0
    classification: Literal["success", "partial", "failure"] | None = None
    audience_delta: int = 0


class ProducerText(BaseModel):
    """A scheduled producer text shown during the text phase."""

    model_config = ConfigDict(extra="forbid")

    id: str
    day: int
    phase: Literal["text"] = "text"
    kind: str
    body: str
    triggers: list[str] = Field(default_factory=list)


class GroupDate(BaseModel):
    """A scheduled two-NPC group date hook."""

    model_config = ConfigDict(extra="forbid")

    id: str
    participants: list[str]
    location: Literal["pool", "kitchen", "terrace", "bedroom"]
    day: int
    pending: bool = True


class QuestionBankPrompt(BaseModel):
    """One pre-generated prompt cached in the Question Bank.

    See ``docs/minigame-system.md`` §3.4.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    minigame_kind: str
    target_id: str
    trait_key: str
    tier: int = Field(ge=0, le=4)
    mechanical: bool = True
    stem: str
    correct_value: str
    distractors: list[str] = Field(default_factory=list)
    flavor_tags: list[str] = Field(default_factory=list)


class QuestionBank(BaseModel):
    """Per-season cache of pre-generated minigame prompts.

    See ``docs/minigame-system.md`` §3.4.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    bank_seed: int
    prompts: dict[str, list[QuestionBankPrompt]] = Field(default_factory=dict)


class IntrosState(BaseModel):
    """Per-NPC content generated once at the start of Day-1 intros.

    Populated by the npc_greeter agent (live mode) or left empty (mock).
    Mock-mode callers fall back to template greetings in
    ``web/lib/intros.ts`` so the UX is identical either way.
    """

    model_config = ConfigDict(extra="forbid")

    greetings: dict[str, str] = Field(default_factory=dict)
