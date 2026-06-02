"""State models for NPC autonomy."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

SummonReason = Literal[
    "chemistry_partner_arrived",
    "friend_needs_them",
    "drama_summon",
    "needs_space",
    "phase_pressure",
]

ApproachReason = Literal[
    "wants_to_chat",
    "has_gossip",
    "flirty",
    "curious",
]


class PendingNPCSummon(BaseModel):
    """A deterministic queued NPC summon from an arrival private-chat hit."""

    model_config = ConfigDict(extra="forbid")

    npc_id: str
    from_conversation_id: str
    reason: SummonReason
    target_location: str


class PendingNPCApproach(BaseModel):
    """A co-located NPC seeking out the idle (ambient) player.

    The idle-state sibling of ``NPCInterruption``: instead of barging into an
    active conversation, an NPC walks up to the unoccupied player. The player
    chooses how to receive them, and that choice moves the relationship.
    """

    model_config = ConfigDict(extra="forbid")

    npc_id: str
    location_id: str
    reason: ApproachReason
    warmth: Literal["casual", "keen", "intense"]
    desire: int
