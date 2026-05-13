"""Pydantic models for canonical game state."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.game.state.autonomy import PendingNPCSummon as PendingNPCSummon
from src.game.state.casa import CasaAmorState as CasaAmorState
from src.game.state.casa import CasaDecision as CasaDecision
from src.game.state.casa import VillaName as VillaName
from src.game.state.event_models import (
    AudienceEntry as AudienceEntry,
)
from src.game.state.event_models import (
    AudienceSnapshot as AudienceSnapshot,
)
from src.game.state.event_models import (
    Challenge as Challenge,
)
from src.game.state.event_models import (
    GroupDate as GroupDate,
)
from src.game.state.event_models import (
    ProducerText as ProducerText,
)
from src.game.state.event_models import (
    RelationshipDelta as RelationshipDelta,
)
from src.game.state.memory import Memory as Memory
from src.game.state.memory import MemoryBatch as MemoryBatch
from src.game.state.memory import MemoryDraft as MemoryDraft
from src.game.state.personality import AttachmentStyle as AttachmentStyle
from src.game.state.personality import Big5 as Big5
from src.game.state.personality import TypeOnPaper as TypeOnPaper
from src.game.state.phase_clock import PhaseClock as PhaseClock

SCHEMA_VERSION = 17


class Phase(StrEnum):
    """The day clock for the playable v0 loop."""

    MORNING = "morning"
    CHALLENGE = "challenge"
    AFTERNOON = "afternoon"
    TEXT = "text"
    EVENING = "evening"
    COMPLETE = "complete"


class RunOutcome(StrEnum):
    WON_AS_COUPLE = "won_as_couple"
    RUNNER_UP_COUPLE = "runner_up_couple"
    LEFT_SINGLE = "left_single"
    ELIMINATED = "eliminated"


class Location(StrEnum):
    POOL = "pool"
    KITCHEN = "kitchen"
    TERRACE = "terrace"
    BEDROOM = "bedroom"
    HIDEAWAY = "hideaway"
    CASA_POOL = "casa_pool"
    CASA_KITCHEN = "casa_kitchen"
    CASA_TERRACE = "casa_terrace"


class Mood(StrEnum):
    HAPPY = "happy"
    FLIRTY = "flirty"
    UPSET = "upset"
    ANXIOUS = "anxious"
    ANGRY = "angry"
    CONTENT = "content"


class Gender(StrEnum):
    """Binary villa gender used for attraction and same-sex dynamics in v0."""

    MAN = "man"
    WOMAN = "woman"


class PlayerStats(BaseModel):
    """Five fixed player stats with the A3 30-point budget."""

    model_config = ConfigDict(extra="forbid")

    charm: int = Field(ge=3, le=9)
    banter: int = Field(ge=3, le=9)
    eq: int = Field(ge=3, le=9)
    graft: int = Field(ge=3, le=9)
    loyalty: int = Field(ge=3, le=9)

    @model_validator(mode="after")
    def validate_budget(self) -> PlayerStats:
        """Reject stat allocations above the starting 30-point budget."""
        total = self.charm + self.banter + self.eq + self.graft + self.loyalty
        if total > 30:
            raise ValueError("player stat total cannot exceed 30")
        return self


class CharacterCreation(BaseModel):
    """Audited starting character selection."""

    model_config = ConfigDict(extra="forbid")

    archetype_id: str
    gender: Gender
    stats: PlayerStats
    rerolled: bool = False


class PlayerState(BaseModel):
    """Player identity and stats."""

    model_config = ConfigDict(extra="forbid")

    id: str = "player"
    name: str = "You"
    gender: Gender = Gender.MAN
    stats: PlayerStats
    archetype_id: str = "balanced"
    character_created: bool = True
    reroll_used: bool = False
    public_perception: int = Field(default=50, ge=0, le=100)
    eliminated: bool = False
    memories: list[Memory] = Field(default_factory=list)


class RelationshipState(BaseModel):
    """Player-facing relationship state for one islander."""

    model_config = ConfigDict(extra="forbid")

    affection: int = Field(default=0, ge=0, le=100)
    chemistry: int = Field(default=0, ge=0, le=100)
    trust: int = Field(default=0, ge=0, le=100)
    friendship: int = Field(default=0, ge=0, le=100)


class IslanderState(BaseModel):
    """Minimal NPC Islander state."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    gender: Gender
    archetype: str
    location_id: Location
    relationship: RelationshipState = Field(default_factory=RelationshipState)
    public_perception: int = Field(default=50, ge=0, le=100)
    eliminated: bool = False
    mood: Mood = Mood.CONTENT
    big5: Big5
    attachment: AttachmentStyle
    type_on_paper: TypeOnPaper
    familiarity_with_player: int = Field(default=0, ge=0, le=100)
    memories: list[Memory] = Field(default_factory=list)


class Couple(BaseModel):
    model_config = ConfigDict(extra="forbid")

    partner_a_id: str
    partner_b_id: str
    formed_on_day: int
    has_used_hideaway: bool = False
    last_steal_attempt_chance: int | None = None


class HideawayState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    used_on_day: int | None = None
    partner_id: str | None = None
    deltas_applied: bool = False


class FollowUpOption(BaseModel):
    """One contextual follow-up choice in an open conversation."""

    model_config = ConfigDict(extra="forbid")

    label: str
    category: Literal[
        "friendly",
        "flirty",
        "deep",
        "banter",
        "gossip",
        "supportive",
        "bromance",
        "gossip_ring",
        "exit",
    ]
    intent_kind: str
    stat_used: Literal["charm", "banter", "eq", "graft", "loyalty"] | None
    risk: Literal["safe", "low", "medium", "high"]
    tone: str
    unlock_threshold: dict[str, int] | None = None


class FollowUpMenu(BaseModel):
    """Contextual menu generated after an NPC reply."""

    model_config = ConfigDict(extra="forbid")

    options: list[FollowUpOption] = Field(min_length=2, max_length=4)
    npc_will_leave: bool
    npc_exit_line: str | None = None


class NPCInterruption(BaseModel):
    """An NPC walking up to interrupt the player's active conversation."""

    model_config = ConfigDict(extra="forbid")

    interrupter_id: str
    reason: Literal["jealous", "has_gossip", "drawn_to_topic", "needs_to_talk"]
    urgency: Literal["polite", "insistent", "dramatic"]


class ExchangeRecord(BaseModel):
    """One exchange retained inside an active conversation."""

    model_config = ConfigDict(extra="forbid")

    turn_index: int
    intent_id: str
    player_dialogue: str
    npc_dialogue: str
    npc_tone: str
    npc_mood_after: Mood
    success: bool
    tags: list[str] = Field(default_factory=list)
    relationship_deltas: dict[str, RelationshipDelta] = Field(default_factory=dict)


class BackgroundExchangeRecord(BaseModel):
    """One NPC-NPC exchange retained in a background conversation."""

    model_config = ConfigDict(extra="forbid")

    turn_index: int
    speaker_a_id: str
    speaker_b_id: str
    speaker_a_line: str
    speaker_b_line: str
    tone: str


class Conversation(BaseModel):
    """A single active one-on-one conversation."""

    model_config = ConfigDict(extra="forbid")

    target_id: str
    started_on_turn: int
    started_on_day: int
    exchanges: list[ExchangeRecord] = Field(default_factory=list)
    accumulated_tags: list[str] = Field(default_factory=list)
    status: Literal["open", "closing", "closed"] = "open"
    departure_probability_last: int = 0
    pending_options: FollowUpMenu | None = None
    pending_interruption: NPCInterruption | None = None
    gossip_offers: list[Memory] = Field(default_factory=list)


class NPCNPCConversation(BaseModel):
    """A persistent off-screen conversation between two NPC islanders."""

    model_config = ConfigDict(extra="forbid")

    id: str
    participants: list[str] = Field(min_length=2, max_length=2)
    location_id: Location
    topic: str
    started_on_turn: int
    exchanges: list[BackgroundExchangeRecord] = Field(default_factory=list)
    status: Literal["active", "ending", "closed"] = "active"


class GameState(BaseModel):
    """Canonical deterministic game state."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = SCHEMA_VERSION
    seed: int
    turn_index: int = 0
    day: int = 1
    phase: Phase = Phase.MORNING
    phase_clock: PhaseClock = Field(default_factory=lambda: PhaseClock(phase=Phase.MORNING.value, budget_minutes=120))
    location_id: Location = Location.POOL
    villa: VillaName = VillaName.MAIN
    player: PlayerState
    islanders: list[IslanderState]
    couples: list[Couple] = Field(default_factory=list)
    active_conversation: Conversation | None = None
    npc_conversations: list[NPCNPCConversation] = Field(default_factory=list)
    pending_npc_summon: PendingNPCSummon | None = None
    character_creation: CharacterCreation | None = None
    audience_snapshots: list[AudienceSnapshot] = Field(default_factory=list)
    pending_challenge: Challenge | None = None
    pending_text: ProducerText | None = None
    pending_group_date: GroupDate | None = None
    hideaway: HideawayState = Field(default_factory=HideawayState)
    casa_amor_state: CasaAmorState | None = None
    outcome: RunOutcome | None = None

    @property
    def is_terminal(self) -> bool:
        return self.phase is Phase.COMPLETE or self.outcome is not None


def clamp_relationship(value: int) -> int:
    return max(0, min(100, value))


def new_game(seed: int, *, player_stats: PlayerStats | None = None) -> GameState:
    return GameState(
        seed=seed,
        player=PlayerState(
            stats=player_stats
            if player_stats is not None
            else PlayerStats(charm=6, banter=6, eq=6, graft=6, loyalty=6)
        ),
        islanders=[
            IslanderState(
                id="chloe",
                name="Chloe",
                gender=Gender.WOMAN,
                archetype="sweetheart",
                location_id=Location.POOL,
                relationship=RelationshipState(affection=10),
                big5=Big5(openness=7, conscientiousness=6, extraversion=9, agreeableness=8, neuroticism=4),
                attachment=AttachmentStyle.SECURE,
                type_on_paper=TypeOnPaper(
                    physical_type="warm smiles and kind eyes",
                    personality_type=["warm", "confident"],
                    values=["loyalty", "honesty"],
                    dealbreakers=["arrogance"],
                ),
            ),
            IslanderState(
                id="maya",
                name="Maya",
                gender=Gender.WOMAN,
                archetype="joker",
                location_id=Location.KITCHEN,
                relationship=RelationshipState(affection=8),
                big5=Big5(openness=8, conscientiousness=5, extraversion=9, agreeableness=5, neuroticism=6),
                attachment=AttachmentStyle.ANXIOUS,
                type_on_paper=TypeOnPaper(
                    physical_type="expressive people with bright energy",
                    personality_type=["funny", "attentive"],
                    values=["humor", "attention"],
                    dealbreakers=["neglect"],
                ),
            ),
            IslanderState(
                id="liam",
                name="Liam",
                gender=Gender.MAN,
                archetype="friend",
                location_id=Location.TERRACE,
                relationship=RelationshipState(affection=6),
                big5=Big5(openness=5, conscientiousness=8, extraversion=6, agreeableness=7, neuroticism=3),
                attachment=AttachmentStyle.SECURE,
                type_on_paper=TypeOnPaper(
                    physical_type="grounded and easygoing",
                    personality_type=["steady", "thoughtful"],
                    values=["steadiness", "depth"],
                    dealbreakers=["flakiness"],
                ),
            ),
        ],
    )
