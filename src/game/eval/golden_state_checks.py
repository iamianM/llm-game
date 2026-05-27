"""State-focused deterministic checks for golden LLM evals."""

from __future__ import annotations

from src.game.engine.actions import ActionKind
from src.game.engine.couples import player_couple
from src.game.engine.state_access import find_islander
from src.game.eval.golden_models import GoldenCheckResult, GoldenTurnSpec
from src.game.state.models import GameState, Location

COUPLE_CHANGING_KINDS: frozenset[ActionKind] = frozenset(
    {
        ActionKind.RECOUPLE,
        ActionKind.PROPOSE_RECOUPLE,
        ActionKind.CASA_DECISION,
        ActionKind.NPC_PROPOSAL_RESPONSE,
        ActionKind.JOIN_GATHER,
    }
)


def check_active_conversation_target(
    check_id: str,
    turn_spec: GoldenTurnSpec,
    turn: object,
) -> GoldenCheckResult:
    from src.game.engine.turn import TurnResult

    if not isinstance(turn, TurnResult):
        return _fail(check_id, "turn did not produce a TurnResult", turn_spec.id)
    expected = check_id.removeprefix("active_conversation_target_is:")
    active = turn.state.active_conversation
    if active is None:
        return _fail(check_id, "no active conversation", turn_spec.id)
    if active.target_id != expected:
        return _fail(check_id, f"expected active target {expected}, got {active.target_id}", turn_spec.id)
    return _pass(check_id, f"active conversation target is {expected}", turn_spec.id)


def check_relationship_delta(
    check_id: str,
    turn_spec: GoldenTurnSpec,
    turn: object,
) -> GoldenCheckResult:
    from src.game.engine.turn import TurnResult

    if not isinstance(turn, TurnResult):
        return _fail(check_id, "turn did not produce a TurnResult", turn_spec.id)
    parts = check_id.split(":")
    if len(parts) != 4:
        return _fail(check_id, "expected relationship_delta:<target>:<field>:<amount>", turn_spec.id)
    _, target_id, field, raw_amount = parts
    if field not in {"affection", "chemistry", "trust", "friendship"}:
        return _fail(check_id, f"unknown relationship field: {field}", turn_spec.id)
    try:
        expected = int(raw_amount)
    except ValueError:
        return _fail(check_id, f"invalid delta amount: {raw_amount}", turn_spec.id)
    delta = turn.mechanical_result.relationship_deltas.get(target_id)
    if delta is None:
        return _fail(check_id, f"no relationship delta for {target_id}", turn_spec.id)
    actual = getattr(delta, field)
    if actual != expected:
        return _fail(check_id, f"expected {target_id}.{field} delta {expected}, got {actual}", turn_spec.id)
    return _pass(check_id, f"{target_id}.{field} delta is {expected}", turn_spec.id)


def check_ceremony_event_present(
    check_id: str,
    turn_spec: GoldenTurnSpec,
    turn: object,
) -> GoldenCheckResult:
    from src.game.engine.turn import TurnResult

    if not isinstance(turn, TurnResult):
        return _fail(check_id, "turn did not produce a TurnResult", turn_spec.id)
    expected = check_id.removeprefix("ceremony_event_present:")
    matching = [event for event in turn.ceremony_events if event.kind == expected]
    if not matching:
        found = [event.kind for event in turn.ceremony_events]
        return _fail(check_id, f"expected event {expected}, found {found}", turn_spec.id)
    return _pass(check_id, f"ceremony event present: {expected}", turn_spec.id)


def check_forced_movement(
    check_id: str,
    turn_spec: GoldenTurnSpec,
    turn: object,
) -> GoldenCheckResult:
    from src.game.engine.turn import TurnResult

    if not isinstance(turn, TurnResult):
        return _fail(check_id, "turn did not produce a TurnResult", turn_spec.id)
    parts = check_id.split(":")
    if len(parts) != 3:
        return _fail(check_id, "expected forced_movement_present:<actor>:<kind>", turn_spec.id)
    _, actor_id, kind = parts
    for movement in turn.mechanical_result.forced_movements:
        if movement.actor_id == actor_id and movement.kind == kind:
            return _pass(check_id, f"forced movement present for {actor_id}: {kind}", turn_spec.id)
    found = [f"{movement.actor_id}:{movement.kind}" for movement in turn.mechanical_result.forced_movements]
    return _fail(check_id, f"forced movement not found; found {found}", turn_spec.id)


def check_pending_npc_proposal_from(
    check_id: str,
    turn_spec: GoldenTurnSpec,
    turn: object,
) -> GoldenCheckResult:
    from src.game.engine.turn import TurnResult

    if not isinstance(turn, TurnResult):
        return _fail(check_id, "turn did not produce a TurnResult", turn_spec.id)
    expected = check_id.removeprefix("pending_npc_proposal_from:")
    pending = turn.state.pending_recouple_proposal
    if pending is None:
        return _fail(check_id, "no pending NPC proposal", turn_spec.id)
    if pending.proposer_id != expected:
        return _fail(check_id, f"expected proposer {expected}, got {pending.proposer_id}", turn_spec.id)
    return _pass(check_id, f"pending NPC proposal from {expected}", turn_spec.id)


def check_pending_npc_proposal_cleared(
    check_id: str,
    turn_spec: GoldenTurnSpec,
    turn: object,
) -> GoldenCheckResult:
    from src.game.engine.turn import TurnResult

    if not isinstance(turn, TurnResult):
        return _fail(check_id, "turn did not produce a TurnResult", turn_spec.id)
    if turn.state.pending_recouple_proposal is not None:
        pending = turn.state.pending_recouple_proposal
        return _fail(check_id, f"pending proposal still waiting from {pending.proposer_id}", turn_spec.id)
    return _pass(check_id, "pending NPC proposal cleared", turn_spec.id)


def check_proposal_outcome(
    check_id: str,
    turn_spec: GoldenTurnSpec,
    turn: object,
) -> GoldenCheckResult:
    from src.game.engine.turn import TurnResult

    if not isinstance(turn, TurnResult):
        return _fail(check_id, "turn did not produce a TurnResult", turn_spec.id)
    expected = check_id.removeprefix("proposal_outcome_is:")
    if expected not in {"accepted", "rejected"}:
        return _fail(check_id, "expected proposal_outcome_is:<accepted|rejected>", turn_spec.id)
    outcome = turn.mechanical_result.proposal_outcome
    if not isinstance(outcome, dict):
        return _fail(check_id, "turn has no proposal outcome", turn_spec.id)
    actual = "accepted" if outcome.get("accepted") is True else "rejected"
    if actual != expected:
        return _fail(check_id, f"expected proposal {expected}, got {actual}", turn_spec.id)
    return _pass(check_id, f"proposal outcome is {expected}", turn_spec.id)


def check_couple_present(
    check_id: str,
    turn_spec: GoldenTurnSpec,
    turn: object,
) -> GoldenCheckResult:
    from src.game.engine.turn import TurnResult

    if not isinstance(turn, TurnResult):
        return _fail(check_id, "turn did not produce a TurnResult", turn_spec.id)
    parts = check_id.split(":")
    if len(parts) != 3:
        return _fail(check_id, "expected couple_present:<first>:<second>", turn_spec.id)
    _, first_id, second_id = parts
    expected = tuple(sorted((first_id, second_id)))
    for couple in turn.state.couples:
        actual = tuple(sorted((couple.partner_a_id, couple.partner_b_id)))
        if actual == expected:
            return _pass(check_id, f"couple present: {first_id}/{second_id}", turn_spec.id)
    found = [f"{couple.partner_a_id}/{couple.partner_b_id}" for couple in turn.state.couples]
    return _fail(check_id, f"couple not found; found {found}", turn_spec.id)


def check_audience_delta(
    check_id: str,
    turn_spec: GoldenTurnSpec,
    turn: object,
) -> GoldenCheckResult:
    from src.game.engine.turn import TurnResult

    if not isinstance(turn, TurnResult):
        return _fail(check_id, "turn did not produce a TurnResult", turn_spec.id)
    raw_expected = check_id.removeprefix("audience_delta:")
    try:
        expected = int(raw_expected)
    except ValueError:
        return _fail(check_id, f"invalid audience delta: {raw_expected}", turn_spec.id)
    actual = turn.mechanical_result.audience_delta
    if actual != expected:
        return _fail(check_id, f"expected audience delta {expected}, got {actual}", turn_spec.id)
    return _pass(check_id, f"audience delta is {expected}", turn_spec.id)


def check_hideaway_consumed(
    check_id: str,
    turn_spec: GoldenTurnSpec,
    turn: object,
    pre_state: GameState | None,
) -> GoldenCheckResult:
    from src.game.engine.turn import TurnResult

    if not isinstance(turn, TurnResult):
        return _fail(check_id, "turn did not produce a TurnResult", turn_spec.id)
    expected_partner_id = check_id.removeprefix("hideaway_consumed:")
    state = turn.state
    hideaway = state.hideaway
    violations: list[str] = []
    if hideaway.partner_id != expected_partner_id:
        violations.append(f"partner_id expected {expected_partner_id}, got {hideaway.partner_id}")
    if hideaway.used_on_day is None:
        violations.append("used_on_day was not set")
    elif pre_state is not None and hideaway.used_on_day != pre_state.day:
        violations.append(f"used_on_day expected {pre_state.day}, got {hideaway.used_on_day}")
    if not hideaway.deltas_applied:
        violations.append("deltas_applied is false")
    if state.location_id is not Location.HIDEAWAY:
        violations.append(f"player location expected hideaway, got {state.location_id.value}")
    partner = find_islander(state, expected_partner_id)
    if partner.location_id is not Location.HIDEAWAY:
        violations.append(f"{expected_partner_id} location expected hideaway, got {partner.location_id.value}")
    couple = player_couple(state)
    if couple is None or not couple.has_used_hideaway:
        violations.append("player couple did not record has_used_hideaway")
    if violations:
        return GoldenCheckResult(
            id=check_id,
            kind="deterministic",
            result="fail",
            reason=f"{len(violations)} Hideaway invariant(s) violated",
            evidence="\n".join(violations),
            turn_id=turn_spec.id,
        )
    return _pass(check_id, f"Hideaway consumed with {expected_partner_id}", turn_spec.id)


def check_engine_state_invariants(
    turn_spec: GoldenTurnSpec,
    turn: object,
    pre_state: GameState | None,
) -> GoldenCheckResult:
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
        violations.append(f"schema_version changed: {pre_state.schema_version} -> {post.schema_version}")
    if post.seed != pre_state.seed:
        violations.append(f"seed changed: {pre_state.seed} -> {post.seed}")
    if post.player.id != pre_state.player.id:
        violations.append(f"player.id changed: {pre_state.player.id} -> {post.player.id}")
    if post.player.gender != pre_state.player.gender:
        violations.append(f"player.gender changed: {pre_state.player.gender} -> {post.player.gender}")
    if post.player.archetype_id != pre_state.player.archetype_id:
        violations.append(
            f"player.archetype_id changed: {pre_state.player.archetype_id} -> {post.player.archetype_id}"
        )
    pre_eliminated = {islander.id for islander in pre_state.islanders if islander.eliminated}
    post_eliminated = {islander.id for islander in post.islanders if islander.eliminated}
    resurrected = pre_eliminated - post_eliminated
    if resurrected:
        violations.append(f"eliminated Heartbreakers were brought back: {sorted(resurrected)}")
    action_kind = turn.mechanical_result.action.kind
    couples_changed = _couple_set(pre_state) != _couple_set(post)
    if couples_changed and action_kind not in COUPLE_CHANGING_KINDS:
        violations.append(
            f"couples changed under action {action_kind.value!r} - only "
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


def _pass(check_id: str, reason: str, turn_id: str) -> GoldenCheckResult:
    return GoldenCheckResult(id=check_id, kind="deterministic", result="pass", reason=reason, turn_id=turn_id)


def _fail(check_id: str, reason: str, turn_id: str) -> GoldenCheckResult:
    return GoldenCheckResult(id=check_id, kind="deterministic", result="fail", reason=reason, turn_id=turn_id)
