"""Compatibility, familiarity, and attachment-style mechanics."""

from __future__ import annotations

from src.game.state.models import AttachmentStyle, GameState, IslanderState, RelationshipDelta

ARCHETYPE_MATCHES = {
    "heartthrob": {"confident", "ambitious", "edge"},
    "class_clown": {"funny", "humor", "attention"},
    "loyal_friend": {"loyalty", "honesty", "steadiness", "depth", "warm"},
    "balanced": {"honesty"},
}

REVEAL_THRESHOLDS = {
    "physical_type": 25,
    "personality_type": 50,
    "values": 75,
    "dealbreakers": 100,
}


def compatibility_bonus(state: GameState, target: IslanderState, tags: list[str]) -> int:
    """Return the Type-on-Paper compatibility bonus, capped at +20."""
    matches = 0
    archetype_tags = ARCHETYPE_MATCHES.get(state.player.archetype_id, ARCHETYPE_MATCHES["balanced"])
    wanted = {item.lower() for item in target.type_on_paper.personality_type + target.type_on_paper.values}
    matches += len(wanted & {tag.lower() for tag in tags})
    matches += len(wanted & archetype_tags)
    if any(word in target.type_on_paper.physical_type.lower() for word in archetype_tags):
        matches += 1
    return min(20, matches * 4)


def dealbreaker_penalty(target: IslanderState, tags: list[str]) -> int:
    """Return the dealbreaker penalty for recent player tags."""
    normalized = {tag.lower() for tag in tags}
    for dealbreaker in target.type_on_paper.dealbreakers:
        if dealbreaker.lower() in normalized:
            return 15
    return 0


def attachment_delta_modifier(
    target: IslanderState,
    intent_kind: str,
    success: bool,
) -> RelationshipDelta:
    """Return relationship delta modifiers from attachment style."""
    style = target.attachment
    if style is AttachmentStyle.SECURE and success and _is_deep(intent_kind):
        return RelationshipDelta(trust=1)
    if style is AttachmentStyle.ANXIOUS:
        if not success and _is_flirty(intent_kind):
            return RelationshipDelta(trust=-3)
        if not success and _is_deep(intent_kind):
            return RelationshipDelta(trust=2)
    if style is AttachmentStyle.AVOIDANT:
        if success and _is_flirty(intent_kind):
            return RelationshipDelta(chemistry=-1)
        if success and _is_deep(intent_kind):
            return RelationshipDelta(trust=-2)
    if style is AttachmentStyle.FEARFUL and success:
        swing = 2 if (target.familiarity_with_player % 2 == 0) else -2
        if _is_flirty(intent_kind):
            return RelationshipDelta(chemistry=swing)
        if _is_deep(intent_kind):
            return RelationshipDelta(trust=-1)
    return RelationshipDelta()


def apply_familiarity(target: IslanderState, amount: int) -> None:
    """Increase familiarity, capped at 100."""
    target.familiarity_with_player = max(0, min(100, target.familiarity_with_player + amount))


def revealed_preferences(target: IslanderState) -> dict[str, object]:
    """Return currently revealed Type-on-Paper fields for an islander."""
    prefs = target.type_on_paper
    familiarity = target.familiarity_with_player
    revealed: dict[str, object] = {}
    if familiarity >= REVEAL_THRESHOLDS["physical_type"]:
        revealed["physical_type"] = prefs.physical_type
    if familiarity >= REVEAL_THRESHOLDS["personality_type"]:
        revealed["personality_type"] = prefs.personality_type
    if familiarity >= REVEAL_THRESHOLDS["values"]:
        revealed["values"] = prefs.values
    if familiarity >= REVEAL_THRESHOLDS["dealbreakers"]:
        revealed["dealbreakers"] = prefs.dealbreakers
    return revealed


def revealed_preference_count(state: GameState) -> int:
    """Count all revealed preference fields across NPCs."""
    return sum(len(revealed_preferences(islander)) for islander in state.islanders)


def _is_flirty(intent_kind: str) -> bool:
    return "flirt" in intent_kind or intent_kind in {"escalate_flirt", "flirty_compliment_looks"}


def _is_deep(intent_kind: str) -> bool:
    return "deep" in intent_kind or intent_kind in {"honest_vulnerable", "share_feelings"}
