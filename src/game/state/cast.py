"""Hardcoded v0 starting cast factory."""

from __future__ import annotations

from src.game.content.loader import load_backstories
from src.game.content.trait_library import opening_trait_cards
from src.game.state.models import (
    AttachmentStyle,
    Big5,
    Gender,
    IslanderState,
    Location,
    RelationshipState,
    TypeOnPaper,
)
from src.game.state.traits import KnownFact, TraitCard


def starting_islanders() -> list[IslanderState]:
    """Return the H9 eight-islander starting cast."""
    backstories = load_backstories()
    trait_cards = opening_trait_cards()
    cast = [
        _islander("chloe", "Chloe", Gender.WOMAN, "sweetheart", backstories, trait_cards, Location.POOL, 10, (7, 6, 9, 8, 4), AttachmentStyle.SECURE, "warm smiles and kind eyes", ["warm", "confident"], ["loyalty", "honesty"], ["arrogance"]),
        _islander("maya", "Maya", Gender.WOMAN, "joker", backstories, trait_cards, Location.KITCHEN, 8, (8, 5, 9, 5, 6), AttachmentStyle.ANXIOUS, "expressive people with bright energy", ["funny", "attentive"], ["humor", "attention"], ["neglect"]),
        _islander("liam", "Liam", Gender.MAN, "friend", backstories, trait_cards, Location.TERRACE, 6, (5, 8, 6, 7, 3), AttachmentStyle.SECURE, "grounded and easygoing", ["steady", "thoughtful"], ["steadiness", "depth"], ["flakiness"]),
        _islander("sophie", "Sophie", Gender.WOMAN, "alpha", backstories, trait_cards, Location.BEDROOM, 7, (7, 8, 8, 5, 5), AttachmentStyle.AVOIDANT, "sharp style and confident eye contact", ["ambitious", "direct"], ["drive", "confidence"], ["clinginess"]),
        _islander("nia", "Nia", Gender.WOMAN, "sweetheart", backstories, trait_cards, Location.TERRACE, 7, (8, 7, 7, 8, 4), AttachmentStyle.SECURE, "soft warmth and grounded humor", ["kind", "steady"], ["honesty", "patience"], ["cruelty"]),
        _islander("marcus", "Marcus", Gender.MAN, "alpha", backstories, trait_cards, Location.KITCHEN, 7, (6, 8, 8, 5, 4), AttachmentStyle.AVOIDANT, "athletic confidence and direct energy", ["confident", "protective"], ["ambition", "loyalty"], ["indecision"]),
        _islander("blake", "Blake", Gender.MAN, "friend", backstories, trait_cards, Location.BEDROOM, 6, (6, 7, 6, 8, 3), AttachmentStyle.SECURE, "dry wit and calm loyalty", ["thoughtful", "funny"], ["humor", "depth"], ["showboating"]),
        _islander("jordan", "Jordan", Gender.MAN, "joker", backstories, trait_cards, Location.POOL, 6, (7, 5, 9, 6, 5), AttachmentStyle.ANXIOUS, "bright grin and restless energy", ["playful", "attentive"], ["fun", "reassurance"], ["being ignored"]),
    ]
    _seed_npc_known_facts(cast)
    return cast


def _islander(
    islander_id: str,
    name: str,
    gender: Gender,
    archetype: str,
    backstories: dict[str, str],
    trait_cards: dict[str, TraitCard],
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
        backstory=backstories[islander_id],
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
        trait_card=trait_cards[islander_id],
    )


def _seed_npc_known_facts(cast: list[IslanderState]) -> None:
    """Give NPCs enough public trivia about each other for early gossip hooks."""
    for holder in cast:
        for subject in cast:
            if holder.id == subject.id:
                continue
            for key, fact in subject.trait_card.core_traits.items():
                if fact.tier != 1:
                    continue
                fact_key = f"{subject.id}.{key}"
                holder.known_facts[fact_key] = KnownFact(
                    fact_key=fact_key,
                    value=fact.value,
                    source="witnessed",
                    source_npc_id="preseason",
                    learned_on_day=1,
                    learned_on_turn=0,
                    confidence=1.0,
                    citation=f"Preseason chatter about {subject.name}",
                )
