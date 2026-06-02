"""Tests for ambient NPC approach mechanics (engine/approach.py)."""

from __future__ import annotations

from src.game.engine.actions import ActionKind, PlayerAction, validate_action
from src.game.engine.approach import (
    APPROACH_INTENT_KINDS,
    apply_approach_response,
    approach_candidates,
    approach_chance,
    roll_ambient_approach,
)
from src.game.state.models import (
    GameState,
    Location,
    Mood,
    NPCNPCConversation,
    Phase,
    new_game,
)
from src.game.state.rng import SeededRng


def _place_with_player(state: GameState, *heartbreaker_ids: str) -> None:
    """Co-locate the named heartbreakers with the player; banish everyone else."""
    state.location_id = Location.POOL
    for heartbreaker in state.heartbreakers:
        heartbreaker.location_id = (
            Location.POOL if heartbreaker.id in heartbreaker_ids else Location.BEDROOM
        )


def test_candidates_only_co_located_and_free() -> None:
    state = new_game(1)
    _place_with_player(state, "chloe", "maya")
    state.heartbreakers[2].location_id = Location.POOL  # liam co-located too
    state.heartbreakers[2].eliminated = True  # ...but eliminated
    # Lock maya into an NPC-NPC conversation.
    state.npc_conversations.append(
        NPCNPCConversation(
            id="npcconv_busy",
            participants=["maya", "sophie"],
            location_id=Location.POOL,
            topic="x",
            started_on_turn=0,
        )
    )

    ids = {npc.id for npc in approach_candidates(state)}

    assert "chloe" in ids
    assert "maya" not in ids  # locked
    assert "liam" not in ids  # eliminated
    assert "sophie" not in ids  # not co-located


def test_chance_rises_with_chemistry_and_extraversion() -> None:
    state = new_game(1)
    _place_with_player(state, "chloe")
    npc = state.heartbreakers[0]
    npc.big5.extraversion = 5
    npc.relationship.chemistry = 0
    npc.relationship.affection = 0
    low = approach_chance(state, npc, encounter_boost=0)
    npc.relationship.chemistry = 60
    npc.big5.extraversion = 9
    high = approach_chance(state, npc, encounter_boost=0)

    assert high > low


def test_encounter_boost_increases_chance() -> None:
    state = new_game(1)
    _place_with_player(state, "chloe")
    npc = state.heartbreakers[0]
    no_boost = approach_chance(state, npc, encounter_boost=0)
    with_boost = approach_chance(state, npc, encounter_boost=14)

    assert with_boost - no_boost == 14


def test_roll_sets_pending_when_chance_is_high() -> None:
    state = new_game(1)
    _place_with_player(state, "chloe")
    # Crank chloe so her approach is near-certain.
    chloe = state.heartbreakers[0]
    chloe.relationship.chemistry = 90
    chloe.relationship.affection = 90
    chloe.big5.extraversion = 10
    chloe.mood = Mood.FLIRTY

    approach = roll_ambient_approach(state, SeededRng(2))

    assert approach is not None
    assert approach.npc_id == "chloe"
    assert state.pending_npc_approach is approach


def test_roll_none_when_no_candidates() -> None:
    state = new_game(1)
    # Send everyone away from the player.
    state.location_id = Location.PRIVATE_SUITE
    for heartbreaker in state.heartbreakers:
        heartbreaker.location_id = Location.POOL

    assert roll_ambient_approach(state, SeededRng(1)) is None
    assert state.pending_npc_approach is None


def test_engage_warms_relationship_and_resets_ambient() -> None:
    state = new_game(1)
    _place_with_player(state, "chloe")
    state.active_ambient_id = "pool_lounge"
    roll_ambient_approach(state, SeededRng(2))
    state.pending_npc_approach = _force_pending(state, "chloe")
    before = state.heartbreakers[0].relationship.affection

    result = apply_approach_response(
        state,
        PlayerAction(kind=ActionKind.RESPOND_WITH, target_id="chloe", intent_id="engage_approach"),
        SeededRng(1),
    )

    assert state.heartbreakers[0].relationship.affection > before
    assert state.pending_npc_approach is None
    assert state.active_ambient_id is None
    assert result.success


def test_wave_off_firmly_seeds_gossip_and_walks_away() -> None:
    state = new_game(1)
    _place_with_player(state, "chloe")
    state.pending_npc_approach = _force_pending(state, "chloe")
    before = state.heartbreakers[0].relationship.affection

    result = apply_approach_response(
        state,
        PlayerAction(kind=ActionKind.RESPOND_WITH, target_id="chloe", intent_id="wave_off_firmly"),
        SeededRng(1),
    )

    chloe = state.heartbreakers[0]
    assert chloe.relationship.affection == before - 4
    assert chloe.location_id is not Location.POOL  # walked away
    assert result.forced_movements
    # A snub memory seeds gossip about the player.
    assert any(
        m.subject_id == "player" and "interruption" in m.tags for m in chloe.memories
    )


def test_ignore_is_milder_and_seeds_no_public_snub() -> None:
    state = new_game(1)
    _place_with_player(state, "chloe")
    state.pending_npc_approach = _force_pending(state, "chloe")
    before = state.heartbreakers[0].relationship.affection
    memories_before = len(state.heartbreakers[0].memories)

    apply_approach_response(
        state,
        PlayerAction(kind=ActionKind.RESPOND_WITH, target_id="chloe", intent_id="ignore_approach"),
        SeededRng(1),
    )

    chloe = state.heartbreakers[0]
    assert chloe.relationship.affection == before - 2
    assert len(chloe.memories) == memories_before  # no public snub memory
    assert state.pending_npc_approach is None


def test_validate_requires_pending_approach() -> None:
    state = new_game(1)
    state.phase = Phase.AFTERNOON
    _place_with_player(state, "chloe")
    action = PlayerAction(
        kind=ActionKind.RESPOND_WITH, target_id="chloe", intent_id="engage_approach"
    )
    try:
        validate_action(state, action)
        raise AssertionError("expected validation to fail without a pending approach")
    except ValueError:
        pass

    state.pending_npc_approach = _force_pending(state, "chloe")
    validate_action(state, action)  # now allowed


def test_all_intent_kinds_clear_pending() -> None:
    for intent in APPROACH_INTENT_KINDS:
        state = new_game(1)
        _place_with_player(state, "chloe")
        state.pending_npc_approach = _force_pending(state, "chloe")
        apply_approach_response(
            state,
            PlayerAction(kind=ActionKind.RESPOND_WITH, target_id="chloe", intent_id=intent),
            SeededRng(1),
        )
        assert state.pending_npc_approach is None, intent


def test_approach_response_labels_are_clean_and_named() -> None:
    """The four approach responses surface player-facing copy with no enum leak.

    Regression guard: labels must name the approacher and must NOT expose raw
    internal tags like ``(wants_to_chat, keen)`` or ``(polite)``. We assert the
    serialized AvailableAction labels (what the web renders), not the raw spec.
    """
    from src.api.serializers import available_action
    from src.game.engine.actions import available_actions

    engage_by_reason = {
        "wants_to_chat": "Welcome Chloe over for a chat",
        "has_gossip": "Lean in — let Chloe spill the gossip",
        "flirty": "Flirt back with Chloe",
        "curious": "See what Chloe wants",
    }
    leak_tokens = ["wants_to_chat", "has_gossip", "flirty", "curious",
                   "casual", "keen", "intense", "polite", "engage_approach",
                   "wave_off", "ignore_approach"]

    for reason, expected_engage in engage_by_reason.items():
        state = new_game(1)
        state.phase = Phase.AFTERNOON
        _place_with_player(state, "chloe")
        pending = _force_pending(state, "chloe")
        pending.reason = reason  # type: ignore[assignment]
        state.pending_npc_approach = pending

        specs = available_actions(state)
        labels = [available_action(state, spec).label for spec in specs]

        assert labels == [
            expected_engage,
            "Wave Chloe off gently",
            "Brush Chloe off",
            "Pretend not to notice Chloe",
        ], (reason, labels)
        for label in labels:
            assert "Chloe" in label, label
            for token in leak_tokens:
                assert token not in label, (reason, token, label)


def test_deterministic_for_same_seed() -> None:
    results = []
    for _ in range(2):
        state = new_game(1)
        _place_with_player(state, "chloe", "jordan")
        for npc in state.heartbreakers:
            npc.relationship.chemistry = 40
        approach = roll_ambient_approach(state, SeededRng(99))
        results.append(None if approach is None else approach.model_dump())
    assert results[0] == results[1]


def _force_pending(state: GameState, npc_id: str):
    from src.game.state.autonomy import PendingNPCApproach

    return PendingNPCApproach(
        npc_id=npc_id,
        location_id=state.location_id.value,
        reason="wants_to_chat",
        warmth="keen",
        desire=40,
    )
