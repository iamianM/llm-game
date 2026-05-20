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
    1: ProducerTextDef("welcome", 1, "welcome", "Heartbreakers, welcome to Sunset Bay. Let the sparks begin."),
    2: ProducerTextDef(
        "group_date_invite",
        2,
        "group_date_invite",
        "Heartbreakers, tomorrow morning two of you will join the player for a group date.",
        ("group_date_day3",),
    ),
    3: ProducerTextDef(
        "coupling_warning",
        3,
        "coupling_warning",
        "Heartbreakers, tonight there will be a Pairing Ceremony. Choose wisely.",
    ),
    4: ProducerTextDef(
        "casa_amor_announce",
        4,
        "casa_amor_announce",
        "Heartbreakers, pack a bag. Flush of Hearts is open, and every connection is about to be tested.",
    ),
    6: ProducerTextDef(
        "final_vote_announce",
        6,
        "final_vote_announce",
        "Heartbreakers, tonight the Pulse vote decides the winning couple.",
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
    return f"{_producer_text_label(text.kind)}: {text.body}"


def _producer_text_label(kind: str) -> str:
    labels = {
        "casa_amor_announce": "Flush of Hearts text",
        "coupling_warning": "Pairing Ceremony text",
        "final_vote_announce": "Final Vote text",
        "group_date_invite": "Date text",
        "welcome": "Welcome text",
    }
    return labels.get(kind, "Paradise Calls")
