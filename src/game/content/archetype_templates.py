"""Persona-generation archetype templates."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ArchetypeTemplate(BaseModel):
    """Soft constraints for Trait Generator seeds."""

    model_config = ConfigDict(extra="forbid")

    id: str
    display_name: str
    typical_secret_engines: list[str]
    biggest_fear_themes: list[str]
    worst_habit_themes: list[str]
    voice_register: str
    big5_bias: dict[str, tuple[int, int]]
    attachment_bias: list[str]


ARCHETYPE_TEMPLATES: dict[str, ArchetypeTemplate] = {
    "sweetheart": ArchetypeTemplate(
        id="sweetheart",
        display_name="Sweetheart",
        typical_secret_engines=[
            "abandons people first to avoid being abandoned",
            "performs warmth to mask self-doubt",
            "over-gives so they feel needed",
            "treats every relationship like an audition they're failing",
        ],
        biggest_fear_themes=["being unseen", "being unloved", "being too much"],
        worst_habit_themes=["ghosting", "people-pleasing", "minimizing feelings"],
        voice_register="warm, soft, confrontation-avoidant, light pet names",
        big5_bias={"agreeableness": (70, 95), "neuroticism": (50, 80), "openness": (50, 80)},
        attachment_bias=["anxious", "secure"],
    ),
    "alpha": ArchetypeTemplate(
        id="alpha",
        display_name="Alpha",
        typical_secret_engines=[
            "needs to be the most useful person in any room",
            "controls intimacy by setting all the terms",
            "performs confidence to hide that they don't know how to receive",
            "leads to avoid being led",
        ],
        biggest_fear_themes=["being unnecessary", "losing control", "being seen as weak"],
        worst_habit_themes=["unsolicited advice", "interrupting", "deflecting compliments"],
        voice_register="direct, protective, leads with questions, deflects softness with action",
        big5_bias={"conscientiousness": (70, 95), "extraversion": (60, 90), "agreeableness": (40, 70)},
        attachment_bias=["secure", "avoidant"],
    ),
    "joker": ArchetypeTemplate(
        id="joker",
        display_name="Joker",
        typical_secret_engines=[
            "humor is how they keep people at a comfortable distance",
            "if they stop being funny they think no one will stay",
            "deflects feelings with bits because the feelings are too big",
            "uses being entertaining as currency",
        ],
        biggest_fear_themes=["not being funny", "being taken seriously", "being boring"],
        worst_habit_themes=["joking through vulnerability", "self-roasts", "ghosting"],
        voice_register="quick, bitty, sharp, pivots when intimacy approaches",
        big5_bias={"extraversion": (70, 95), "openness": (60, 90), "agreeableness": (40, 70)},
        attachment_bias=["avoidant", "anxious"],
    ),
    "friend": ArchetypeTemplate(
        id="friend",
        display_name="Friend",
        typical_secret_engines=[
            "always the friend, never the chosen one",
            "scared to want something so they want nothing loudly",
            "absorbs everyone else's feelings instead of having their own",
            "loyal to people who don't choose them back",
        ],
        biggest_fear_themes=["being a placeholder", "being passed over", "wanting too much"],
        worst_habit_themes=["disappearing", "agreeing too fast", "downplaying wins"],
        voice_register="low-key, observant, supportive, sharper than expected",
        big5_bias={"agreeableness": (75, 95), "conscientiousness": (60, 85), "extraversion": (30, 60)},
        attachment_bias=["anxious", "secure"],
    ),
}
