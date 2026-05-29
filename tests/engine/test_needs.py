"""Tests for needs-driven NPC movement (engine/needs.py)."""

from __future__ import annotations

from src.game.engine.needs import (
    PARTNER_PULL,
    ROLE_OF,
    NeedsMovement,
    apply_needs_movements,
    destination_score,
    free_npcs,
    plan_and_apply,
    plan_needs_movements,
)
from src.game.state.models import (
    Conversation,
    Couple,
    GameState,
    Location,
    NPCNPCConversation,
    Phase,
    new_game,
)
from src.game.state.rng import SeededRng


def _neutralize_personalities(state: GameState) -> None:
    """Flatten Big5 to neutral so phase advertisement dominates scoring."""
    for islander in state.islanders:
        islander.big5.openness = 5
        islander.big5.conscientiousness = 5
        islander.big5.extraversion = 5
        islander.big5.agreeableness = 5
        islander.big5.neuroticism = 5


def _place_all(state: GameState, location: Location) -> None:
    for islander in state.islanders:
        islander.location_id = location


def test_no_movement_in_scripted_phases() -> None:
    """CHALLENGE / INTROS / COMPLETE have no advertisement table — no moves."""
    for phase in (Phase.CHALLENGE, Phase.INTROS, Phase.COMPLETE):
        state = new_game(1)
        state.phase = phase
        _place_all(state, Location.FIREPIT)
        assert plan_needs_movements(state, SeededRng(1)) == []


def test_morning_disperses_from_firepit_to_home_rooms() -> None:
    """After an event (all at firepit), morning pulls NPCs to bedroom/kitchen."""
    state = new_game(1)
    state.phase = Phase.MORNING
    _neutralize_personalities(state)
    _place_all(state, Location.FIREPIT)

    moves = plan_and_apply(state, SeededRng(7))

    assert moves, "expected morning dispersal away from the firepit"
    for islander in free_npcs(state):
        assert islander.location_id is not Location.FIREPIT
        assert ROLE_OF[islander.location_id] in {"bedroom", "kitchen"}


def test_afternoon_pulls_to_pool() -> None:
    """Afternoon advertises the pool most strongly for neutral personalities."""
    state = new_game(1)
    state.phase = Phase.AFTERNOON
    _neutralize_personalities(state)
    _place_all(state, Location.BEDROOM)

    plan_and_apply(state, SeededRng(3))

    for islander in free_npcs(state):
        assert islander.location_id is Location.POOL


def test_evening_clusters_on_terrace_and_firepit() -> None:
    """Evening keeps people on the terrace / at the firepit, not the bedroom."""
    state = new_game(1)
    state.phase = Phase.EVENING
    _neutralize_personalities(state)
    _place_all(state, Location.POOL)

    plan_and_apply(state, SeededRng(5))

    for islander in free_npcs(state):
        assert ROLE_OF[islander.location_id] in {"terrace", "firepit"}


def test_locked_conversation_participants_are_not_moved() -> None:
    """NPCs locked in an active NPC-NPC conversation stay put."""
    state = new_game(1)
    state.phase = Phase.AFTERNOON
    _neutralize_personalities(state)
    _place_all(state, Location.BEDROOM)
    a, b = state.islanders[0].id, state.islanders[1].id
    state.npc_conversations.append(
        NPCNPCConversation(
            id="npcconv_locked",
            participants=[a, b],
            location_id=Location.BEDROOM,
            topic="secrets",
            started_on_turn=0,
        )
    )

    moves = plan_needs_movements(state, SeededRng(3))
    moved_ids = {move.npc_id for move in moves}

    assert a not in moved_ids
    assert b not in moved_ids


def test_active_player_target_is_not_moved() -> None:
    """The islander the player is actively talking to is never relocated."""
    state = new_game(1)
    state.phase = Phase.AFTERNOON
    _neutralize_personalities(state)
    _place_all(state, Location.BEDROOM)
    target = state.islanders[0].id
    state.active_conversation = Conversation(
        target_id=target, started_on_turn=0, started_on_day=1
    )

    free = free_npcs(state)
    moves = plan_needs_movements(state, SeededRng(3))

    assert all(islander.id != target for islander in free)
    assert all(move.npc_id != target for move in moves)


def test_eliminated_islanders_excluded() -> None:
    state = new_game(1)
    state.phase = Phase.AFTERNOON
    state.islanders[0].eliminated = True

    assert all(islander.id != state.islanders[0].id for islander in free_npcs(state))


def test_present_partner_adds_exactly_partner_pull() -> None:
    """Romance pull contributes exactly PARTNER_PULL when the partner is present."""
    state = new_game(1)
    state.phase = Phase.AFTERNOON
    _neutralize_personalities(state)
    _place_all(state, Location.POOL)
    a, b = state.islanders[2], state.islanders[3]
    state.couples.append(
        Couple(partner_a_id=a.id, partner_b_id=b.id, formed_on_day=1, formed_via="opening")
    )

    # Partner b present at the terrace.
    b.location_id = Location.TERRACE
    with_partner = destination_score(state, a, Location.TERRACE, SeededRng(1))
    # Partner b elsewhere.
    b.location_id = Location.KITCHEN
    without_partner = destination_score(state, a, Location.TERRACE, SeededRng(1))

    assert with_partner - without_partner == PARTNER_PULL


def test_deterministic_for_same_seed() -> None:
    state_a = new_game(1)
    state_b = new_game(1)
    for state in (state_a, state_b):
        state.phase = Phase.MORNING
        _place_all(state, Location.FIREPIT)

    moves_a = plan_needs_movements(state_a, SeededRng(42))
    moves_b = plan_needs_movements(state_b, SeededRng(42))

    assert [m.model_dump() for m in moves_a] == [m.model_dump() for m in moves_b]


def test_apply_needs_movements_sets_locations() -> None:
    state = new_game(1)
    npc = state.islanders[0]
    npc.location_id = Location.POOL
    move = NeedsMovement(
        npc_id=npc.id,
        from_location=Location.POOL,
        to_location=Location.TERRACE,
        role="terrace",
        score=40,
        reason="test",
    )

    apply_needs_movements(state, [move])

    assert npc.location_id is Location.TERRACE


def test_extraverts_prefer_social_spots_over_introverts() -> None:
    """At equal advertisement, extraverts score the pool higher than introverts."""
    state = new_game(1)
    state.phase = Phase.AFTERNOON
    extravert = state.islanders[0]
    introvert = state.islanders[1]
    extravert.big5.extraversion = 9
    introvert.big5.extraversion = 1
    # Put a crowd at the pool so the social term has something to act on.
    for islander in state.islanders[2:]:
        islander.location_id = Location.POOL

    extravert_score = destination_score(state, extravert, Location.POOL, SeededRng(1))
    introvert_score = destination_score(state, introvert, Location.POOL, SeededRng(1))

    assert extravert_score > introvert_score
