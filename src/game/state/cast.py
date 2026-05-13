"""Hardcoded v0 starting cast factory."""

from __future__ import annotations

from src.game.state.models import (
    AttachmentStyle,
    Big5,
    Gender,
    IslanderState,
    Location,
    RelationshipState,
    TypeOnPaper,
)


def starting_islanders() -> list[IslanderState]:
    """Return the H9 eight-islander starting cast."""
    return [
        _islander("chloe", "Chloe", Gender.WOMAN, "sweetheart", Location.POOL, 10, (7, 6, 9, 8, 4), AttachmentStyle.SECURE, "warm smiles and kind eyes", ["warm", "confident"], ["loyalty", "honesty"], ["arrogance"]),
        _islander("maya", "Maya", Gender.WOMAN, "joker", Location.KITCHEN, 8, (8, 5, 9, 5, 6), AttachmentStyle.ANXIOUS, "expressive people with bright energy", ["funny", "attentive"], ["humor", "attention"], ["neglect"]),
        _islander("liam", "Liam", Gender.MAN, "friend", Location.TERRACE, 6, (5, 8, 6, 7, 3), AttachmentStyle.SECURE, "grounded and easygoing", ["steady", "thoughtful"], ["steadiness", "depth"], ["flakiness"]),
        _islander("sophie_start", "Sophie", Gender.WOMAN, "alpha", Location.BEDROOM, 7, (7, 8, 8, 5, 5), AttachmentStyle.AVOIDANT, "sharp style and confident eye contact", ["ambitious", "direct"], ["drive", "confidence"], ["clinginess"]),
        _islander("nia_start", "Nia", Gender.WOMAN, "sweetheart", Location.TERRACE, 7, (8, 7, 7, 8, 4), AttachmentStyle.SECURE, "soft warmth and grounded humor", ["kind", "steady"], ["honesty", "patience"], ["cruelty"]),
        _islander("marcus_start", "Marcus", Gender.MAN, "alpha", Location.KITCHEN, 7, (6, 8, 8, 5, 4), AttachmentStyle.AVOIDANT, "athletic confidence and direct energy", ["confident", "protective"], ["ambition", "loyalty"], ["indecision"]),
        _islander("blake_start", "Blake", Gender.MAN, "friend", Location.BEDROOM, 6, (6, 7, 6, 8, 3), AttachmentStyle.SECURE, "dry wit and calm loyalty", ["thoughtful", "funny"], ["humor", "depth"], ["showboating"]),
        _islander("jordan_start", "Jordan", Gender.MAN, "joker", Location.POOL, 6, (7, 5, 9, 6, 5), AttachmentStyle.ANXIOUS, "bright grin and restless energy", ["playful", "attentive"], ["fun", "reassurance"], ["being ignored"]),
    ]


def _islander(
    islander_id: str,
    name: str,
    gender: Gender,
    archetype: str,
    location: Location,
    affection: int,
    big5: tuple[int, int, int, int, int],
    attachment: AttachmentStyle,
    physical_type: str,
    personality_type: list[str],
    values: list[str],
    dealbreakers: list[str],
) -> IslanderState:
    openness, conscientiousness, extraversion, agreeableness, neuroticism = big5
    return IslanderState(
        id=islander_id,
        name=name,
        gender=gender,
        archetype=archetype,
        location_id=location,
        relationship=RelationshipState(affection=affection),
        big5=Big5(
            openness=openness,
            conscientiousness=conscientiousness,
            extraversion=extraversion,
            agreeableness=agreeableness,
            neuroticism=neuroticism,
        ),
        attachment=attachment,
        type_on_paper=TypeOnPaper(
            physical_type=physical_type,
            personality_type=personality_type,
            values=values,
            dealbreakers=dealbreakers,
        ),
    )
