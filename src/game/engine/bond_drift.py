"""Overnight bond drift: the villa keeps moving between the player's scenes.

Each night the four raw bonds (affection, chemistry, trust, friendship) settle
toward the *shape of the couples*, so relationships are never frozen between the
moments the player acts:

- **Consolidation** — an islander coupled with the player warms a touch: the
  easy comfort of being a couple. Passive warmth plateaus at a soft ceiling, so
  coupling up and then idling can never substitute for real scenes.
- **Roving eye** — an islander who chose *someone else* cools on the player
  romantically (their head has turned), though the platonic layer lingers.
- **Fade** — anyone left unpartnered slowly loses the spark without tending.

Everything here is pure and deterministic: no I/O, no LLM, no RNG. Drift is
small, floored, and ceilinged so it animates the Connection ring day to day
without ever erasing the player's actual progress. It is the single source of
truth for "what one night does to a bond"; the phase clock calls
:func:`apply_overnight_drift` exactly once per night at the day rollover.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.game.engine.state_access import apply_relationship_delta
from src.game.state.models import GameState, IslanderState, RelationshipDelta

# Passive warmth plateaus here: being a couple lifts a bond to "comfortable" but
# anything past it has to be earned in an actual scene.
SOFT_CEIL = 60
# Cooling never drags a built bond below this. Neglect dims a connection; it does
# not delete it, and it never undercuts a bond the player already let lapse.
SOFT_FLOOR = 10

DriftKind = Literal["consolidation", "roving", "fade"]


@dataclass(frozen=True)
class BondDrift:
    """The realized overnight change to one islander's bonds with the player.

    Carries the *applied* deltas (after flooring/ceiling), so it is an honest
    record of what moved — a caller can surface it without recomputing.
    """

    islander_id: str
    kind: DriftKind
    affection: int = 0
    chemistry: int = 0
    trust: int = 0
    friendship: int = 0

    @property
    def is_zero(self) -> bool:
        return not (self.affection or self.chemistry or self.trust or self.friendship)

    def as_delta(self) -> RelationshipDelta:
        return RelationshipDelta(
            affection=self.affection,
            chemistry=self.chemistry,
            trust=self.trust,
            friendship=self.friendship,
        )


def _warm(value: int, amount: int) -> int:
    """Realized positive step toward (but never past) ``SOFT_CEIL``.

    Returns 0 once a bond is at or above the ceiling, so a bond pushed high by
    real scenes is never *further* inflated by passivity — and is never cooled
    by warmth either.
    """
    if value >= SOFT_CEIL:
        return 0
    return min(amount, SOFT_CEIL - value)


def _cool(value: int, amount: int) -> int:
    """Realized negative step toward (but never past) ``SOFT_FLOOR``.

    Returns 0 once a bond is at or below the floor, so cooling can dim a strong
    bond but can neither bottom it out nor disturb one that is already low.
    """
    if value <= SOFT_FLOOR:
        return 0
    return -min(amount, value - SOFT_FLOOR)


def _partner_id(state: GameState, islander_id: str) -> str | None:
    """The id of whoever ``islander_id`` is currently coupled with, or None."""
    for couple in state.couples:
        if couple.partner_a_id == islander_id:
            return couple.partner_b_id
        if couple.partner_b_id == islander_id:
            return couple.partner_a_id
    return None


def plan_drift_for(state: GameState, npc: IslanderState) -> BondDrift:
    """Pure: the realized overnight drift for one islander, given couple state."""
    rel = npc.relationship
    partner = _partner_id(state, npc.id)
    if partner == state.player.id:
        # Consolidation: the comfort of being a couple warms every axis a touch.
        return BondDrift(
            islander_id=npc.id,
            kind="consolidation",
            affection=_warm(rel.affection, 1),
            chemistry=_warm(rel.chemistry, 1),
            trust=_warm(rel.trust, 1),
            friendship=_warm(rel.friendship, 1),
        )
    if partner is not None:
        # Roving eye: they picked someone else; romance cools, mateship lingers.
        return BondDrift(
            islander_id=npc.id,
            kind="roving",
            affection=_cool(rel.affection, 1),
            chemistry=_cool(rel.chemistry, 2),
        )
    # Fade: unpartnered, the spark slips without tending. The platonic layer
    # (trust/friendship) is left alone — you can stay mates while the romance
    # quietly cools.
    return BondDrift(
        islander_id=npc.id,
        kind="fade",
        affection=_cool(rel.affection, 1),
        chemistry=_cool(rel.chemistry, 1),
    )


def apply_overnight_drift(state: GameState) -> list[BondDrift]:
    """Apply one night of drift to every live islander; return what actually moved.

    Called once per night by the phase clock at the day rollover. Skips the
    player and eliminated islanders. Deterministic — a pure function of the
    current bonds and couple state — so replays and baked checkpoints stay
    stable. It is *not* idempotent (each call drifts again from the freshly
    mutated bonds), which is why the phase clock is the single caller and fires
    it exactly once per night.
    """
    moved: list[BondDrift] = []
    for npc in state.islanders:
        if npc.eliminated:
            continue
        drift = plan_drift_for(state, npc)
        if drift.is_zero:
            continue
        apply_relationship_delta(npc, drift.as_delta())
        moved.append(drift)
    return moved
