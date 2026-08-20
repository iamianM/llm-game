"""Tests for daily challenge mechanics."""

from __future__ import annotations

from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.challenges import (
    challenge_event_message,
    resolve_challenge,
    schedule_challenge,
)
from src.game.engine.turn import run_turn
from src.game.state.models import Challenge, Couple, new_game
from src.game.state.rng import SeededRng


def _drive_round_based_compat_quiz(seed: int, picks: list[str]):
    """Helper: drive the new round-based Compatibility Quiz to completion.

    Returns (state, challenge) post-application.
    """
    from src.game.engine.compatibility_quiz import (
        apply_compatibility_quiz_result,
        build_rounds,
        quiz_partner_id,
        score_compatibility_quiz,
        submit_choice,
    )
    from src.game.engine.question_bank import ensure_question_bank

    state = new_game(seed)
    state.couples = [Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=1)]
    ensure_question_bank(state)
    challenge = schedule_challenge(1)
    assert challenge is not None
    partner = quiz_partner_id(state)
    challenge.rounds = build_rounds(state, partner, SeededRng(seed).fork("compat_quiz_day1"))
    challenge.participants = ["player", partner]
    for pick in picks:
        current = challenge.rounds[challenge.current_round_index]
        if pick == "correct":
            choice_id = next(c.id for c in current.choices if c.is_correct)
        else:
            choice_id = next(c.id for c in current.choices if not c.is_correct)
        challenge = submit_choice(challenge, choice_id)
    challenge = score_compatibility_quiz(state, challenge)
    challenge = apply_compatibility_quiz_result(state, challenge)
    return state, challenge


def test_compatibility_quiz_success_applies_couple_strength_bonus() -> None:
    """All-correct picks on a fresh Day-1 partner hit the partial band; affection bumps."""
    state, challenge = _drive_round_based_compat_quiz(seed=1, picks=["correct"] * 5)

    assert challenge.classification in {"success", "partial"}
    assert challenge.total_points > 0
    chloe = next(i for i in state.heartbreakers if i.id == "chloe")
    # Partial gives affection +2; success gives +6. Either way >0.
    assert chloe.relationship.affection > 0


def test_compatibility_quiz_failure_applies_tension() -> None:
    """All-wrong picks: failure classification, partner trust drops by 3."""
    state, challenge = _drive_round_based_compat_quiz(seed=1, picks=["wrong"] * 5)

    assert challenge.classification == "failure"
    assert challenge.total_points == 0
    chloe = next(i for i in state.heartbreakers if i.id == "chloe")
    # _delta_for("failure") = RelationshipDelta(affection=-2, trust=-3); applied
    # via apply_relationship_delta which clamps to >=0, so trust ends at 0 or below
    # depending on starting value.
    assert challenge.deltas["chloe"].trust == -3
    # Wrong answers must also write quiz_misread KnownFacts and caught_unprepared memories.
    assert len(state.player.known_facts) == 5
    assert all(kf.source == "quiz_misread" for kf in state.player.known_facts.values())
    assert all(kf.confidence == 0.5 for kf in state.player.known_facts.values())
    caught = [m for m in chloe.memories if "caught_unprepared" in m.tags]
    assert len(caught) == 5


def test_heart_rate_uses_charm_when_directly_resolved() -> None:
    """Legacy single-roll path stays a no-op for migrated minigames."""
    state = new_game(1)
    state.player.stats.charm = 9
    challenge = schedule_challenge(2)
    assert challenge is not None
    # Heart Rate is now a round-based minigame; resolve_challenge no-ops
    # because the kind is in CHOICE_REQUIRED_CHALLENGES without a choice.
    resolved = resolve_challenge(state, challenge, SeededRng(1))
    assert resolved.stat_tested == "charm"
    assert resolved.result is None  # waiting for the reaction round


def test_couples_quiz_now_round_based() -> None:
    """The Couples Quiz now uses round-based dispatch; legacy resolve no-ops."""
    state = new_game(1)
    challenge = schedule_challenge(3)
    assert challenge is not None
    resolved = resolve_challenge(state, challenge, SeededRng(5))
    assert resolved.result is None


def test_lie_detector_now_round_based() -> None:
    """Lie Detector now uses round-based dispatch."""
    state = new_game(1)
    challenge = schedule_challenge(4)
    assert challenge is not None
    resolved = resolve_challenge(state, challenge, SeededRng(5))
    assert resolved.result is None


def test_kiss_wed_pass_now_round_based() -> None:
    """Kiss Wed Pass is now a round-based minigame; legacy resolve no-ops."""
    state = new_game(1)
    challenge = schedule_challenge(5)
    assert challenge is not None
    resolved = resolve_challenge(state, challenge, SeededRng(1))
    assert resolved.result is None  # not resolved by single-roll path anymore


def test_final_couples_now_round_based() -> None:
    """Final Couples now uses round-based dispatch."""
    state = new_game(1)
    challenge = schedule_challenge(6)
    assert challenge is not None
    resolved = resolve_challenge(state, challenge, SeededRng(1))
    assert resolved.stat_tested == "combined"
    assert resolved.result is None


def test_schedule_challenge_returns_correct_kind_per_day() -> None:
    challenge = schedule_challenge(4)

    assert challenge is not None
    assert challenge.kind == "lie_detector"


def test_schedule_challenge_returns_none_off_schedule() -> None:
    assert schedule_challenge(7) is None


def test_challenge_event_message_uses_player_facing_labels() -> None:
    challenge = schedule_challenge(5)
    assert challenge is not None

    message = challenge_event_message(challenge)

    assert message == "Kiss Wed Pass is still pending."


def test_resolved_challenge_clears_after_wrap_turn() -> None:
    """Resolved minigames stay for their wrap, then leave the playable surface."""
    state = new_game(1)
    state.pending_challenge = Challenge(
        id="final_couples",
        day=6,
        kind="final_couples",
        stat_tested="combined",
        participants=["player", "chloe"],
        result="success",
        classification="success",
        total_points=20,
    )

    result = run_turn(
        state,
        PlayerAction(kind=ActionKind.AMBIENT, target_id="pool_lounge"),
        SeededRng(1),
    )

    assert result.state.pending_challenge is None
    assert not any(event.kind == "challenge" for event in result.ceremony_events)
