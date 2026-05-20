"""Deterministic checks for golden LLM eval scenarios."""

from __future__ import annotations

from src.game.agents.contextual_options import validate_follow_up_menu
from src.game.agents.event_narrator import validate_event_narration
from src.game.agents.islander_voice import islander_voice_context, validate_exchange
from src.game.engine.actions import ActionKind
from src.game.eval.golden_models import GoldenCheckResult, GoldenTurnSpec
from src.game.state.models import GameState, MemoryBatch

# Actions that legitimately change the couple list. Other kinds must not
# change couples — if they do, the agent layer leaked into engine state.
COUPLE_CHANGING_KINDS: frozenset[ActionKind] = frozenset(
    {
        ActionKind.RECOUPLE,
        ActionKind.PROPOSE_RECOUPLE,
        ActionKind.CASA_DECISION,
        ActionKind.NPC_PROPOSAL_RESPONSE,
        ActionKind.JOIN_GATHER,
    }
)


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
            return _check_engine_state_invariants(turn_spec, turn, pre_state)
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
            return _pass(
                check_id,
                "villa orchestrator commit recorded (starts/continues/ends/movements counted in actual output)",
                turn_spec.id,
            )
        if check_id == "background_kind_isolated":
            offenders: list[str] = []
            for batch in turn.agent_commits.curator_batches:
                if batch.kind != "background":
                    continue
                for memory in batch.memories:
                    if memory.holder_id == "player" and memory.source == "direct":
                        offenders.append(
                            f"batch kind=background but direct player memory present: {memory.content!r}"
                        )
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
        if check_id == "pull_recorded":
            attempt = turn.mechanical_result.pull_attempt
            if attempt is None:
                return _fail(check_id, "no pull attempt was recorded", turn_spec.id)
            return _pass(
                check_id,
                f"pull recorded for {attempt.target_id}: roll {attempt.roll} vs chance {attempt.chance}, success={attempt.success}",
                turn_spec.id,
            )
        if check_id == "pull_succeeded":
            attempt = turn.mechanical_result.pull_attempt
            if attempt is None:
                return _fail(check_id, "no pull attempt was recorded", turn_spec.id)
            if not attempt.success:
                return _fail(
                    check_id,
                    f"pull was rejected: roll {attempt.roll} vs chance {attempt.chance}",
                    turn_spec.id,
                )
            return _pass(
                check_id,
                f"pull succeeded: roll {attempt.roll} vs chance {attempt.chance}",
                turn_spec.id,
            )
        if check_id == "pull_rejected":
            attempt = turn.mechanical_result.pull_attempt
            if attempt is None:
                return _fail(check_id, "no pull attempt was recorded", turn_spec.id)
            if attempt.success:
                return _fail(
                    check_id,
                    f"pull unexpectedly succeeded: roll {attempt.roll} vs chance {attempt.chance}",
                    turn_spec.id,
                )
            return _pass(
                check_id,
                f"pull rejected as expected: roll {attempt.roll} vs chance {attempt.chance}",
                turn_spec.id,
            )
        if check_id == "npc_conversation_still_active":
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
                return _fail(
                    check_id,
                    f"NPC conversation {blocked_id} is no longer active after the rejected pull",
                    turn_spec.id,
                )
            return _pass(
                check_id, f"NPC conversation {blocked_id} remains active", turn_spec.id
            )
        if check_id == "no_agent_validation_retries":
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
        return GoldenCheckResult(
            id=check_id,
            kind="deterministic",
            result="cannot_determine",
            reason=f"unknown deterministic check: {check_id}",
            turn_id=turn_spec.id,
        )
    except ValueError as exc:
        return _fail(check_id, str(exc), turn_spec.id)


def _check_engine_state_invariants(
    turn_spec: GoldenTurnSpec,
    turn: object,
    pre_state: GameState | None,
) -> GoldenCheckResult:
    """Catch agents that quietly rewrite deterministic state.

    Player identity, schema/seed, eliminations, and the couple list are
    engine-owned. Agents return typed commits; only the engine applies them
    and only when the action kind authorizes the change.
    """
    from src.game.engine.turn import TurnResult

    if not isinstance(turn, TurnResult):
        return _fail("engine_state_invariants_preserved", "turn did not produce a TurnResult", turn_spec.id)
    if pre_state is None:
        return GoldenCheckResult(
            id="engine_state_invariants_preserved",
            kind="deterministic",
            result="cannot_determine",
            reason="pre_state was not captured for this turn",
            turn_id=turn_spec.id,
        )
    post = turn.state
    violations: list[str] = []
    if post.schema_version != pre_state.schema_version:
        violations.append(
            f"schema_version changed: {pre_state.schema_version} -> {post.schema_version}"
        )
    if post.seed != pre_state.seed:
        violations.append(f"seed changed: {pre_state.seed} -> {post.seed}")
    if post.player.id != pre_state.player.id:
        violations.append(f"player.id changed: {pre_state.player.id} -> {post.player.id}")
    if post.player.gender != pre_state.player.gender:
        violations.append(
            f"player.gender changed: {pre_state.player.gender} -> {post.player.gender}"
        )
    if post.player.archetype_id != pre_state.player.archetype_id:
        violations.append(
            f"player.archetype_id changed: {pre_state.player.archetype_id} -> {post.player.archetype_id}"
        )
    pre_eliminated = {
        islander.id for islander in pre_state.islanders if islander.eliminated
    }
    post_eliminated = {islander.id for islander in post.islanders if islander.eliminated}
    resurrected = pre_eliminated - post_eliminated
    if resurrected:
        violations.append(f"eliminated Heartbreakers were brought back: {sorted(resurrected)}")
    action_kind = turn.mechanical_result.action.kind
    couples_changed = _couple_set(pre_state) != _couple_set(post)
    if couples_changed and action_kind not in COUPLE_CHANGING_KINDS:
        violations.append(
            f"couples changed under action {action_kind.value!r} — only "
            f"{sorted(kind.value for kind in COUPLE_CHANGING_KINDS)} may move the couple list"
        )
    if violations:
        return GoldenCheckResult(
            id="engine_state_invariants_preserved",
            kind="deterministic",
            result="fail",
            reason=f"{len(violations)} engine-state invariant(s) violated",
            evidence="\n".join(violations),
            turn_id=turn_spec.id,
        )
    return _pass(
        "engine_state_invariants_preserved",
        "player identity, schema, seed, eliminations, and couples respect the engine boundary",
        turn_spec.id,
    )


def _couple_set(state: GameState) -> set[tuple[str, str]]:
    couples: set[tuple[str, str]] = set()
    for couple in state.couples:
        pair = sorted((couple.partner_a_id, couple.partner_b_id))
        couples.add((pair[0], pair[1]))
    return couples


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


def _pass(check_id: str, reason: str, turn_id: str) -> GoldenCheckResult:
    return GoldenCheckResult(id=check_id, kind="deterministic", result="pass", reason=reason, turn_id=turn_id)


def _fail(check_id: str, reason: str, turn_id: str) -> GoldenCheckResult:
    return GoldenCheckResult(id=check_id, kind="deterministic", result="fail", reason=reason, turn_id=turn_id)
