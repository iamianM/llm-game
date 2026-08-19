"""One full game turn pipeline.

Design sources:
- 03-LLM-Architecture.md: The Handoff Point
- 05-Interaction-System.md: The Interaction Flow

Target flow:
validate action -> apply deterministic rules -> produce MechanicalResult ->
optionally narrate -> persist state and trace -> return next visible actions.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.game.agents.background_dialogue import BackgroundDialogueFn
from src.game.agents.contextual_options import (
    ContextualOptionsFn,
)
from src.game.agents.conversation_curator import ConversationCuratorFn
from src.game.agents.event_narrator import EventNarration, EventNarratorFn, mock_event_narration
from src.game.agents.heartbreaker_voice import (
    Exchange,
    HeartbreakerVoiceFn,
    mock_heartbreaker_voice,
)
from src.game.agents.resort_orchestrator import ResortOrchestratorFn, ResortUpdate
from src.game.agents.runtime import (
    AgentError,
    AgentTrace,
    begin_agent_trace_capture,
    end_agent_trace_capture,
    record_agent_degradation,
)
from src.game.engine.actions import ActionKind, ActionSpec, PlayerAction, available_actions
from src.game.engine.approach import APPROACH_INTENT_KINDS, roll_ambient_approach
from src.game.engine.arrival_rolls import ArrivalRoll
from src.game.engine.ceremonies import CeremonyEvent, initial_coupling, pairing
from src.game.engine.conversation import (
    append_exchange,
    close_conversation,
    departure_probability,
    start_conversation,
)
from src.game.engine.daily_recap import append_daily_recap_if_needed
from src.game.engine.flush_of_hearts import flush_decision_message
from src.game.engine.follow_up_menu import generate_follow_up_menu
from src.game.engine.gather import close_conversations_for_gather, move_everyone_to_gather
from src.game.engine.memory import add_memory_batch, remember_ceremony_events
from src.game.engine.phases import is_finale_evening
from src.game.engine.private_chat import (
    PrivateChatAttempt,
    attempt_private_chat,
    target_in_active_conversation,
)
from src.game.engine.private_chat_turn import (
    private_chat_rejected_result,
    remember_private_chat_rejection,
)
from src.game.engine.private_suite import private_suite_event
from src.game.engine.proposals import maybe_trigger_npc_player_proposal
from src.game.engine.resort import AgentCommits
from src.game.engine.rules import EXIT_INTENT_KINDS, MechanicalResult, apply_action
from src.game.engine.state_access import display_name, player_display_name
from src.game.engine.time_budget import check_auto_advance, deduct_time
from src.game.engine.turn_autonomy import apply_resort_turn
from src.game.engine.turn_curator import (
    bump_target_familiarity,
    curate_npc_conversation,
    curate_player_conversation,
    intro_memory_batch,
    intro_segment_complete,
)
from src.game.engine.turn_events import (
    advance_phase_with_events,
    challenge_response_event,
    pairing_events,
    resolve_pending_gather,
)
from src.game.engine.turn_proposals import close_proposal_conversation, proposal_event
from src.game.state.flush import FlushDecision
from src.game.state.models import (
    AudienceSnapshot,
    Conversation,
    FollowUpMenu,
    GameState,
    MemoryBatch,
    Phase,
    RunOutcome,
)
from src.game.state.rng import SeededRng
from src.game.state.snapshot import state_hash, state_hash_payload


class TurnResult(BaseModel):
    """One completed turn returned to CLI, browser, or tests."""

    model_config = ConfigDict(extra="forbid")

    state: GameState
    mechanical_result: MechanicalResult
    exchange: Exchange | None = None
    event_narration: EventNarration | None = None
    follow_up_menu: FollowUpMenu | None = None
    available_actions: list[ActionSpec]
    state_hash: str
    ceremony_events: list[CeremonyEvent] = []
    curator_batches: list[MemoryBatch] = []
    audience_snapshot: AudienceSnapshot | None = None
    agent_commits: AgentCommits = Field(default_factory=AgentCommits)
    time_cost: int = 0
    auto_advance: bool = False
    arrival_rolls: list[ArrivalRoll] = Field(default_factory=list)
    agent_traces: list[AgentTrace] = Field(default_factory=list)


def _voiced_exchange(
    state: GameState,
    result: MechanicalResult,
    heartbreaker_voice: HeartbreakerVoiceFn | None,
) -> Exchange:
    """Produce the turn's spoken exchange without ever dead-screening the player.

    Heartbreaker Voice is the only turn agent whose output *is* the payload the player
    came for, and it runs on every conversation beat. The live agent retries on
    validation failure and then raises (each failed attempt is recorded in the
    agent trace). A raise here would crash the conversation mid-beat, discarding
    the player's action. On exhaustion we fall back to the deterministic mock voice
    — contract-valid by construction, and it only ever names the present partner so
    it cannot leak hidden cast — so the beat lands a little generically for one turn
    instead of throwing a dead screen.
    """
    if heartbreaker_voice is None:
        exchange = mock_heartbreaker_voice(state, result)
    else:
        try:
            exchange = heartbreaker_voice(state, result)
        except AgentError as exc:
            record_agent_degradation("heartbreaker_voice", exc)
            exchange = mock_heartbreaker_voice(state, result)
    _remember_player_line(state, exchange.player_dialogue)
    return exchange


RECENT_PLAYER_LINE_CAP = 8


def _remember_player_line(state: GameState, line: str) -> None:
    """Track recent player spoken lines resort-wide so Heartbreaker Voice can avoid
    reusing the same opener across *separate* conversations.

    The per-conversation anti-repetition guard only sees lines from the active
    thread, which leaves the one-at-a-time intro round exposed: each heartbreaker is
    a fresh conversation, so without a resort-wide memory the player greets eight
    people in a row with the same "Thought I'd come say hi while it's still
    calm" template. This rolling buffer feeds that guard so the opener varies.
    """
    text = line.strip()
    if not text:
        return
    state.recent_player_lines.append(text)
    if len(state.recent_player_lines) > RECENT_PLAYER_LINE_CAP:
        state.recent_player_lines = state.recent_player_lines[-RECENT_PLAYER_LINE_CAP:]


def _narrated_events(
    state: GameState,
    events: list[CeremonyEvent],
    event_narrator: EventNarratorFn | None,
) -> EventNarration:
    """Narrate ceremony events without dead-screening the moment.

    The Event Narrator retries on validation failure and then raises (each failed
    attempt is recorded in the agent trace). Ceremonies are high-stakes beats, so a
    raise here would crash the player out of a pairing or result reveal. On
    exhaustion we fall back to the deterministic mock narration — built straight
    from event data, so it always names every participant and never leaks engine
    tokens — letting the ceremony resolve with plainer prose instead of throwing.
    """
    if event_narrator is None:
        return mock_event_narration(state, events)
    try:
        return event_narrator(state, events)
    except AgentError as exc:
        record_agent_degradation("event_narrator", exc)
        return mock_event_narration(state, events)


def run_turn(
    state: GameState,
    action: PlayerAction,
    rng: SeededRng,
    heartbreaker_voice: HeartbreakerVoiceFn | None = None,
    contextual_options: ContextualOptionsFn | None = None,
    event_narrator: EventNarratorFn | None = None,
    conversation_curator: ConversationCuratorFn | None = None,
    resort_orchestrator: ResortOrchestratorFn | None = None,
    background_dialogue: BackgroundDialogueFn | None = None,
) -> TurnResult:
    """Run one deterministic game turn."""
    trace_token = begin_agent_trace_capture()

    def finalize_turn(turn: TurnResult) -> TurnResult:
        turn.agent_traces = end_agent_trace_capture(trace_token)
        return turn

    starting_day = state.day
    if action.kind is not ActionKind.CHALLENGE_RESPONSE:
        _clear_resolved_challenge_after_wrap(state)
    pre_curator_batches: list[MemoryBatch] = []
    private_chat_attempt: PrivateChatAttempt | None = None
    exchange: Exchange | None = None
    audience_snapshot: AudienceSnapshot | None = None
    if action.kind is ActionKind.START_CONVERSATION and action.target_id is not None:
        blocked = target_in_active_conversation(state, action.target_id)
        if blocked is not None:
            private_chat_attempt = attempt_private_chat(state, action.target_id, rng)
            if private_chat_attempt.success:
                batch = curate_npc_conversation(state, blocked, conversation_curator)
                pre_curator_batches.append(batch)
                state.npc_conversations = [
                    conversation
                    for conversation in state.npc_conversations
                    if conversation.id != blocked.id
                ]
            else:
                result = private_chat_rejected_result(state, action, private_chat_attempt)
                time_cost = deduct_time(state, action)
                state.turn_index += 1
                exchange = _voiced_exchange(state, result, heartbreaker_voice)
                private_chat_attempt.deflection_line = exchange.npc_dialogue
                remember_private_chat_rejection(state, private_chat_attempt)
                resort_update, resort_changes, arrival_rolls = apply_resort_turn(
                    state,
                    rng.fork(f"resort-turn-{state.turn_index}"),
                    resort_orchestrator,
                    background_dialogue=background_dialogue,
                    conversation_curator=conversation_curator,
                )
                private_chat_curator_batches = [*pre_curator_batches, *resort_changes.curator_batches]
                agent_commits = AgentCommits(
                    resort_update=resort_update,
                    background_dialogues=resort_changes.background_dialogues,
                    curator_batches=private_chat_curator_batches,
                )
                auto_advance = False
                if check_auto_advance(state):
                    advance_phase_with_events(state, rng)
                    auto_advance = True
                append_daily_recap_if_needed(state, starting_day)
                return finalize_turn(
                    TurnResult(
                        state=state,
                        mechanical_result=result,
                        exchange=exchange,
                        available_actions=available_actions(state),
                        state_hash=state_hash(state_hash_payload(state)),
                        curator_batches=private_chat_curator_batches,
                        agent_commits=agent_commits,
                        time_cost=time_cost,
                        auto_advance=auto_advance,
                        arrival_rolls=arrival_rolls,
                    )
                )
    result = apply_action(state, action, rng)
    time_cost = deduct_time(state, action)
    if private_chat_attempt is not None:
        result.private_chat_attempt = private_chat_attempt
    ceremony_events: list[CeremonyEvent] = []
    if action.kind is ActionKind.PAIR:
        # A pending pairing gather means this PAIR is the player's
        # in-ceremony partner pick (Day 3 / Day 5). Resolve it the same way
        # the gather would have — but with the player's chosen partner — and
        # clear the gather so the player isn't asked to "join" afterwards.
        is_ceremony_pick = (
            state.pending_gather is not None
            and state.pending_gather.kind == "ceremony"
            and state.pending_gather.event_id.startswith("pairing")
        )
        ceremony = (
            initial_coupling(state, action.target_id)
            if state.day == 1 and not state.couples and action.target_id is not None
            else pairing(state, action.target_id)
        )
        ceremony_events.extend(pairing_events(state, ceremony))
        if ceremony.eliminated_id == state.player.id:
            state.outcome = RunOutcome.ELIMINATED
        if is_ceremony_pick:
            state.pending_gather = None
            from src.game.engine.phases import advance_phase
            advance_phase(state)
    if action.kind is ActionKind.CHALLENGE_RESPONSE and state.pending_challenge is not None:
        event = challenge_response_event(state)
        if event is not None:
            ceremony_events.append(event)
    if action.kind is ActionKind.FLUSH_DECISION and action.intent_id is not None:
        decision = FlushDecision(action.intent_id)
        ceremony_events.append(
            CeremonyEvent(
                kind="flush_of_hearts_decision",
                message=flush_decision_message(state, decision, action.target_id),
                heartbreaker_id=action.target_id,
            )
        )
    if action.kind is ActionKind.PRIVATE_SUITE:
        ceremony_events.append(private_suite_event(state))
    event = proposal_event(state, result)
    if event is not None:
        ceremony_events.append(event)
    if action.kind is ActionKind.JOIN_GATHER:
        gather_curator_batches = [*pre_curator_batches]
        gather_curator_batches.extend(
                close_conversations_for_gather(
                    state,
                    conversation_curator,
                    curate_player_conversation,
                    curate_npc_conversation,
                )
        )
        move_everyone_to_gather(state)
        phase_events, audience_snapshot = resolve_pending_gather(state, rng)
        ceremony_events.extend(phase_events)
        append_daily_recap_if_needed(state, starting_day)
        state.turn_index += 1
        event_narration = None
        if ceremony_events:
            remember_ceremony_events(state, ceremony_events)
            event_narration = _narrated_events(state, ceremony_events, event_narrator)
        auto_advance = False
        if check_auto_advance(state):
            more_events, audience_after_auto = advance_phase_with_events(state, rng)
            ceremony_events.extend(more_events)
            audience_snapshot = audience_snapshot or audience_after_auto
            auto_advance = True
        return finalize_turn(
            TurnResult(
                state=state,
                mechanical_result=result,
                event_narration=event_narration,
                available_actions=available_actions(state),
                state_hash=state_hash(state_hash_payload(state)),
                ceremony_events=ceremony_events,
                curator_batches=gather_curator_batches,
                audience_snapshot=audience_snapshot,
                agent_commits=AgentCommits(curator_batches=gather_curator_batches),
                time_cost=time_cost,
                auto_advance=auto_advance,
            )
        )
    if action.kind is ActionKind.PAIR and state.day == 1 and state.phase is Phase.MORNING:
        # Intros already ran before First Spark, so the next legal beat is
        # the Day-1 Challenge. Mark MORNING fully spent and let auto-advance
        # roll into CHALLENGE through advance_phase so the challenge gets
        # scheduled via the standard _scheduled_phase_events path.
        state.phase_clock.elapsed_minutes = state.phase_clock.budget_minutes
    state.turn_index += 1
    follow_up_menu = None
    curator_batches: list[MemoryBatch] = [*pre_curator_batches]
    if result.action.intent_id == "accept_interruption":
        active = state.active_conversation
        if active is None or result.action.target_id is None:
            raise ValueError("accept_interruption requires active conversation and target")
        batch = curate_player_conversation(state, active, conversation_curator)
        curator_batches.append(batch)
        close_conversation(state, "player_exit")
        new_conversation = start_conversation(state, result.action.target_id, state.turn_index)
        exchange = _voiced_exchange(state, result, heartbreaker_voice)
        append_exchange(new_conversation, result, exchange, turn_index=state.turn_index)
        bump_target_familiarity(state, new_conversation.target_id, 1)
        probability = departure_probability(new_conversation, state)
        new_conversation.departure_probability_last = probability
        follow_up_menu = generate_follow_up_menu(
            state,
            result,
            exchange,
            probability,
            contextual_options,
        )
        new_conversation.pending_options = follow_up_menu
    elif result.action.intent_id in {"defer_interruption", "ignore_interruption"}:
        follow_up_menu = (
            None if state.active_conversation is None else state.active_conversation.pending_options
        )
    elif result.action.intent_id == "engage_approach":
        # The player welcomed an NPC who sought them out while idling. Open a
        # fresh conversation just as accept_interruption re-opens one — the
        # approacher becomes the active conversation target.
        if result.action.target_id is None:
            raise ValueError("engage_approach requires a target")
        new_conversation = start_conversation(state, result.action.target_id, state.turn_index)
        exchange = _voiced_exchange(state, result, heartbreaker_voice)
        append_exchange(new_conversation, result, exchange, turn_index=state.turn_index)
        bump_target_familiarity(state, new_conversation.target_id, 1)
        probability = departure_probability(new_conversation, state)
        new_conversation.departure_probability_last = probability
        follow_up_menu = generate_follow_up_menu(
            state,
            result,
            exchange,
            probability,
            contextual_options,
        )
        new_conversation.pending_options = follow_up_menu
    elif result.action.intent_id in APPROACH_INTENT_KINDS:
        # Waved off / ignored: no conversation opens, the player stays idle.
        follow_up_menu = None
    elif action.kind in {ActionKind.START_CONVERSATION, ActionKind.RESPOND_WITH}:
        conversation: Conversation
        if action.kind is ActionKind.START_CONVERSATION:
            if result.action.target_id is None:
                raise ValueError("START_CONVERSATION result missing target_id")
            conversation = start_conversation(state, result.action.target_id, state.turn_index)
        else:
            active = state.active_conversation
            if active is None:
                raise ValueError("RESPOND_WITH requires active conversation")
            conversation = active
            conversation.pending_options = None
        exchange = _voiced_exchange(state, result, heartbreaker_voice)
        append_exchange(conversation, result, exchange, turn_index=state.turn_index)
        bump_target_familiarity(state, conversation.target_id, 1)
        if _is_wheel_exit(result):
            batch = curate_player_conversation(state, conversation, conversation_curator)
            curator_batches.append(batch)
            close_conversation(state, "wheel_exit")
        else:
            probability = departure_probability(conversation, state)
            conversation.departure_probability_last = probability
            follow_up_menu = generate_follow_up_menu(
                state,
                result,
                exchange,
                probability,
                contextual_options,
            )
            conversation.pending_options = follow_up_menu
            if follow_up_menu.npc_will_leave:
                batch = curate_player_conversation(state, conversation, conversation_curator)
                curator_batches.append(batch)
                close_conversation(state, "npc_left")
    elif action.kind is ActionKind.INTRODUCE_TO:
        exchange = _voiced_exchange(state, result, heartbreaker_voice)
        if action.target_id is not None:
            bump_target_familiarity(state, action.target_id, 0)
        if intro_segment_complete(state):
            if not state.intro_memory_created:
                batch = intro_memory_batch(state)
                add_memory_batch(state, batch, day=state.day, turn=state.turn_index)
                curator_batches.append(batch)
                state.intro_memory_created = True
            state.phase_clock.elapsed_minutes = state.phase_clock.budget_minutes
    if action.kind is ActionKind.END_CONVERSATION:
        if state.active_conversation is not None:
            batch = curate_player_conversation(state, state.active_conversation, conversation_curator)
            curator_batches.append(batch)
        close_conversation(state, "player_exit")
    curator_batches.extend(close_proposal_conversation(state, result, conversation_curator))
    auto_advance = False
    if state.active_conversation is None and check_auto_advance(state):
        phase_events, audience_after_auto = advance_phase_with_events(state, rng)
        ceremony_events.extend(phase_events)
        audience_snapshot = audience_snapshot or audience_after_auto
        auto_advance = True
    resort_update_commit: ResortUpdate | None
    background_dialogues = []
    if state.pending_gather is not None:
        resort_update_commit = None
        arrival_rolls = []
    else:
        resort_update_commit, resort_changes, arrival_rolls = apply_resort_turn(
            state,
            rng.fork(f"resort-turn-{state.turn_index}"),
            resort_orchestrator,
            background_dialogue=background_dialogue,
            conversation_curator=conversation_curator,
        )
        background_dialogues = resort_changes.background_dialogues
        curator_batches.extend(resort_changes.curator_batches)
        if action.kind is not ActionKind.NPC_PROPOSAL_RESPONSE:
            incoming = maybe_trigger_npc_player_proposal(state, rng.fork(f"npc-proposal-{state.turn_index}"))
            if incoming is not None:
                ceremony_events.append(
                    CeremonyEvent(
                        kind="npc_proposal_incoming",
                        sub_kind="incoming",
                        message=(
                            f"{display_name(state, incoming.proposer_id)} wants to ask "
                            f"{player_display_name(state)} to pair."
                        ),
                        heartbreaker_id=incoming.proposer_id,
                    )
                )
    # Being "sought after": when the player chooses to idle (an AMBIENT turn),
    # a co-located NPC may walk up to them. Only after the resort has settled
    # into its needs-driven positions, never while another demand is pending,
    # and never on the cusp of a phase change (the approach would be stranded).
    # On the final night the resort settles for the Final Vote — a fresh approach
    # here would just bury the "gather everyone" CTA behind a decline menu.
    if (
        action.kind is ActionKind.AMBIENT
        and not auto_advance
        and state.active_conversation is None
        and state.pending_npc_approach is None
        and state.pending_npc_summon is None
        and state.pending_pair_proposal is None
        and state.pending_gather is None
        and state.pending_challenge is None
        and not is_finale_evening(state)
        and not check_auto_advance(state)
    ):
        roll_ambient_approach(state, rng.fork(f"approach-turn-{state.turn_index}"))
    agent_commits = AgentCommits(
        resort_update=resort_update_commit,
        background_dialogues=background_dialogues,
        curator_batches=curator_batches,
    )
    if not auto_advance and check_auto_advance(state):
        if state.active_conversation is not None:
            batch = curate_player_conversation(state, state.active_conversation, conversation_curator)
            curator_batches.append(batch)
            close_conversation(state, "phase_end")
        phase_events, audience_after_auto = advance_phase_with_events(state, rng)
        ceremony_events.extend(phase_events)
        audience_snapshot = audience_snapshot or audience_after_auto
        auto_advance = True
    append_daily_recap_if_needed(state, starting_day)
    event_narration = None
    if ceremony_events:
        remember_ceremony_events(state, ceremony_events)
        event_narration = _narrated_events(state, ceremony_events, event_narrator)
    return finalize_turn(
        TurnResult(
            state=state,
            mechanical_result=result,
            exchange=exchange,
            event_narration=event_narration,
            follow_up_menu=follow_up_menu,
            available_actions=available_actions(state),
            state_hash=state_hash(state_hash_payload(state)),
            ceremony_events=ceremony_events,
            curator_batches=curator_batches,
            audience_snapshot=audience_snapshot,
            agent_commits=agent_commits,
            time_cost=time_cost,
            auto_advance=auto_advance,
            arrival_rolls=arrival_rolls,
        )
    )


def _is_wheel_exit(result: MechanicalResult) -> bool:
    return (
        result.action.kind is ActionKind.RESPOND_WITH
        and result.action.intent_id in EXIT_INTENT_KINDS
    )


def _clear_resolved_challenge_after_wrap(state: GameState) -> None:
    challenge = state.pending_challenge
    if challenge is not None and challenge.result is not None:
        state.pending_challenge = None
