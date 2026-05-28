"""Deterministic checks for golden LLM eval scenarios."""

from __future__ import annotations

from src.game.agents.contextual_options import validate_follow_up_menu
from src.game.agents.event_narrator import validate_event_narration
from src.game.agents.islander_voice import islander_voice_context, validate_exchange
from src.game.engine.actions import ActionKind
from src.game.eval.golden_models import GoldenCheckResult, GoldenTurnSpec
from src.game.eval.golden_state_checks import (
    check_active_conversation_target,
    check_audience_delta,
    check_ceremony_event_present,
    check_couple_present,
    check_engine_state_invariants,
    check_forced_movement,
    check_hideaway_consumed,
    check_pending_npc_proposal_cleared,
    check_pending_npc_proposal_from,
    check_proposal_outcome,
    check_relationship_delta,
)
from src.game.state.models import GameState, MemoryBatch


def run_deterministic_check(
    check_id: str,
    *,
    turn_spec: GoldenTurnSpec,
    turn: object,
    llm_mode: str,
    pre_state: GameState | None = None,
) -> GoldenCheckResult:
    """Run one deterministic golden-eval check."""
    from src.game.engine.turn import TurnResult

    if not isinstance(turn, TurnResult):
        return _fail(check_id, "turn did not produce a TurnResult", turn_spec.id)
    try:
        if check_id == "exchange_valid":
            if turn.exchange is None:
                return _fail(check_id, "turn has no exchange", turn_spec.id)
            validation_state = turn.state if pre_state is None else pre_state
            validate_exchange(turn.exchange, islander_voice_context(validation_state, turn.mechanical_result))
            return _pass(check_id, "exchange validates", turn_spec.id)
        if check_id == "follow_up_menu_valid":
            if turn.follow_up_menu is None:
                return _fail(check_id, "turn has no follow-up menu", turn_spec.id)
            validate_follow_up_menu(turn.follow_up_menu)
            return _pass(check_id, "follow-up menu validates", turn_spec.id)
        if check_id == "exactly_one_exit":
            menu = turn.follow_up_menu
            if menu is None:
                return _fail(check_id, "turn has no follow-up menu", turn_spec.id)
            count = sum(option.category == "exit" for option in menu.options)
            if count != 1:
                return _fail(check_id, f"expected one exit option, found {count}", turn_spec.id)
            return _pass(check_id, "follow-up menu has exactly one exit", turn_spec.id)
        if check_id == "conversation_active":
            target_id = turn.mechanical_result.action.target_id
            active = turn.state.active_conversation
            if active is None or active.target_id != target_id:
                return _fail(check_id, "active conversation target did not match action", turn_spec.id)
            return _pass(check_id, "conversation remains active with target", turn_spec.id)
        if check_id == "conversation_closed":
            if turn.state.active_conversation is not None:
                return _fail(check_id, "active conversation is still open", turn_spec.id)
            return _pass(check_id, "conversation is closed", turn_spec.id)
        if check_id == "curator_memories":
            return _check_curator_memories(turn_spec, turn)
        if check_id.startswith("curator_memories_for:"):
            return _check_curator_memories_for(check_id, turn_spec, turn)
        if check_id == "no_exchange":
            if turn.exchange is not None:
                return _fail(check_id, "turn unexpectedly produced an exchange", turn_spec.id)
            return _pass(check_id, "turn produced no Islander Voice exchange", turn_spec.id)
        if check_id == "event_narration_valid":
            if turn.event_narration is None:
                return _fail(check_id, "turn has no event narration", turn_spec.id)
            validate_event_narration(turn.event_narration, turn.ceremony_events)
            return _pass(check_id, "event narration validates", turn_spec.id)
        if check_id == "event_narration_present":
            if turn.event_narration is None:
                return _fail(check_id, "turn has no event narration", turn_spec.id)
            return _pass(check_id, "event narration is present", turn_spec.id)
        if check_id == "ceremony_events_present":
            if not turn.ceremony_events:
                return _fail(check_id, "turn has no ceremony events", turn_spec.id)
            return _pass(check_id, f"{len(turn.ceremony_events)} ceremony event(s) recorded", turn_spec.id)
        if check_id == "pending_gather_waiting":
            if turn.state.pending_gather is None:
                return _fail(check_id, "state has no pending gather", turn_spec.id)
            return _pass(check_id, f"pending gather: {turn.state.pending_gather.kind}", turn_spec.id)
        if check_id == "challenge_resolved":
            challenge = turn.state.pending_challenge
            if challenge is None or challenge.result is None:
                return _fail(check_id, "challenge is not resolved", turn_spec.id)
            return _pass(check_id, f"challenge result: {challenge.result}", turn_spec.id)
        if check_id == "challenge_cleared":
            if turn.state.pending_challenge is not None:
                return _fail(check_id, "resolved challenge is still visible", turn_spec.id)
            return _pass(check_id, "resolved challenge is no longer visible", turn_spec.id)
        if check_id == "casa_active":
            if turn.state.casa_amor_state is None or turn.state.casa_amor_state.returned:
                return _fail(check_id, "Casa Amor is not active", turn_spec.id)
            return _pass(check_id, "Casa Amor is active", turn_spec.id)
        if check_id == "run_outcome_present":
            if turn.state.outcome is None:
                return _fail(check_id, "run outcome is not set", turn_spec.id)
            return _pass(check_id, f"run outcome: {turn.state.outcome.value}", turn_spec.id)
        if check_id.startswith("location_is:"):
            expected = check_id.removeprefix("location_is:")
            actual = turn.state.location_id.value
            if actual != expected:
                return _fail(check_id, f"expected location {expected}, got {actual}", turn_spec.id)
            return _pass(check_id, f"location is {actual}", turn_spec.id)
        if check_id.startswith("active_conversation_target_is:"):
            return check_active_conversation_target(check_id, turn_spec, turn)
        if check_id.startswith("relationship_delta:"):
            return check_relationship_delta(check_id, turn_spec, turn)
        if check_id.startswith("ceremony_event_present:"):
            return check_ceremony_event_present(check_id, turn_spec, turn)
        if check_id.startswith("forced_movement_present:"):
            return check_forced_movement(check_id, turn_spec, turn)
        if check_id.startswith("pending_npc_proposal_from:"):
            return check_pending_npc_proposal_from(check_id, turn_spec, turn)
        if check_id == "pending_npc_proposal_cleared":
            return check_pending_npc_proposal_cleared(check_id, turn_spec, turn)
        if check_id.startswith("proposal_outcome_is:"):
            return check_proposal_outcome(check_id, turn_spec, turn)
        if check_id.startswith("couple_present:"):
            return check_couple_present(check_id, turn_spec, turn)
        if check_id.startswith("audience_delta:"):
            return check_audience_delta(check_id, turn_spec, turn)
        if check_id.startswith("hideaway_consumed:"):
            return check_hideaway_consumed(check_id, turn_spec, turn, pre_state)
        if check_id.startswith("visible_targets_include:"):
            expected_ids = {
                item.strip()
                for item in check_id.removeprefix("visible_targets_include:").split(",")
                if item.strip()
            }
            visible_ids = {
                islander.id
                for islander in turn.state.islanders
                if islander.location_id == turn.state.location_id and not islander.eliminated
            }
            missing = expected_ids - visible_ids
            if missing:
                return _fail(check_id, f"missing visible target(s): {sorted(missing)}", turn_spec.id)
            return _pass(check_id, f"visible targets include {sorted(expected_ids)}", turn_spec.id)
        if check_id == "agent_traces_present":
            if llm_mode == "mock":
                return _pass(check_id, "mock mode does not emit live agent traces", turn_spec.id)
            if not turn.agent_traces:
                return _fail(check_id, "real LLM turn has no agent traces", turn_spec.id)
            return _pass(check_id, f"captured {len(turn.agent_traces)} agent trace(s)", turn_spec.id)
        if check_id == "engine_state_invariants_preserved":
            return check_engine_state_invariants(turn_spec, turn, pre_state)
        if check_id == "interruption_cleared":
            conversation = turn.state.active_conversation
            if conversation is not None and conversation.pending_interruption is not None:
                return _fail(
                    check_id,
                    "pending_interruption is still set after the interruption response",
                    turn_spec.id,
                )
            return _pass(check_id, "pending_interruption was cleared by the engine", turn_spec.id)
        if check_id == "villa_update_committed":
            commit = turn.agent_commits.villa_update
            if commit is None:
                return _fail(check_id, "no villa update was committed", turn_spec.id)
            return _pass(check_id, "villa orchestrator commit recorded", turn_spec.id)
        if check_id == "background_kind_isolated":
            return _check_background_kind_isolated(check_id, turn_spec, turn)
        if check_id == "pull_recorded":
            return _check_pull_recorded(check_id, turn_spec, turn)
        if check_id == "pull_succeeded":
            return _check_pull_outcome(check_id, turn_spec, turn, expected=True)
        if check_id == "pull_rejected":
            return _check_pull_outcome(check_id, turn_spec, turn, expected=False)
        if check_id == "npc_conversation_still_active":
            return _check_npc_conversation_still_active(check_id, turn_spec, turn)
        if check_id == "npc_conversation_closed":
            return _check_npc_conversation_closed(check_id, turn_spec, turn)
        if check_id == "pull_rejection_witness_memory":
            return _check_pull_rejection_witness_memory(check_id, turn_spec, turn)
        if check_id == "no_agent_validation_retries":
            return _check_no_agent_validation_retries(check_id, turn_spec, turn, llm_mode)
        return GoldenCheckResult(
            id=check_id,
            kind="deterministic",
            result="cannot_determine",
            reason=f"unknown deterministic check: {check_id}",
            turn_id=turn_spec.id,
        )
    except ValueError as exc:
        return _fail(check_id, str(exc), turn_spec.id)


def _check_background_kind_isolated(
    check_id: str,
    turn_spec: GoldenTurnSpec,
    turn: object,
) -> GoldenCheckResult:
    offenders: list[str] = []
    for batch in turn.agent_commits.curator_batches:
        if batch.kind != "background":
            continue
        for memory in batch.memories:
            if memory.holder_id == "player" and memory.source == "direct":
                offenders.append(f"batch kind=background but direct player memory present: {memory.content!r}")
    if offenders:
        return GoldenCheckResult(
            id=check_id,
            kind="deterministic",
            result="fail",
            reason="background curator batches must not write direct player memories",
            evidence="\n".join(offenders),
            turn_id=turn_spec.id,
        )
    return _pass(check_id, "background batches keep player memories witnessed-only", turn_spec.id)


def _check_pull_recorded(check_id: str, turn_spec: GoldenTurnSpec, turn: object) -> GoldenCheckResult:
    attempt = turn.mechanical_result.pull_attempt
    if attempt is None:
        return _fail(check_id, "no pull attempt was recorded", turn_spec.id)
    return _pass(
        check_id,
        f"pull recorded for {attempt.target_id}: roll {attempt.roll} vs chance {attempt.chance}, success={attempt.success}",
        turn_spec.id,
    )


def _check_pull_outcome(
    check_id: str,
    turn_spec: GoldenTurnSpec,
    turn: object,
    *,
    expected: bool,
) -> GoldenCheckResult:
    attempt = turn.mechanical_result.pull_attempt
    if attempt is None:
        return _fail(check_id, "no pull attempt was recorded", turn_spec.id)
    if attempt.success is not expected:
        label = "succeeded" if attempt.success else "rejected"
        return _fail(check_id, f"pull was {label}: roll {attempt.roll} vs chance {attempt.chance}", turn_spec.id)
    label = "succeeded" if expected else "rejected"
    return _pass(check_id, f"pull {label}: roll {attempt.roll} vs chance {attempt.chance}", turn_spec.id)


def _check_npc_conversation_still_active(
    check_id: str,
    turn_spec: GoldenTurnSpec,
    turn: object,
) -> GoldenCheckResult:
    blocked_id = (
        turn.mechanical_result.pull_attempt.blocked_conversation_id
        if turn.mechanical_result.pull_attempt is not None
        else None
    )
    if blocked_id is None:
        return _fail(check_id, "no blocked NPC conversation recorded", turn_spec.id)
    still_active = any(
        conversation.id == blocked_id and conversation.status == "active"
        for conversation in turn.state.npc_conversations
    )
    if not still_active:
        return _fail(check_id, f"NPC conversation {blocked_id} is no longer active", turn_spec.id)
    return _pass(check_id, f"NPC conversation {blocked_id} remains active", turn_spec.id)


def _check_npc_conversation_closed(
    check_id: str,
    turn_spec: GoldenTurnSpec,
    turn: object,
) -> GoldenCheckResult:
    blocked_id = (
        turn.mechanical_result.pull_attempt.blocked_conversation_id
        if turn.mechanical_result.pull_attempt is not None
        else None
    )
    if blocked_id is None:
        return _fail(check_id, "no blocked NPC conversation recorded", turn_spec.id)
    still_present = any(conversation.id == blocked_id for conversation in turn.state.npc_conversations)
    if still_present:
        return _fail(check_id, f"NPC conversation {blocked_id} is still present", turn_spec.id)
    return _pass(check_id, f"NPC conversation {blocked_id} was removed after the pull", turn_spec.id)


def _check_pull_rejection_witness_memory(
    check_id: str,
    turn_spec: GoldenTurnSpec,
    turn: object,
) -> GoldenCheckResult:
    attempt = turn.mechanical_result.pull_attempt
    if attempt is None:
        return _fail(check_id, "no pull attempt was recorded", turn_spec.id)
    holders = [
        islander.id
        for islander in turn.state.islanders
        for memory in islander.memories
        if "saw_pull_rejected" in memory.tags and attempt.target_id in memory.tags
    ]
    if not holders:
        return _fail(check_id, f"no witness memory recorded for rejected pull of {attempt.target_id}", turn_spec.id)
    return _pass(check_id, f"rejected pull witness memory recorded by {sorted(holders)}", turn_spec.id)


def _check_no_agent_validation_retries(
    check_id: str,
    turn_spec: GoldenTurnSpec,
    turn: object,
    llm_mode: str,
) -> GoldenCheckResult:
    if llm_mode == "mock":
        return _pass(check_id, "mock mode has no live validation retries", turn_spec.id)
    errors = [
        f"{trace.agent_name} attempt {trace.attempt}: {trace.validation_error}"
        for trace in turn.agent_traces
        if trace.validation_error
    ]
    if errors:
        return GoldenCheckResult(
            id=check_id,
            kind="deterministic",
            result="fail",
            reason=f"{len(errors)} live agent validation retry/retries occurred",
            evidence="\n".join(errors),
            turn_id=turn_spec.id,
        )
    return _pass(check_id, "no live agent validation retries", turn_spec.id)


def _check_curator_memories(turn_spec: GoldenTurnSpec, turn: object) -> GoldenCheckResult:
    from src.game.engine.turn import TurnResult

    if not isinstance(turn, TurnResult):
        return _fail("curator_memories", "turn did not produce a TurnResult", turn_spec.id)
    target_id = turn.mechanical_result.action.target_id
    participant_ids = {"player", target_id} if target_id is not None else {"player"}
    batches: list[MemoryBatch] = turn.agent_commits.curator_batches
    if not batches:
        return _fail("curator_memories", "no curator batches recorded", turn_spec.id)
    if turn.mechanical_result.action.kind is ActionKind.END_CONVERSATION:
        has_player_close = any(
            "player" in {memory.holder_id for memory in batch.memories}
            and any(memory.holder_id != "player" for memory in batch.memories)
            for batch in batches
        )
        if not has_player_close:
            return _fail(
                "curator_memories",
                "conversation close did not record both player and NPC memories",
                turn_spec.id,
            )
        return _pass("curator_memories", "conversation close memories were recorded", turn_spec.id)
    holders = {memory.holder_id for batch in batches for memory in batch.memories}
    missing = {holder for holder in participant_ids if holder is not None} - holders
    if missing:
        return _fail("curator_memories", f"missing memory holders: {sorted(missing)}", turn_spec.id)
    return _pass("curator_memories", "participant memories were recorded", turn_spec.id)


def _check_curator_memories_for(
    check_id: str,
    turn_spec: GoldenTurnSpec,
    turn: object,
) -> GoldenCheckResult:
    target_id = check_id.removeprefix("curator_memories_for:")
    holders = {
        memory.holder_id
        for batch in turn.agent_commits.curator_batches
        for memory in batch.memories
        if memory.subject_id in {target_id, "player"} and memory.holder_id in {target_id, "player"}
    }
    if {"player", target_id} - holders:
        return _fail(check_id, f"missing curator memories for player/{target_id}: {sorted(holders)}", turn_spec.id)
    return _pass(check_id, f"curator memories include player and {target_id}", turn_spec.id)


def _pass(check_id: str, reason: str, turn_id: str) -> GoldenCheckResult:
    return GoldenCheckResult(id=check_id, kind="deterministic", result="pass", reason=reason, turn_id=turn_id)


def _fail(check_id: str, reason: str, turn_id: str) -> GoldenCheckResult:
    return GoldenCheckResult(id=check_id, kind="deterministic", result="fail", reason=reason, turn_id=turn_id)
