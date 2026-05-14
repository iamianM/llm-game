"""Location-aware ambient action content."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.game.state.models import Location

AmbientCategory = Literal["relax", "observe", "self_care", "social"]


class AmbientOption(BaseModel):
    """One non-conversation action available at a villa location."""

    model_config = ConfigDict(extra="forbid")

    id: str
    location: Location
    label: str
    category: AmbientCategory
    mood_effect: str
    stat_trickle: dict[str, int] = Field(default_factory=dict)
    npc_encounter_boost: int = 0


AMBIENT_OPTIONS: tuple[AmbientOption, ...] = (
    AmbientOption(
        id="ambient_wait",
        location=Location.POOL,
        label="Take in the villa",
        category="relax",
        mood_effect="neutral",
        stat_trickle={},
        npc_encounter_boost=4,
    ),
    AmbientOption(
        id="pool_lounge",
        location=Location.POOL,
        label="Lounge by the pool",
        category="relax",
        mood_effect="content",
        stat_trickle={"charm": 1},
        npc_encounter_boost=8,
    ),
    AmbientOption(
        id="pool_people_watch",
        location=Location.POOL,
        label="People-watch from a lounger",
        category="observe",
        mood_effect="curious",
        stat_trickle={"eq": 1},
        npc_encounter_boost=12,
    ),
    AmbientOption(
        id="kitchen_make_snack",
        location=Location.KITCHEN,
        label="Make a snack",
        category="self_care",
        mood_effect="settled",
        stat_trickle={"loyalty": 1},
        npc_encounter_boost=10,
    ),
    AmbientOption(
        id="kitchen_help_out",
        location=Location.KITCHEN,
        label="Help tidy the kitchen",
        category="social",
        mood_effect="grounded",
        stat_trickle={"eq": 1},
        npc_encounter_boost=14,
    ),
    AmbientOption(
        id="terrace_take_air",
        location=Location.TERRACE,
        label="Take air on the terrace",
        category="relax",
        mood_effect="reflective",
        stat_trickle={"eq": 1},
        npc_encounter_boost=8,
    ),
    AmbientOption(
        id="terrace_scan_villa",
        location=Location.TERRACE,
        label="Scan the villa from above",
        category="observe",
        mood_effect="watchful",
        stat_trickle={"banter": 1},
        npc_encounter_boost=12,
    ),
    AmbientOption(
        id="bedroom_reset",
        location=Location.BEDROOM,
        label="Reset in the bedroom",
        category="self_care",
        mood_effect="calm",
        stat_trickle={"loyalty": 1},
        npc_encounter_boost=5,
    ),
    AmbientOption(
        id="bedroom_check_outfits",
        location=Location.BEDROOM,
        label="Check outfits",
        category="self_care",
        mood_effect="confident",
        stat_trickle={"charm": 1},
        npc_encounter_boost=7,
    ),
    AmbientOption(
        id="firepit_sit_quietly",
        location=Location.FIREPIT,
        label="Sit quietly by the firepit",
        category="relax",
        mood_effect="thoughtful",
        stat_trickle={"loyalty": 1},
        npc_encounter_boost=6,
    ),
)


def ambient_options_for(location: Location) -> list[AmbientOption]:
    """Return ambient options for one location."""
    return [
        option
        for option in AMBIENT_OPTIONS
        if option.id != "ambient_wait" and option.location is location
    ]


def get_ambient_option(option_id: str) -> AmbientOption:
    """Return one ambient option or raise."""
    for option in AMBIENT_OPTIONS:
        if option.id == option_id:
            return option
    raise ValueError(f"unknown ambient option: {option_id}")
