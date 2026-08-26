"""Pydantic models for canonical game state."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.game.state.autonomy import PendingNPCApproach as PendingNPCApproach
from src.game.state.autonomy import PendingNPCSummon as PendingNPCSummon
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
    IntrosState as IntrosState,
)
from src.game.state.event_models import (
    MinigameChoice as MinigameChoice,
)
from src.game.state.event_models import (
    MinigameReveal as MinigameReveal,
)
from src.game.state.event_models import (
    MinigameRound as MinigameRound,
)
from src.game.state.event_models import (
    ProducerText as ProducerText,
)
from src.game.state.event_models import (
    QuestionBank as QuestionBank,
)
from src.game.state.event_models import (
    QuestionBankPrompt as QuestionBankPrompt,
)
from src.game.state.event_models import (
    RelationshipDelta as RelationshipDelta,
)
from src.game.state.flush import FlushDecision as FlushDecision
from src.game.state.flush import FlushOfHeartsState as FlushOfHeartsState
from src.game.state.flush import ResortName as ResortName
from src.game.state.memory import Memory as Memory
from src.game.state.memory import MemoryBatch as MemoryBatch
from src.game.state.memory import MemoryDraft as MemoryDraft
from src.game.state.memory import RecapDisposition as RecapDisposition
from src.game.state.personality import AttachmentStyle as AttachmentStyle
from src.game.state.personality import Big5 as Big5
from src.game.state.personality import IdealMatch as IdealMatch
from src.game.state.phase_clock import PhaseClock as PhaseClock
from src.game.state.traits import KnownFacts as KnownFacts
from src.game.state.traits import TraitCard as TraitCard
from src.game.state.traits import empty_trait_card

SCHEMA_VERSION = 30


class Phase(StrEnum):
    """The day clock for the playable v0 loop."""

    MORNING = "morning"
    INTROS = "intros"
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
    FLAME_DECK = "flame_deck"
    PRIVATE_SUITE = "private_suite"
    FLUSH_POOL = "flush_pool"
    FLUSH_KITCHEN = "flush_kitchen"
    FLUSH_TERRACE = "flush_terrace"


class Mood(StrEnum):
    HAPPY = "happy"
    FLIRTY = "flirty"
    UPSET = "upset"
    ANXIOUS = "anxious"
    ANGRY = "angry"
    CONTENT = "content"


class Gender(StrEnum):
    MAN = "man"
    WOMAN = "woman"


class PlayerStats(BaseModel):
    """Five player stats.

    Character creation enforces the starting 30-point budget. Runtime state can
    grow through game effects while each individual stat remains capped.
    """

    model_config = ConfigDict(extra="forbid")

    charm: int = Field(ge=3, le=9)
    banter: int = Field(ge=3, le=9)
    eq: int = Field(ge=3, le=9)
    spark: int = Field(ge=3, le=9)
    loyalty: int = Field(ge=3, le=9)


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
    known_facts: KnownFacts = Field(default_factory=dict)
    private_chat_attempts_this_phase: dict[str, int] = Field(default_factory=dict)


class RelationshipState(BaseModel):
    """Player-facing relationship state for one heartbreaker."""

    model_config = ConfigDict(extra="forbid")

    affection: int = Field(default=0, ge=0, le=100)
    chemistry: int = Field(default=0, ge=0, le=100)
    trust: int = Field(default=0, ge=0, le=100)
    friendship: int = Field(default=0, ge=0, le=100)


class HeartbreakerState(BaseModel):
    """Minimal NPC Heartbreaker state."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    gender: Gender
    archetype: str
    backstory: str
    location_id: Location
    relationship: RelationshipState = Field(default_factory=RelationshipState)
    public_perception: int = Field(default=50, ge=0, le=100)
    eliminated: bool = False
    mood: Mood = Mood.CONTENT
    big5: Big5
    attachment: AttachmentStyle
    ideal_match: IdealMatch
    familiarity_with_player: int = Field(default=0, ge=0, le=100)
    memories: list[Memory] = Field(default_factory=list)
    trait_card: TraitCard = Field(default_factory=empty_trait_card)
    known_facts: KnownFacts = Field(default_factory=dict)
    # Mutual NPC↔NPC attraction toward other heartbreakers (other_id -> 0..100).
    # The resort's own love stories: kept symmetric by the peer engine and grown
    # deterministically as compatible heartbreakers spend time co-located. Absent on
    # older saves (defaults empty), so the field is backward compatible.
    peer_affinity: dict[str, int] = Field(default_factory=dict)


class Couple(BaseModel):
    model_config = ConfigDict(extra="forbid")

    partner_a_id: str
    partner_b_id: str
    formed_on_day: int
    formed_via: Literal["opening", "ceremony", "flush_return", "proposal"] = "ceremony"
    has_used_private_suite: bool = False
    last_steal_attempt_chance: int | None = None
    rebound: bool = False


class PrivateSuiteState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    used_on_day: int | None = None
    partner_id: str | None = None
    deltas_applied: bool = False


class PendingGather(BaseModel):
    """A mandatory resort gather waiting to resolve."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["producer_text", "ceremony", "challenge", "flush_announce"]
    event_id: str
    gather_location: Location
    fires_on_turn: int


class DailyRecapItem(BaseModel):
    """One notable memory shown in the daily recap."""

    model_config = ConfigDict(extra="forbid")

    holder_id: str
    subject_id: str
    content: str
    formed_on_turn: int
    emotional_weight: int
    tags: list[str] = Field(default_factory=list)
    recap_disposition: RecapDisposition

    @field_validator("recap_disposition")
    @classmethod
    def require_visible_disposition(cls, value: RecapDisposition) -> RecapDisposition:
        if value is RecapDisposition.NONE:
            raise ValueError("Daily Recap items require a visible disposition")
        return value


class DailyRecap(BaseModel):
    """End-of-day background recap."""

    model_config = ConfigDict(extra="forbid")

    day: int
    resort_id: ResortName
    items: list[DailyRecapItem] = Field(default_factory=list)


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
    stat_used: Literal["charm", "banter", "eq", "spark", "loyalty"] | None
    risk: Literal["safe", "low", "medium", "high"]
    tone: str
    audience_hint: Literal["+", "-", ""] = ""
    reveal_tier: int = Field(default=0, ge=0, le=4)
    reveal_tag: str | None = None
    unlock_threshold: dict[str, int] | None = None


class FollowUpMenu(BaseModel):
    """Contextual menu generated after an NPC reply.

    Option count is driven by the prompt (it asks for a 2-5 menu including
    one exit); the schema only enforces non-emptiness so the engine can
    always render something.
    """

    model_config = ConfigDict(extra="forbid")

    options: list[FollowUpOption] = Field(min_length=1)
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
    """A persistent off-screen conversation between two NPC heartbreakers."""

    model_config = ConfigDict(extra="forbid")

    id: str
    participants: list[str] = Field(min_length=2, max_length=2)
    location_id: Location
    topic: str
    started_on_turn: int
    exchanges: list[BackgroundExchangeRecord] = Field(default_factory=list)
    status: Literal["active", "ending", "closed"] = "active"


class ConversationClosure(BaseModel):
    """One engine-owned record that a conversation ended this turn."""

    model_config = ConfigDict(extra="forbid")

    conversation_id: str
    participant_ids: list[str] = Field(min_length=2)
    reason: str


class PendingPairProposal(BaseModel):
    """An NPC proposal awaiting the player's response."""

    model_config = ConfigDict(extra="forbid")

    proposer_id: str
    target_id: str = "player"
    chance: int
    audience_hint_accept: Literal["+", "-", ""] = ""
    reason: str = "pair_proposal"


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
    resort: ResortName = ResortName.MAIN
    player: PlayerState
    heartbreakers: list[HeartbreakerState]
    couples: list[Couple] = Field(default_factory=list)
    active_ambient_id: str | None = None
    consecutive_ambient_turns: int = 0
    intro_completed_ids: list[str] = Field(default_factory=list)
    intro_memory_created: bool = False
    active_conversation: Conversation | None = None
    recent_player_lines: list[str] = Field(default_factory=list)
    npc_conversations: list[NPCNPCConversation] = Field(default_factory=list)
    pending_npc_summon: PendingNPCSummon | None = None
    pending_npc_approach: PendingNPCApproach | None = None
    pending_pair_proposal: PendingPairProposal | None = None
    heart_throb_briefs: list[dict[str, str]] = Field(default_factory=list)
    character_creation: CharacterCreation | None = None
    audience_snapshots: list[AudienceSnapshot] = Field(default_factory=list)
    intros: IntrosState | None = None
    pending_challenge: Challenge | None = None
    quizzed_traits_this_run: dict[str, list[str]] = Field(default_factory=dict)
    question_bank: QuestionBank | None = None
    pending_text: ProducerText | None = None
    pending_gather: PendingGather | None = None
    pending_group_date: GroupDate | None = None
    daily_recaps: list[DailyRecap] = Field(default_factory=list)
    private_suite: PrivateSuiteState = Field(default_factory=PrivateSuiteState)
    flush_of_hearts_state: FlushOfHeartsState | None = None
    outcome: RunOutcome | None = None

    @property
    def is_terminal(self) -> bool:
        return self.phase is Phase.COMPLETE or self.outcome is not None


def clamp_relationship(value: int) -> int:
    return max(0, min(100, value))


def new_game(seed: int, *, player_stats: PlayerStats | None = None) -> GameState:
    from src.game.state.cast import starting_heartbreakers

    return GameState(
        seed=seed,
        player=PlayerState(
            stats=player_stats
            if player_stats is not None
            else PlayerStats(charm=6, banter=6, eq=6, spark=6, loyalty=6)
        ),
        heartbreakers=starting_heartbreakers(),
    )
