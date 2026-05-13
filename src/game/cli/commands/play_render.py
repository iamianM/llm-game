"""Rendering helpers for the interactive play command."""

from __future__ import annotations

from itertools import groupby

from src.game.engine.actions import ActionKind, ActionSpec
from src.game.engine.casa_amor import locations_for_villa
from src.game.engine.compatibility import revealed_preferences
from src.game.engine.couples import couple_strength, partner_for, player_couple
from src.game.engine.turn import TurnResult
from src.game.state.models import GameState, NPCNPCConversation


def print_character_card(state: GameState) -> None:
    """Print the confirmed player character card."""
    stats = state.player.stats
    print("\nCharacter confirmed:")
    print(f"  Archetype: {state.player.archetype_id}")
    print(
        f"  Stats: Charm {stats.charm}, Banter {stats.banter}, EQ {stats.eq}, "
        f"Graft {stats.graft}, Loyalty {stats.loyalty}"
    )
    print(f"  Public perception: {state.player.public_perception}")


def print_state(state: GameState, *, debug: bool = False) -> None:
    """Print the current villa map and player relationship state."""
    print(f"\nDay {state.day} | {state.phase.value} | turn {state.turn_index}")
    print(f"Current villa: {state.villa.value}. You are at the {state.location_id.value.upper()}.")
    print(
        f"Time remaining: {state.phase_clock.remaining} min "
        f"({state.phase_clock.elapsed_minutes}/{state.phase_clock.budget_minutes} used)"
    )
    if 0 < state.phase_clock.remaining <= 20:
        print("It's getting late - phase will end soon.")
    print("\nVilla:")
    for location in locations_for_villa(state.villa):
        occupants = ["you"] if location is state.location_id else []
        occupants.extend(
            islander.name
            for islander in state.islanders
            if islander.location_id is location and not islander.eliminated
        )
        line = f"  {location.value.title():<9} -> {', '.join(occupants) if occupants else '(empty)'}"
        conversations = [
            conversation
            for conversation in state.npc_conversations
            if conversation.location_id is location and conversation.status == "active"
        ]
        if conversations:
            summaries = "; ".join(
                f'{names_for(state, conversation.participants)} chatting about "{conversation.topic}"'
                for conversation in conversations
            )
            line = f"{line} -- {summaries}"
        print(line)

    print("\nYour relationships:")
    for islander in state.islanders:
        if islander.eliminated:
            continue
        rel = islander.relationship
        print(
            f"  {islander.name:<7} affection {rel.affection:<3} chemistry {rel.chemistry:<3} "
            f"trust {rel.trust:<3} friendship {rel.friendship:<3} familiarity {islander.familiarity_with_player:<3}"
        )
        revealed = revealed_preferences(islander)
        if revealed:
            print(f"    known type: {revealed}")
        if debug and islander.memories:
            print(f"    memories: {len(islander.memories)}")
    if state.active_conversation is not None and state.active_conversation.pending_interruption is not None:
        interruption = state.active_conversation.pending_interruption
        print(
            f"\n*** Interruption: {name_for(state, interruption.interrupter_id)} wants to talk "
            f"({interruption.urgency}, {interruption.reason}) ***"
        )
    if state.pending_challenge is not None:
        challenge = state.pending_challenge
        result = challenge.result or "waiting for choice"
        print(f"\nChallenge: {challenge.kind} ({challenge.stat_tested}) -- {result}")
    if state.pending_text is not None:
        print(f"\nI've got a text: {state.pending_text.body}")
    if state.pending_group_date is not None and state.pending_group_date.pending:
        print(
            f"\nGroup date pending: {names_for(state, state.pending_group_date.participants)} "
            f"at the {state.pending_group_date.location}"
        )
    couple = player_couple(state)
    if couple is not None:
        partner_id = partner_for(couple, state.player.id)
        print(f"\nCouple: {name_for(state, partner_id)} | strength {couple_strength(state, couple)}")
    if state.hideaway.used_on_day is not None:
        partner = state.hideaway.partner_id or "unknown"
        print(f"Hideaway used day {state.hideaway.used_on_day} with {name_for(state, partner)}")
    if state.casa_amor_state is not None:
        casa = state.casa_amor_state
        decision = casa.player_decision.value if casa.player_decision is not None else "pending"
        print(f"Casa Amor: started day {casa.started_on_day}, return day {casa.return_day}, decision {decision}")


def print_actions(actions: list[ActionSpec]) -> None:
    """Print available action labels."""
    if any(spec.action.kind is ActionKind.RESPOND_WITH for spec in actions):
        _print_follow_up_actions(actions)
        return
    for index, spec in enumerate(actions, start=1):
        print(f"{index}. {spec.label}")


def print_turn(turn: TurnResult) -> None:
    """Print the result of one completed turn."""
    result = turn.mechanical_result
    if result.pull_attempt is not None:
        outcome = "succeeded" if result.pull_attempt.success else "missed"
        print(
            f"Pull attempt: {result.pull_attempt.target_id} "
            f"({result.pull_attempt.chance}% chance, rolled {result.pull_attempt.roll}) -- {outcome}"
        )
        if result.pull_attempt.deflection_line:
            print(result.pull_attempt.deflection_line)
    for roll in turn.arrival_rolls:
        print(
            f"Arrival: {name_for(turn.state, roll.arriving_npc_id)} walked in. "
            f"Interruption roll {roll.interruption_roll}/{roll.interruption_chance} "
            f"({'hit' if roll.interruption_hit else 'miss'}); "
            f"pull roll {roll.pull_roll}/{roll.pull_chance} "
            f"({'hit' if roll.pull_hit else 'miss'})."
        )
    if turn.auto_advance:
        print(f"Time passes. -> {turn.state.phase.value}.")
    if turn.exchange is not None:
        print(f'You: "{turn.exchange.player_dialogue}"')
        print(f'{_target_name(turn)}: {turn.exchange.npc_dialogue}')
    if turn.event_narration is not None:
        print(turn.event_narration.prose)
    if result.action.kind is ActionKind.HIDEAWAY:
        partner = turn.state.hideaway.partner_id or "unknown"
        print(f"Hideaway night: you and {name_for(turn.state, partner)} spent private time together.")
    if turn.state.pending_challenge is not None and turn.state.pending_challenge.result is not None:
        challenge = turn.state.pending_challenge
        print(f"Challenge: {challenge.kind} -- {challenge.result}")
    if turn.state.pending_text is not None:
        print(f"Text: {turn.state.pending_text.body}")
    if turn.audience_snapshot is not None:
        print("Audience ranking:")
        for entry in turn.audience_snapshot.entries:
            couple = " & ".join(entry.couple)
            marker = " (you)" if entry.is_player_couple else ""
            print(f"  {entry.rank}. {couple}{marker}: {entry.score}")
    if turn.agent_commits.villa_update is not None:
        print_villa_update(turn)
    if turn.follow_up_menu is not None and turn.follow_up_menu.npc_will_leave:
        print(turn.follow_up_menu.npc_exit_line)
    if result.roll is not None and result.success_chance is not None:
        outcome = "success" if result.success else "miss"
        print(f"{outcome}: rolled {result.roll} vs {result.success_chance}")
    print(f"hash: {turn.state_hash}")


def print_villa_update(turn: TurnResult) -> None:
    """Print named background villa events from the turn commits."""
    update = turn.agent_commits.villa_update
    if update is None:
        return
    lines: list[str] = []
    for movement in update.npc_movements:
        name = name_for(turn.state, movement.npc_id)
        if movement.target_location is turn.state.location_id:
            lines.append(f"{name} joined you at the {movement.target_location.value} ({movement.reason})")
        else:
            lines.append(f"{name} moved to the {movement.target_location.value} ({movement.reason})")
    for start in update.conversation_starts:
        lines.append(
            f'{names_for(turn.state, start.participants)} started chatting at the '
            f'{start.location.value}: "{start.topic}"'
        )
    for continuation in update.conversation_continues:
        conversation = _npc_conversation(turn.state, continuation.conversation_id)
        label = continuation.conversation_id
        if conversation is not None:
            label = f"{names_for(turn.state, conversation.participants)} at the {conversation.location_id.value}"
        nudge = f': "{continuation.nudge}"' if continuation.nudge else ""
        lines.append(f"{label} kept talking{nudge}")
    for ended in update.conversation_ends:
        lines.append(f"Conversation ended ({ended.conversation_id}): {ended.reason}")
    for summon in update.npc_summoned_elsewhere:
        lines.append(
            f"{name_for(turn.state, summon.npc_id)} was pulled to the "
            f"{summon.target_location.value} ({summon.reason})"
        )
    for exchange in turn.agent_commits.background_dialogues:
        lines.append(f"Background ({exchange.tone}): {short_line(exchange.speaker_a_line)}")
    if not lines:
        return
    print("While you talked:")
    for line in lines:
        print(f"  - {line}")


def name_for(state: GameState, islander_id: str) -> str:
    """Return a display name for an islander id."""
    if islander_id == "player":
        return "you"
    for islander in state.islanders:
        if islander.id == islander_id:
            return islander.name
    return islander_id


def names_for(state: GameState, islander_ids: list[str]) -> str:
    """Return a display label for multiple islanders."""
    return " & ".join(name_for(state, islander_id) for islander_id in islander_ids)


def short_line(line: str, *, limit: int = 120) -> str:
    """Compact and quote one background dialogue line."""
    compact = " ".join(line.split())
    if len(compact) <= limit:
        return f'"{compact}"'
    return f'"{compact[: limit - 1].rstrip()}..."'


def _print_follow_up_actions(actions: list[ActionSpec]) -> None:
    numbered = list(enumerate(actions, start=1))
    followups = [
        (index, spec)
        for index, spec in numbered
        if spec.action.kind is ActionKind.RESPOND_WITH
    ]
    for category, category_specs in groupby(followups, key=lambda item: item[1].label.split(":", 1)[0]):
        print(f"{category}:")
        for index, spec in category_specs:
            label = spec.label.split(":", 1)[1].strip() if ":" in spec.label else spec.label
            print(f"  {index}. {label}")
    for index, spec in numbered:
        if spec.action.kind is not ActionKind.RESPOND_WITH:
            print(f"{index}. {spec.label}")


def _target_name(turn: TurnResult) -> str:
    target_id = turn.mechanical_result.action.target_id
    for islander in turn.state.islanders:
        if islander.id == target_id:
            return islander.name
    return "Islander"


def _npc_conversation(state: GameState, conversation_id: str) -> NPCNPCConversation | None:
    for conversation in state.npc_conversations:
        if conversation.id == conversation_id:
            return conversation
    return None
