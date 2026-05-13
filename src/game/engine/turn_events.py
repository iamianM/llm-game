"""Phase-transition event helpers for the turn pipeline."""

from __future__ import annotations

from typing import Literal

from src.game.engine.audience import record_audience_snapshot
from src.game.engine.casa_amor import enter_casa_amor, return_ceremony
from src.game.engine.ceremonies import (
    CeremonyEvent,
    RecouplingResult,
    final_vote_ceremony,
    recoupling,
)
from src.game.engine.challenges import (
    challenge_event_message,
    resolve_challenge,
    schedule_challenge,
)
from src.game.engine.phases import advance_phase
from src.game.engine.producer_events import producer_text_event_message, schedule_producer_text
from src.game.state.models import (
    AudienceSnapshot,
    GameState,
    Location,
    PendingGather,
    Phase,
    RunOutcome,
)
from src.game.state.rng import SeededRng

GatherKind = Literal["producer_text", "ceremony", "challenge", "casa_announce"]


def advance_phase_with_events(
    state: GameState,
    rng: SeededRng,
) -> tuple[list[CeremonyEvent], AudienceSnapshot | None]:
    """Advance the clock and return any events created by the transition."""
    events: list[CeremonyEvent] = []
    audience_snapshot: AudienceSnapshot | None = None
    casa_active = state.casa_amor_state is not None and not state.casa_amor_state.returned
    if state.phase.value == "evening" and state.day in {3, 5} and not (state.day == 5 and casa_active):
        events.append(_schedule_gather(state, kind="ceremony", event_id=f"recoupling_day_{state.day}"))
        return events, audience_snapshot
    if state.phase.value == "evening" and state.day >= 6:
        events.append(_schedule_gather(state, kind="ceremony", event_id="final_vote"))
        return events, audience_snapshot
    if state.phase.value == "evening":
        audience_snapshot = record_audience_snapshot(state)
    advance_phase(state)
    if state.day == 6 and state.phase is Phase.MORNING:
        if state.casa_amor_state is not None and not state.casa_amor_state.returned:
            events.append(_schedule_gather(state, kind="ceremony", event_id="casa_return"))
    events.extend(_scheduled_phase_events(state, rng))
    return events, audience_snapshot


def resolve_pending_gather(
    state: GameState,
    rng: SeededRng,
) -> tuple[list[CeremonyEvent], AudienceSnapshot | None]:
    """Resolve a mandatory gather event after the player joins it."""
    if state.pending_gather is None:
        raise ValueError("no pending gather to resolve")
    gather = state.pending_gather
    events: list[CeremonyEvent] = []
    audience_snapshot: AudienceSnapshot | None = None
    if gather.kind in {"producer_text", "casa_announce"}:
        if state.pending_text is not None:
            events.append(CeremonyEvent(kind="producer_text", message=producer_text_event_message(state.pending_text)))
            if state.pending_text.kind == "casa_amor_announce":
                events.append(enter_casa_amor(state))
        state.pending_text = None
    elif gather.kind == "ceremony" and gather.event_id.startswith("recoupling"):
        ceremony = recoupling(state)
        events.extend(recoupling_events(ceremony))
        if ceremony.eliminated_id == state.player.id:
            state.outcome = RunOutcome.ELIMINATED
        audience_snapshot = record_audience_snapshot(state)
        advance_phase(state)
    elif gather.kind == "ceremony" and gather.event_id == "final_vote":
        audience_snapshot = record_audience_snapshot(state)
        events.append(final_vote_ceremony(state))
    elif gather.kind == "ceremony" and gather.event_id == "casa_return":
        casa_return = return_ceremony(state)
        if casa_return is not None:
            events.append(casa_return)
    elif gather.kind == "challenge":
        challenge = schedule_challenge(state.day)
        if challenge is not None:
            state.pending_challenge = resolve_challenge(state, challenge, rng.fork(f"challenge-{state.day}"))
            events.append(CeremonyEvent(kind="challenge", message=challenge_event_message(state.pending_challenge)))
    else:
        raise ValueError(f"unknown pending gather: {gather.model_dump()}")
    state.pending_gather = None
    return events, audience_snapshot


def recoupling_events(ceremony: RecouplingResult) -> list[CeremonyEvent]:
    """Create recoupling and optional dumping events."""
    events = [CeremonyEvent(kind="recoupling", message="Recoupling ceremony completed.")]
    for attempt in ceremony.steal_attempts:
        outcome = "succeeds" if attempt.success else "fails"
        events.append(
            CeremonyEvent(
                kind="steal_attempt",
                message=(
                    f"Steal attempt: {attempt.bombshell_id} tries to steal {attempt.target_id} "
                    f"from {attempt.abandoned_id} and {outcome} "
                    f"(roll {attempt.roll} vs {attempt.chance})."
                ),
                islander_id=attempt.bombshell_id,
            )
        )
        if attempt.success:
            events.append(
                CeremonyEvent(
                    kind="partner_stolen",
                    message=f"Partner stolen: {attempt.target_id} recouples with {attempt.bombshell_id}.",
                    islander_id=attempt.target_id,
                )
            )
    if ceremony.eliminated_id is not None:
        events.append(
            CeremonyEvent(
                kind="elimination",
                message=f"Dumping decision: {ceremony.eliminated_id} leaves the villa.",
                islander_id=ceremony.eliminated_id,
            )
        )
    return events


def challenge_response_event(state: GameState) -> CeremonyEvent | None:
    """Return a narratable event for a completed challenge response."""
    if state.pending_challenge is None:
        return None
    return CeremonyEvent(kind="challenge", message=challenge_event_message(state.pending_challenge))


def _scheduled_phase_events(state: GameState, rng: SeededRng) -> list[CeremonyEvent]:
    events: list[CeremonyEvent] = []
    if state.phase.value == "challenge":
        challenge = schedule_challenge(state.day)
        if challenge is not None:
            state.pending_challenge = challenge
            if challenge.kind != "snog_marry_pie":
                state.pending_challenge = resolve_challenge(state, challenge, rng.fork(f"challenge-{state.day}"))
            events.append(CeremonyEvent(kind="challenge", message=challenge_event_message(state.pending_challenge)))
    if state.phase.value == "text":
        state.pending_text = schedule_producer_text(state.day, state)
        if state.pending_text is not None:
            gather_kind: GatherKind = (
                "casa_announce" if state.pending_text.kind == "casa_amor_announce" else "producer_text"
            )
            events.append(_schedule_gather(state, kind=gather_kind, event_id=state.pending_text.id))
    return events


def _schedule_gather(
    state: GameState,
    *,
    kind: GatherKind,
    event_id: str,
) -> CeremonyEvent:
    state.pending_gather = PendingGather(
        kind=kind,
        event_id=event_id,
        gather_location=Location.FIREPIT,
        fires_on_turn=state.turn_index + 1,
    )
    return CeremonyEvent(
        kind="gather_scheduled",
        message=f"Everyone is called to the firepit for {event_id}.",
    )
