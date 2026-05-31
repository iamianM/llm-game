"""Composite Connection: a single, legible read on where the player stands.

The engine stores four raw 0-100 bonds per islander (affection, chemistry,
trust, friendship). Those are mechanically useful but they are a poor thing to
*show* a player: four abstract numbers with no sense of "where am I with this
person." This module is the single source of truth for turning those bonds into
two player-facing things:

- a composite **Connection** score (0-100), a romance-leaning blend; and
- an in-world **tier label** ("Just met" -> "Inseparable").

It also turns a single interaction's :class:`RelationshipDelta` into a short,
tonal, *non-numeric* line of feedback ("The spark with Chloe is electric.")
so the player feels their standing shift at the moment they act, instead of a
silent number changing in a profile modal they may never open.

Everything here is pure and deterministic: no I/O, no LLM, no RNG. That keeps it
testable under ``PARADISE_MOCK_LLM=1`` and safe to call from the serializer hot
path. It is deliberately *additive* — it never mutates stored bonds and never
feeds back into mechanical resolution, so it cannot perturb engine balance or
the determinism of baked checkpoints.
"""

from __future__ import annotations

from src.game.state.models import RelationshipDelta, RelationshipState

# Weights blend the four raw bonds into one romance-leaning score. Affection and
# chemistry (the "do I fancy them" axes) carry most of the weight; trust is the
# foundation underneath; friendship is a gentle lift. They sum to 1.0 so the
# composite stays on the same 0-100 scale as its inputs.
_W_AFFECTION = 0.34
_W_CHEMISTRY = 0.30
_W_TRUST = 0.22
_W_FRIENDSHIP = 0.14

# Ascending intensity ladder. Each entry is (inclusive lower bound, label). The
# labels are in-world and non-numeric — they are what the player reads, so they
# must never sound like a stat ("affection 52") or a grade.
_TIERS: tuple[tuple[int, str], ...] = (
    (0, "Just met"),
    (12, "Warming up"),
    (24, "A spark"),
    (38, "Getting close"),
    (52, "Strong connection"),
    (66, "Falling for them"),
    (80, "Smitten"),
    (92, "Inseparable"),
)

# Dominant-dimension tie-break order. When two bonds move by the same amount we
# report the one the player would *feel* most in a dating context.
_PRIORITY = ("chemistry", "affection", "trust", "friendship")

# (dimension, sign) -> (small, medium, big) phrasing. {name} is the islander's
# display name. Tonal, present tense, no digits, no stat words.
_PHRASES: dict[tuple[str, str], tuple[str, str, str]] = {
    ("chemistry", "+"): (
        "There's a flicker of something with {name}.",
        "The spark with {name} grows.",
        "The spark with {name} is electric.",
    ),
    ("chemistry", "-"): (
        "The spark with {name} dims a little.",
        "The spark with {name} cools.",
        "Whatever spark there was with {name} fizzles.",
    ),
    ("affection", "+"): (
        "{name} warms to you a touch.",
        "{name} is warming to you.",
        "{name} is properly into you.",
    ),
    ("affection", "-"): (
        "{name} pulls back a little.",
        "{name} cools on you.",
        "{name} is pulling away.",
    ),
    ("trust", "+"): (
        "{name} lets their guard down a touch.",
        "{name} trusts you more.",
        "{name} really opens up to you.",
    ),
    ("trust", "-"): (
        "{name}'s guard creeps back up.",
        "{name} trusts you a little less.",
        "{name} shuts you out.",
    ),
    ("friendship", "+"): (
        "You and {name} click a bit more.",
        "You and {name} are becoming proper mates.",
        "You and {name} are tight now.",
    ),
    ("friendship", "-"): (
        "Things feel a touch cooler with {name}.",
        "You and {name} drift apart.",
        "The friendship with {name} is fracturing.",
    ),
}


def connection_score(rel: RelationshipState) -> int:
    """Composite 0-100 Connection from the four raw bonds (romance-leaning)."""
    raw = (
        _W_AFFECTION * rel.affection
        + _W_CHEMISTRY * rel.chemistry
        + _W_TRUST * rel.trust
        + _W_FRIENDSHIP * rel.friendship
    )
    return int(round(raw))


def connection_tier(score: int) -> tuple[int, str]:
    """Map a 0-100 score to an ascending (index, label) on the tier ladder."""
    chosen_index = 0
    chosen_label = _TIERS[0][1]
    for index, (lower, label) in enumerate(_TIERS):
        if score >= lower:
            chosen_index, chosen_label = index, label
        else:
            break
    return chosen_index, chosen_label


def connection_label(score: int) -> str:
    """Convenience: just the tier label for a score."""
    return connection_tier(score)[1]


def _bucket(magnitude: int) -> int:
    """Magnitude bucket: 0 small (1-3), 1 medium (4-7), 2 big (8+)."""
    if magnitude >= 8:
        return 2
    if magnitude >= 4:
        return 1
    return 0


def _dominant_dimension(delta: RelationshipDelta) -> str | None:
    """The dimension that moved most (abs), tie-broken by felt-priority.

    Returns ``None`` when nothing moved.
    """
    values = {
        "affection": delta.affection,
        "chemistry": delta.chemistry,
        "trust": delta.trust,
        "friendship": delta.friendship,
    }
    best: str | None = None
    best_abs = 0
    for dim in _PRIORITY:
        magnitude = abs(values[dim])
        if magnitude > best_abs:
            best_abs = magnitude
            best = dim
    return best


def describe_shift(delta: RelationshipDelta, name: str) -> str | None:
    """A short, tonal, non-numeric line for one interaction's relationship change.

    Driven by the *dominant* dimension's direction and magnitude. Returns
    ``None`` only when nothing moved (every delta field is zero), so callers
    never surface empty feedback. Note this keys off the single biggest move,
    not the net sum — an offsetting delta (e.g. ``affection=+5, trust=-5``) still
    produces a line for whichever dimension the player would feel most.
    """
    dim = _dominant_dimension(delta)
    if dim is None:
        return None
    value = getattr(delta, dim)
    sign = "+" if value > 0 else "-"
    template = _PHRASES[(dim, sign)][_bucket(abs(value))]
    return template.format(name=name)
