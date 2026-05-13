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
    mock_follow_up_menu,
    validate_follow_up_menu,
    with_gossip_options,
)
from src.game.agents.conversation_curator import (
    ConversationCuratorFn,
    mock_conversation_curator,
)
from src.game.agents.event_narrator import (
    EventNarration,
    EventNarratorFn,
    mock_event_narration,
)
from src.game.agents.islander_voice import Exchange, IslanderVoiceFn, mock_islander_voice
from src.game.agents.villa_orchestrator import VillaOrchestratorFn, mock_villa_orchestrator
from src.game.engine.actions import ActionKind, ActionSpec, PlayerAction, available_actions
from src.game.engine.audience import record_audience_snapshot
from src.game.engine.ceremonies import (
    CeremonyEvent,
    arrive_bombshell,
    final_vote_ceremony,
    recoupling,
)
from src.game.engine.conversation import (
    append_exchange,
    close_conversation,
    departure_probability,
    start_conversation,
)
from src.game.engine.memory import (
    add_memory,
    add_memory_batch,
    create_memory,
    remember_ceremony_events,
)
from src.game.engine.phases import advance_phase
from src.game.engine.pull import PullAttempt, attempt_pull, target_in_active_conversation
from src.game.engine.rules import (
    EXIT_INTENT_KINDS,
    MechanicalResult,
    apply_action,
)
from src.game.engine.villa import AgentCommits, apply_villa_update
from src.game.state.models import (
    AudienceSnapshot,
    Conversation,
    FollowUpMenu,
    GameState,
    MemoryBatch,
    NPCNPCConversation,
    RelationshipDelta,
    RunOutcome,
    clamp_relationship,
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


def run_turn(
    state: GameState,
    action: PlayerAction,
    rng: SeededRng,
    islander_voice: IslanderVoiceFn | None = None,
    contextual_options: ContextualOptionsFn | None = None,
    event_narrator: EventNarratorFn | None = None,
    conversation_curator: ConversationCuratorFn | None = None,
    villa_orchestrator: VillaOrchestratorFn | None = None,
    background_dialogue: BackgroundDialogueFn | None = None,
) -> TurnResult:
    """Run one deterministic game turn."""
    pre_curator_batches: list[MemoryBatch] = []
    pull_attempt: PullAttempt | None = None
    exchange: Exchange | None = None
    audience_snapshot: AudienceSnapshot | None = None
    if action.kind is ActionKind.START_CONVERSATION and action.target_id is not None:
        blocked = target_in_active_conversation(state, action.target_id)
        if blocked is not None:
            pull_attempt = attempt_pull(state, action.target_id, rng)
            if pull_attempt.success:
                batch = _curate_npc_conversation(state, blocked, conversation_curator)
                pre_curator_batches.append(batch)
                state.npc_conversations = [
                    conversation
                    for conversation in state.npc_conversations
                    if conversation.id != blocked.id
                ]
            else:
                result = _pull_rejected_result(state, action, pull_attempt)
                state.turn_index += 1
                speak = mock_islander_voice if islander_voice is None else islander_voice
                exchange = speak(state, result)
                pull_attempt.deflection_line = exchange.npc_dialogue
                _remember_pull_rejection(state, pull_attempt)
                orchestrate = mock_villa_orchestrator if villa_orchestrator is None else villa_orchestrator
                villa_update = orchestrate(state)
                villa_changes = apply_villa_update(
                    state,
                    villa_update,
                    rng.fork(f"villa-turn-{state.turn_index}"),
                    background_dialogue=background_dialogue,
                    conversation_curator=conversation_curator,
                )
                pull_curator_batches = [*pre_curator_batches, *villa_changes.curator_batches]
                agent_commits = AgentCommits(
                    villa_update=villa_update,
                    background_dialogues=villa_changes.background_dialogues,
                    curator_batches=pull_curator_batches,
                )
                return TurnResult(
                    state=state,
                    mechanical_result=result,
                    exchange=exchange,
                    available_actions=available_actions(state),
                    state_hash=state_hash(state_hash_payload(state)),
                    curator_batches=pull_curator_batches,
                    agent_commits=agent_commits,
                )
    result = apply_action(state, action, rng)
    if pull_attempt is not None:
        result.pull_attempt = pull_attempt
    ceremony_events: list[CeremonyEvent] = []
    if action.kind is ActionKind.RECOUPLE:
        ceremony = recoupling(state, action.target_id)
        ceremony_events.extend(_recoupling_events(ceremony.eliminated_id))
        if ceremony.eliminated_id == state.player.id:
            state.outcome = RunOutcome.ELIMINATED
    if action.kind is ActionKind.ADVANCE_PHASE:
        if state.phase.value == "evening" and state.day in {3, 5}:
            ceremony = recoupling(state)
            ceremony_events.extend(_recoupling_events(ceremony.eliminated_id))
            if ceremony.eliminated_id == state.player.id:
                state.outcome = RunOutcome.ELIMINATED
        if state.phase.value == "evening":
            audience_snapshot = record_audience_snapshot(state)
        if state.phase.value == "evening" and state.day >= 6:
            ceremony_events.append(final_vote_ceremony(state))
        advance_phase(state)
        if state.day == 4 and state.phase.value == "morning":
            bombshell = arrive_bombshell(state)
            ceremony_events.append(
                CeremonyEvent(
                    kind="bombshell",
                    message=f"Bombshell arrived: {bombshell.name} enters the villa.",
                    islander_id=bombshell.id,
                )
            )
    state.turn_index += 1
    follow_up_menu = None
    curator_batches: list[MemoryBatch] = [*pre_curator_batches]
    if result.action.intent_id == "accept_interruption":
        active = state.active_conversation
        if active is None or result.action.target_id is None:
            raise ValueError("accept_interruption requires active conversation and target")
        batch = _curate_conversation(state, active, conversation_curator)
        curator_batches.append(batch)
        close_conversation(state, "player_exit")
        new_conversation = start_conversation(state, result.action.target_id, state.turn_index)
        speak = mock_islander_voice if islander_voice is None else islander_voice
        exchange = speak(state, result)
        append_exchange(new_conversation, result, exchange, turn_index=state.turn_index)
        probability = departure_probability(new_conversation, state)
        new_conversation.departure_probability_last = probability
        menu_fn = (
            (lambda _state, _result, _exchange, _probability: mock_follow_up_menu(npc_will_leave=True))
            if contextual_options is None
            else contextual_options
        )
        follow_up_menu = with_gossip_options(menu_fn(state, result, exchange, probability), state)
        validate_follow_up_menu(follow_up_menu)
        new_conversation.pending_options = follow_up_menu
    elif result.action.intent_id in {"defer_interruption", "ignore_interruption"}:
        follow_up_menu = (
            None if state.active_conversation is None else state.active_conversation.pending_options
        )
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
        speak = mock_islander_voice if islander_voice is None else islander_voice
        exchange = speak(state, result)
        append_exchange(conversation, result, exchange, turn_index=state.turn_index)
        if _is_wheel_exit(result):
            batch = _curate_conversation(state, conversation, conversation_curator)
            curator_batches.append(batch)
            close_conversation(state, "wheel_exit")
        else:
            probability = departure_probability(conversation, state)
            conversation.departure_probability_last = probability
            menu_fn = (
                (lambda _state, _result, _exchange, _probability: mock_follow_up_menu(npc_will_leave=True))
                if contextual_options is None
                else contextual_options
            )
            follow_up_menu = with_gossip_options(menu_fn(state, result, exchange, probability), state)
            validate_follow_up_menu(follow_up_menu)
            conversation.pending_options = follow_up_menu
            if follow_up_menu.npc_will_leave:
                batch = _curate_conversation(state, conversation, conversation_curator)
                curator_batches.append(batch)
                close_conversation(state, "npc_left")
    if action.kind is ActionKind.END_CONVERSATION:
        if state.active_conversation is not None:
            batch = _curate_conversation(state, state.active_conversation, conversation_curator)
            curator_batches.append(batch)
        close_conversation(state, "player_exit")
    event_narration = None
    if ceremony_events:
        remember_ceremony_events(state, ceremony_events)
        narrate_event = mock_event_narration if event_narrator is None else event_narrator
        event_narration = narrate_event(state, ceremony_events)
    orchestrate = mock_villa_orchestrator if villa_orchestrator is None else villa_orchestrator
    villa_update = orchestrate(state)
    villa_changes = apply_villa_update(
        state,
        villa_update,
        rng.fork(f"villa-turn-{state.turn_index}"),
        background_dialogue=background_dialogue,
        conversation_curator=conversation_curator,
    )
    curator_batches.extend(villa_changes.curator_batches)
    agent_commits = AgentCommits(
        villa_update=villa_update,
        background_dialogues=villa_changes.background_dialogues,
        curator_batches=curator_batches,
    )
    return TurnResult(
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
    )


def _recoupling_events(eliminated_id: str | None) -> list[CeremonyEvent]:
    events = [CeremonyEvent(kind="recoupling", message="Recoupling ceremony completed.")]
    if eliminated_id is not None:
        events.append(
            CeremonyEvent(
                kind="elimination",
                message=f"Dumping decision: {eliminated_id} leaves the villa.",
                islander_id=eliminated_id,
            )
        )
    return events


def _curate_conversation(
    state: GameState,
    conversation: Conversation,
    curator: ConversationCuratorFn | None,
) -> MemoryBatch:
    bystander_ids = _conversation_bystanders(state, conversation.target_id)
    curate = mock_conversation_curator if curator is None else curator
    batch = curate(state, conversation, bystander_ids)
    add_memory_batch(state, batch, day=state.day, turn=state.turn_index)
    return batch


def _curate_npc_conversation(
    state: GameState,
    conversation: NPCNPCConversation,
    curator: ConversationCuratorFn | None,
) -> MemoryBatch:
    conversation.status = "closed"
    bystander_ids = [
        islander.id
        for islander in state.islanders
        if islander.id not in conversation.participants
        and not islander.eliminated
        and islander.location_id == conversation.location_id
    ]
    if state.location_id == conversation.location_id:
        bystander_ids.append("player")
    curate = mock_conversation_curator if curator is None else curator
    batch = curate(state, conversation, bystander_ids)
    add_memory_batch(state, batch, day=state.day, turn=state.turn_index)
    return batch


def _pull_rejected_result(
    state: GameState,
    action: PlayerAction,
    pull_attempt: PullAttempt,
) -> MechanicalResult:
    target = next(islander for islander in state.islanders if islander.id == pull_attempt.target_id)
    delta = RelationshipDelta(affection=-1)
    target.relationship.affection = clamp_relationship(target.relationship.affection + delta.affection)
    return MechanicalResult(
        action=action.model_copy(update={"intent_id": "pull_rejected"}),
        success=False,
        roll=pull_attempt.roll,
        success_chance=pull_attempt.chance,
        relationship_deltas={target.id: delta},
        tags=["pull_rejected"],
        pull_attempt=pull_attempt,
    )


def _remember_pull_rejection(state: GameState, pull_attempt: PullAttempt) -> None:
    target_name = _name_for_memory(state, pull_attempt.target_id)
    for islander in state.islanders:
        if (
            islander.id != pull_attempt.target_id
            and not islander.eliminated
            and islander.location_id == state.location_id
        ):
            add_memory(
                state,
                create_memory(
                    holder_id=islander.id,
                    subject_id="player",
                    source="witnessed",
                    day=state.day,
                    turn=state.turn_index,
                    weight=6,
                    tags=["saw_pull_rejected", "pull", pull_attempt.target_id],
                    content=f"I saw the player try to pull {target_name} away and get brushed off.",
                ),
            )


def _name_for_memory(state: GameState, islander_id: str) -> str:
    for islander in state.islanders:
        if islander.id == islander_id:
            return islander.name
    return islander_id


def _is_wheel_exit(result: MechanicalResult) -> bool:
    return (
        result.action.kind is ActionKind.RESPOND_WITH
        and result.action.intent_id in EXIT_INTENT_KINDS
    )


def _conversation_bystanders(state: GameState, target_id: str) -> list[str]:
    return [
        islander.id
        for islander in state.islanders
        if islander.id != target_id
        and not islander.eliminated
        and islander.location_id == state.location_id
    ]
