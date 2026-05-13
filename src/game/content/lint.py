"""Content linting for frontmatter references.

Design sources:
- docs/decisions/0006-mechanics-in-code-flavor-in-content.md

Implementation rule:
Validate markdown ids, phase names, location ids, and action references against
engine enums and content indexes before the game runs.
"""

from pathlib import Path

from src.game.content.loader import load_content
from src.game.engine.challenges import DAILY_CHALLENGE_SCHEDULE
from src.game.engine.intents import load_intents
from src.game.engine.producer_events import PRODUCER_TEXT_SCHEDULE
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
    expected_player_archetypes = {"heartthrob", "class_clown", "loyal_friend"}
    missing_player_archetypes = expected_player_archetypes - set(index.player_archetypes)
    if missing_player_archetypes:
        raise ValueError(f"missing player archetype content: {sorted(missing_player_archetypes)}")
    expected_challenges = {definition.id for definition in DAILY_CHALLENGE_SCHEDULE.values()}
    missing_challenges = expected_challenges - set(index.challenges)
    if missing_challenges:
        raise ValueError(f"missing challenge content: {sorted(missing_challenges)}")
    expected_texts = {definition.id for definition in PRODUCER_TEXT_SCHEDULE.values()}
    missing_texts = expected_texts - set(index.producer_texts)
    if missing_texts:
        raise ValueError(f"missing producer text content: {sorted(missing_texts)}")
    intents = load_intents()
    valid_stats = {"charm", "banter", "eq", "graft", "loyalty"}
    bad_stats = sorted({intent.stat_used for intent in intents} - valid_stats)
    if bad_stats:
        raise ValueError(f"invalid intent stat references: {bad_stats}")
    print(
        "content lint: "
        f"{len(index.archetypes)} archetype(s), {len(index.locations)} location(s), "
        f"{len(index.player_archetypes)} player archetype(s), "
        f"{len(index.challenges)} challenge(s), {len(index.producer_texts)} producer text(s), "
        f"{len(intents)} intent(s)"
    )
