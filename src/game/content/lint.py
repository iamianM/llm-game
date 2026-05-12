"""Content linting for frontmatter references.

Design sources:
- docs/decisions/0006-mechanics-in-code-flavor-in-content.md

Implementation rule:
Validate markdown ids, phase names, location ids, and action references against
engine enums and content indexes before the game runs.
"""

from pathlib import Path

from src.game.content.loader import load_content
from src.game.engine.intents import load_intents
from src.game.state.models import Location


def run_lint() -> None:
    """Validate runtime content references."""
    index = load_content(Path("content"))
    expected_archetypes = {"sweetheart", "joker", "friend"}
    missing_archetypes = expected_archetypes - set(index.archetypes)
    if missing_archetypes:
        raise ValueError(f"missing archetype content: {sorted(missing_archetypes)}")
    missing_locations = {location.value for location in Location} - set(index.locations)
    if missing_locations:
        raise ValueError(f"missing location content: {sorted(missing_locations)}")
    intents = load_intents()
    valid_stats = {"charm", "banter", "eq", "graft", "loyalty"}
    bad_stats = sorted({intent.stat_used for intent in intents} - valid_stats)
    if bad_stats:
        raise ValueError(f"invalid intent stat references: {bad_stats}")
    print(
        "content lint: "
        f"{len(index.archetypes)} archetype(s), {len(index.locations)} location(s), "
        f"{len(intents)} intent(s)"
    )
