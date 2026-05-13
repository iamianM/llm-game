"""Phase-transition event helpers for the turn pipeline."""

from __future__ import annotations

from src.game.engine.audience import record_audience_snapshot
from src.game.engine.ceremonies import (
    CeremonyEvent,
    RecouplingResult,
    arrive_bombshell,
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
from src.game.state.models import AudienceSnapshot, GameState, RunOutcome
from src.game.state.rng import SeededRng


def advance_phase_with_events(
    state: GameState,
    rng: SeededRng,
) -> tuple[list[CeremonyEvent], AudienceSnapshot | None]:
    """Advance the clock and return any events created by the transition."""
    events: list[CeremonyEvent] = []
    audience_snapshot: AudienceSnapshot | None = None
    if state.phase.value == "evening" and state.day in {3, 5}:
        ceremony = recoupling(state)
        events.extend(recoupling_events(ceremony))
        if ceremony.eliminated_id == state.player.id:
            state.outcome = RunOutcome.ELIMINATED
    if state.phase.value == "evening":
        audience_snapshot = record_audience_snapshot(state)
    if state.phase.value == "evening" and state.day >= 6:
        events.append(final_vote_ceremony(state))
    advance_phase(state)
    events.extend(_scheduled_phase_events(state, rng))
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
            events.append(CeremonyEvent(kind="producer_text", message=producer_text_event_message(state.pending_text)))
    if state.day == 4 and state.phase.value == "morning":
        bombshell = arrive_bombshell(state)
        events.append(
            CeremonyEvent(
                kind="bombshell",
                message=f"Bombshell arrived: {bombshell.name} enters the villa.",
                islander_id=bombshell.id,
            )
        )
    return events
