"""Deterministic producer text scheduling."""

from __future__ import annotations

from dataclasses import dataclass

from src.game.state.models import GameState, GroupDate, Location, Mood, ProducerText


@dataclass(frozen=True)
class ProducerTextDef:
    """Static producer text schedule entry."""

    id: str
    day: int
    kind: str
    body: str
    triggers: tuple[str, ...] = ()


PRODUCER_TEXT_SCHEDULE: dict[int, ProducerTextDef] = {
    1: ProducerTextDef("welcome", 1, "welcome", "Islanders, welcome to the villa. Let the grafting begin."),
    2: ProducerTextDef(
        "group_date_invite",
        2,
        "group_date_invite",
        "Islanders, tomorrow morning two of you will join the player for a group date.",
        ("group_date_day3",),
    ),
    3: ProducerTextDef(
        "coupling_warning",
        3,
        "coupling_warning",
        "Islanders, tonight there will be a recoupling. Choose wisely.",
    ),
    4: ProducerTextDef(
        "bombshell_arrival_tease",
        4,
        "bombshell_arrival_tease",
        "Islanders, a new bombshell is ready to turn heads.",
    ),
    6: ProducerTextDef(
        "final_vote_announce",
        6,
        "final_vote_announce",
        "Islanders, tonight the public vote decides the winning couple.",
    ),
}


def schedule_producer_text(day: int, state: GameState) -> ProducerText | None:
    """Create the scheduled producer text and side effects for ``day``."""
    definition = PRODUCER_TEXT_SCHEDULE.get(day)
    if definition is None:
        return None
    text = ProducerText(
        id=definition.id,
        day=day,
        kind=definition.kind,
        body=definition.body,
        triggers=list(definition.triggers),
    )
    if definition.kind == "group_date_invite":
        state.pending_group_date = GroupDate(
            id="group_date_day3",
            participants=["player", "chloe", "maya"],
            location=Location.TERRACE.value,
            day=3,
        )
    if definition.kind == "coupling_warning":
        for islander in state.islanders:
            if not islander.eliminated:
                islander.mood = Mood.ANXIOUS
    return text


def producer_text_event_message(text: ProducerText) -> str:
    """Return a concise narratable producer text event message."""
    return f"Producer text: {text.kind}. {text.body}"
