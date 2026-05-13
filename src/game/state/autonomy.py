"""State models for NPC autonomy."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

SummonReason = Literal[
    "chemistry_partner_arrived",
    "friend_needs_them",
    "drama_pull",
    "needs_space",
    "phase_pressure",
]


class PendingNPCSummon(BaseModel):
    """A deterministic queued NPC summon from an arrival pull hit."""

    model_config = ConfigDict(extra="forbid")

    npc_id: str
    from_conversation_id: str
    reason: SummonReason
    target_location: str
