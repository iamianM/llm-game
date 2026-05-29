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
    ROUND_BASED_MINIGAMES,
    challenge_event_message,
    resolve_challenge,
    schedule_challenge,
)
from src.game.engine.phases import advance_phase
from src.game.engine.producer_events import producer_text_event_message, schedule_producer_text
from src.game.engine.state_access import display_name
from src.game.state.models import (
    AudienceSnapshot,
    Challenge,
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
    if (
        state.phase is Phase.CHALLENGE
        and state.pending_challenge is not None
        and state.pending_challenge.result is not None
    ):
        advance_phase(state)
        events.extend(_scheduled_phase_events(state, rng))
    # Skip an empty TEXT phase. Some days (e.g. Day 5, mid-Flush-of-Hearts)
    # have no scheduled producer text, so nothing gets queued: no pending_text
    # to gather around and no gather. Landing here strands the player on a
    # zero-action screen. Step straight through to EVENING, where the real
    # beat (the Flush-of-Hearts return decision / Pairing Ceremony) surfaces.
    if state.phase is Phase.TEXT and state.pending_text is None and state.pending_gather is None:
        advance_phase(state)
        events.extend(_scheduled_phase_events(state, rng))
    # Clear a fully-resolved challenge once we cross into a NEW DAY. We
    # intentionally keep it alive within the same day so eval check
    # `challenge_resolved` can inspect the post-resolution state and so the
    # narrator/render can surface the wrap once. The CLI renderer in
    # play_render.py keys its minigame view off state.pending_challenge but
    # tolerates the lingering wrap; without this clear it would re-render
    # the wrap every turn for the rest of the run.
    if (
        state.pending_challenge is not None
        and state.pending_challenge.result is not None
        and state.pending_challenge.day != state.day
    ):
        state.pending_challenge = None
    return events, audience_snapshot


def settle_to_playable(state: GameState, rng: SeededRng, *, max_steps: int = 24) -> None:
    """Walk a non-terminal, zero-action state forward until it is playable.

    The live turn pipeline never *serves* a non-terminal state with no
    available actions — it auto-advances within the turn. A freshly loaded
    checkpoint, however, has not run a turn yet, so it can surface on a
    transient boundary (e.g. a pre-event TEXT phase saved before its gather was
    scheduled). This steps the deterministic phase machine forward so the
    main-menu picker can never drop the player onto a dead screen. Bounded by
    ``max_steps`` as a guard against an unforeseen non-terminating state.
    """
    from src.game.engine.actions import available_actions

    steps = 0
    while not state.is_terminal and not available_actions(state) and steps < max_steps:
        advance_phase_with_events(state, rng)
        steps += 1


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
        events.extend(recoupling_events(state, ceremony))
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
            if challenge.kind in ROUND_BASED_MINIGAMES:
                state.pending_challenge = _prepare_round_based_minigame(
                    state, challenge, rng.fork(f"challenge-{state.day}")
                )
            else:
                state.pending_challenge = resolve_challenge(state, challenge, rng.fork(f"challenge-{state.day}"))
            events.append(
                CeremonyEvent(
                    kind="challenge",
                    sub_kind=state.pending_challenge.kind,
                    message=challenge_event_message(state.pending_challenge),
                )
            )
    else:
        raise ValueError(f"unknown pending gather: {gather.model_dump()}")
    state.pending_gather = None
    return events, audience_snapshot


def recoupling_events(state: GameState, ceremony: RecouplingResult) -> list[CeremonyEvent]:
    """Create recoupling and optional dumping events."""
    events = [CeremonyEvent(kind="recoupling", message="The Pairing Ceremony locks in the next couples.")]
    for attempt in ceremony.steal_attempts:
        outcome = "succeeds" if attempt.success else "fails"
        events.append(
            CeremonyEvent(
                kind="steal_attempt",
                message=(
                    f"Heart Throb steal attempt: {display_name(state, attempt.bombshell_id)} "
                    f"tries to steal {display_name(state, attempt.target_id)} from "
                    f"{display_name(state, attempt.abandoned_id)} and {outcome}."
                ),
                islander_id=attempt.bombshell_id,
            )
        )
        if attempt.success:
            events.append(
                CeremonyEvent(
                    kind="partner_stolen",
                    message=(
                        f"Partner stolen: {display_name(state, attempt.target_id)} "
                        f"pairs with {display_name(state, attempt.bombshell_id)}."
                    ),
                    islander_id=attempt.target_id,
                )
            )
    if ceremony.eliminated_id is not None:
        events.append(
            CeremonyEvent(
                kind="elimination",
                message=f"Heart Out: {display_name(state, ceremony.eliminated_id)} leaves Sunset Bay.",
                islander_id=ceremony.eliminated_id,
            )
        )
    return events


def challenge_response_event(state: GameState) -> CeremonyEvent | None:
    """Return a narratable event for a fully-resolved minigame.

    Round-based minigames advance through several rounds; only fire the
    ceremony event (which triggers the Event Narrator to write a wrap)
    once the challenge has actually resolved. Otherwise every round's
    response would generate a "the quiz hangs over the villa..." wrap
    paragraph mid-quiz, which reads as broken.
    """
    if state.pending_challenge is None:
        return None
    if state.pending_challenge.result is None:
        return None
    return CeremonyEvent(
        kind="challenge",
        sub_kind=state.pending_challenge.kind,
        message=challenge_event_message(state.pending_challenge),
    )


def _scheduled_phase_events(state: GameState, rng: SeededRng) -> list[CeremonyEvent]:
    events: list[CeremonyEvent] = []
    if state.phase.value == "challenge":
        challenge = schedule_challenge(state.day)
        if challenge is not None:
            state.pending_challenge = challenge
            if challenge.kind in ROUND_BASED_MINIGAMES:
                state.pending_challenge = _prepare_round_based_minigame(
                    state, challenge, rng.fork(f"challenge-{state.day}")
                )
            elif challenge.kind != "snog_marry_pie":
                state.pending_challenge = resolve_challenge(state, challenge, rng.fork(f"challenge-{state.day}"))
            events.append(
                CeremonyEvent(
                    kind="challenge",
                    sub_kind=state.pending_challenge.kind,
                    message=challenge_event_message(state.pending_challenge),
                )
            )
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
        message=f"Everyone is called to the firepit for {_event_label(event_id)}.",
    )


def _event_label(event_id: str) -> str:
    if event_id == "casa_return":
        return "the Sunset Bay return"
    if event_id == "final_vote":
        return "the Final Vote"
    if event_id == "casa_amor_announce":
        return "Flush of Hearts"
    if event_id.startswith("recoupling"):
        return "a Pairing Ceremony"
    return event_id.replace("_", " ")


def _prepare_round_based_minigame(
    state: GameState,
    challenge: Challenge,
    rng: SeededRng,
) -> Challenge:
    """Build rounds and participants for a round-based minigame.

    Currently dispatches only ``compatibility_quiz``; new minigames join the
    ``ROUND_BASED_MINIGAMES`` set in :mod:`src.game.engine.challenges` and add
    their own branch here.
    """
    if challenge.kind == "compatibility_quiz":
        from src.game.engine.compatibility_quiz import build_rounds, quiz_partner_id
        from src.game.engine.question_bank import ensure_question_bank
        ensure_question_bank(state)
        partner = quiz_partner_id(state)
        rounds = build_rounds(state, partner, rng)
        return challenge.model_copy(
            update={"rounds": rounds, "participants": ["player", partner]}
        )
    if challenge.kind == "heart_rate":
        from src.game.engine.pulse_race import _partner_id as pulse_partner
        from src.game.engine.pulse_race import _surprise_target_id
        from src.game.engine.pulse_race import build_rounds as pulse_build
        partner = pulse_partner(state) or "chloe"
        rounds = pulse_build(state, partner, rng)
        surprise, _ = _surprise_target_id(state)
        return challenge.model_copy(
            update={"rounds": rounds, "participants": ["player", surprise or partner]}
        )
    if challenge.kind == "snog_marry_pie":
        from src.game.engine.snog_marry_pie import _partner_id as smp_partner
        from src.game.engine.snog_marry_pie import build_rounds as smp_build
        rounds = smp_build(state, rng)
        return challenge.model_copy(
            update={"rounds": rounds, "participants": ["player", smp_partner(state) or ""]}
        )
    if challenge.kind == "mr_and_mrs":
        from src.game.engine.mr_and_mrs import _partner_id as mam_partner
        from src.game.engine.mr_and_mrs import build_rounds as mam_build
        from src.game.engine.question_bank import ensure_question_bank
        ensure_question_bank(state)
        partner = mam_partner(state) or "chloe"
        rounds = mam_build(state, partner, rng)
        return challenge.model_copy(update={"rounds": rounds, "participants": ["player", partner]})
    if challenge.kind == "lie_detector":
        from src.game.engine.lie_detector import _partner_id as ld_partner
        from src.game.engine.lie_detector import build_rounds as ld_build
        partner = ld_partner(state) or "chloe"
        rounds = ld_build(state, partner, rng)
        return challenge.model_copy(update={"rounds": rounds, "participants": ["player", partner]})
    if challenge.kind == "final_couples":
        from src.game.engine.final_couples import _partner_id as fc_partner
        from src.game.engine.final_couples import build_rounds as fc_build
        from src.game.engine.question_bank import ensure_question_bank
        ensure_question_bank(state)
        partner = fc_partner(state) or "chloe"
        rounds = fc_build(state, partner, rng)
        return challenge.model_copy(update={"rounds": rounds, "participants": ["player", partner]})
    raise ValueError(f"unsupported round-based minigame: {challenge.kind}")

