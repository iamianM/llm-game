"""Tests for the round-based Compatibility Quiz minigame harness."""

from __future__ import annotations

import pytest

from src.game.content.minigame_balance import load_minigame_balance, reset_balance_cache
from src.game.engine.challenges import (
    ROUND_BASED_MINIGAMES,
    MinigameKind,
    apply_recovery_floor,
    schedule_challenge,
)
from src.game.engine.compatibility_quiz import (
    QUIZ_ROUNDS,
    apply_compatibility_quiz_result,
    build_rounds,
    has_more_rounds,
    quiz_partner_id,
    score_compatibility_quiz,
    submit_choice,
)
from src.game.engine.question_bank import build_question_bank, ensure_question_bank
from src.game.state.models import Couple, new_game
from src.game.state.rng import SeededRng
from src.game.state.snapshot import state_hash, state_hash_payload


def _state_with_partner(seed: int = 1):
    state = new_game(seed)
    state.couples = [Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=1)]
    ensure_question_bank(state)
    return state


def _drive_quiz(state, picks):
    challenge = schedule_challenge(1)
    assert challenge is not None
    partner = quiz_partner_id(state)
    rng = SeededRng(state.seed).fork("compat_quiz_day1")
    challenge.rounds = build_rounds(state, partner, rng)
    challenge.participants = ["player", partner]
    for pick in picks:
        current = challenge.rounds[challenge.current_round_index]
        if pick == "correct":
            cid = next(c.id for c in current.choices if c.is_correct)
        else:
            cid = next(c.id for c in current.choices if not c.is_correct)
        challenge = submit_choice(challenge, cid)
    challenge = score_compatibility_quiz(state, challenge)
    challenge = apply_compatibility_quiz_result(state, challenge)
    return challenge


# --- Configuration & enum sanity ----------------------------------------


def test_minigame_kind_enum_values_match_canonical_schedule() -> None:
    """The MinigameKind enum must mirror the daily schedule keys."""
    assert MinigameKind.COMPATIBILITY_QUIZ.value == "compatibility_quiz"
    assert "compatibility_quiz" in ROUND_BASED_MINIGAMES


def test_balance_data_loads_with_expected_thresholds() -> None:
    reset_balance_cache()
    bal = load_minigame_balance()
    assert bal.compatibility_quiz.rounds == 5
    assert bal.compatibility_quiz.thresholds.success == 14
    assert bal.compatibility_quiz.thresholds.partial == 8
    assert bal.recovery_floor.audience_threshold == 35


# --- apply_recovery_floor ----------------------------------------------


def test_recovery_floor_does_not_change_high_audience() -> None:
    state = new_game(1)
    state.player.public_perception = 80
    assert apply_recovery_floor(state, 1, "partial") == 1
    assert apply_recovery_floor(state, -2, "failure") == -2
    assert apply_recovery_floor(state, 4, "success") == 4


def test_recovery_floor_bonuses_partial_at_low_audience() -> None:
    state = new_game(1)
    state.player.public_perception = 20
    bal = load_minigame_balance().recovery_floor
    assert apply_recovery_floor(state, 1, "partial") == 1 + bal.partial_audience_bonus


def test_recovery_floor_dampens_failure_but_never_above_zero() -> None:
    state = new_game(1)
    state.player.public_perception = 20
    bal = load_minigame_balance().recovery_floor
    # -2 + 2 dampener = 0 (clamped at 0; never lifts above zero)
    assert apply_recovery_floor(state, -2, "failure") == 0
    # A large negative still gets dampened but stays negative.
    assert apply_recovery_floor(state, -5, "failure") == -5 + bal.failure_audience_dampener


def test_recovery_floor_never_modifies_success() -> None:
    state = new_game(1)
    state.player.public_perception = 10
    assert apply_recovery_floor(state, 4, "success") == 4


# --- Question Bank determinism ------------------------------------------


def test_question_bank_is_deterministic_for_same_seed() -> None:
    s1 = new_game(7)
    s2 = new_game(7)
    b1 = build_question_bank(s1)
    b2 = build_question_bank(s2)
    assert b1.bank_seed == b2.bank_seed
    assert len(b1.prompts["compatibility_quiz"]) == len(b2.prompts["compatibility_quiz"])
    for p1, p2 in zip(
        b1.prompts["compatibility_quiz"], b2.prompts["compatibility_quiz"], strict=True
    ):
        assert (p1.id, p1.correct_value, tuple(p1.distractors)) == (
            p2.id,
            p2.correct_value,
            tuple(p2.distractors),
        )


def test_question_bank_includes_both_mechanical_and_flavor_traits() -> None:
    state = new_game(1)
    bank = build_question_bank(state)
    prompts = bank.prompts["compatibility_quiz"]
    assert any(p.mechanical for p in prompts), "expected mechanical prompts"
    assert any(not p.mechanical for p in prompts), "expected flavor prompts"


# --- build_rounds ------------------------------------------------------


def test_build_rounds_produces_exactly_five_rounds_with_distinct_traits() -> None:
    state = _state_with_partner()
    rounds = build_rounds(state, "chloe", SeededRng(state.seed).fork("compat_quiz_day1"))
    assert len(rounds) == QUIZ_ROUNDS
    trait_keys = [r.trait_key for r in rounds]
    assert len(set(trait_keys)) == QUIZ_ROUNDS, f"duplicate trait_keys: {trait_keys}"


def test_build_rounds_day1_pool_mixes_mechanical_and_flavor() -> None:
    """Day 1 (low familiarity) mixes Tier-1 mechanical with flavor padding."""
    state = _state_with_partner()
    rounds = build_rounds(state, "chloe", SeededRng(state.seed).fork("compat_quiz_day1"))
    mechanical = [r for r in rounds if r.mechanical]
    flavor = [r for r in rounds if not r.mechanical]
    assert len(mechanical) > 0
    assert len(flavor) > 0
    assert all(r.tier <= 1 for r in mechanical), "Day-1 mechanical rounds should be Tier 1 only"


def test_build_rounds_records_quizzed_traits_at_selection() -> None:
    state = _state_with_partner()
    rounds = build_rounds(state, "chloe", SeededRng(state.seed).fork("compat_quiz_day1"))
    ledger = state.quizzed_traits_this_run["chloe"]
    assert len(ledger) == QUIZ_ROUNDS
    for r in rounds:
        assert r.trait_key in ledger


def test_build_rounds_each_round_has_four_choices_with_one_correct() -> None:
    state = _state_with_partner()
    rounds = build_rounds(state, "chloe", SeededRng(state.seed).fork("compat_quiz_day1"))
    for r in rounds:
        assert len(r.choices) == 4
        correct = [c for c in r.choices if c.is_correct]
        assert len(correct) == 1


# --- Scoring & classification ------------------------------------------


def test_all_correct_at_low_familiarity_lands_in_partial_band() -> None:
    """Fresh-partner Day-1 ceiling is ~8 pts (3 Tier-1 + 2 flavor); partial only."""
    state = _state_with_partner()
    challenge = _drive_quiz(state, ["correct"] * 5)
    assert challenge.classification == "partial"
    assert challenge.total_points >= 8
    assert challenge.total_points < 14


def test_all_wrong_classifies_failure_and_zero_points() -> None:
    state = _state_with_partner()
    challenge = _drive_quiz(state, ["wrong"] * 5)
    assert challenge.classification == "failure"
    assert challenge.total_points == 0


def test_threshold_edge_at_partial_threshold() -> None:
    """3 correct Tier-1 mechanical (6 pts) + 2 wrong flavor (0 pts) = 6 = failure."""
    state = _state_with_partner()
    challenge = _drive_quiz(state, ["correct"] * 3 + ["wrong"] * 2)
    # 3*2 + 2*0 = 6, below partial threshold of 8
    assert challenge.classification == "failure"
    assert challenge.total_points == 6


# --- Side effects ------------------------------------------------------


def test_wrong_answer_writes_quiz_misread_known_facts_at_half_confidence() -> None:
    state = _state_with_partner()
    _drive_quiz(state, ["wrong"] * 5)
    assert len(state.player.known_facts) == 5
    for kf in state.player.known_facts.values():
        assert kf.source == "quiz_misread"
        assert kf.confidence == 0.5


def test_correct_answer_writes_compatibility_quiz_known_facts_at_full_confidence() -> None:
    state = _state_with_partner()
    _drive_quiz(state, ["correct"] * 5)
    assert len(state.player.known_facts) == 5
    for kf in state.player.known_facts.values():
        assert kf.source == "compatibility_quiz"
        assert kf.confidence == 1.0


def test_wrong_answer_creates_caught_unprepared_memory_per_round() -> None:
    state = _state_with_partner()
    _drive_quiz(state, ["wrong"] * 5)
    chloe = next(i for i in state.islanders if i.id == "chloe")
    caught = [m for m in chloe.memories if "caught_unprepared" in m.tags]
    assert len(caught) == 5


def test_correct_answers_skip_caught_unprepared_memory() -> None:
    state = _state_with_partner()
    _drive_quiz(state, ["correct"] * 5)
    chloe = next(i for i in state.islanders if i.id == "chloe")
    assert not any("caught_unprepared" in m.tags for m in chloe.memories)


def test_failure_audience_dampened_under_floor() -> None:
    state = _state_with_partner()
    state.player.public_perception = 20  # below floor threshold of 35
    challenge = _drive_quiz(state, ["wrong"] * 5)
    # Nominal failure delta is -5; recovery floor adds +2 dampener -> -3.
    # (Floor never lifts a failure above zero, but it softens the blow.)
    assert challenge.audience_delta == -3


def test_failure_audience_full_above_floor() -> None:
    state = _state_with_partner()
    state.player.public_perception = 80  # above floor threshold
    challenge = _drive_quiz(state, ["wrong"] * 5)
    assert challenge.audience_delta == -5


# --- Determinism --------------------------------------------------------


def test_same_seed_and_picks_produce_identical_state_hash() -> None:
    s1 = _state_with_partner(seed=99)
    s2 = _state_with_partner(seed=99)
    _drive_quiz(s1, ["correct"] * 5)
    _drive_quiz(s2, ["correct"] * 5)
    assert state_hash(state_hash_payload(s1)) == state_hash(state_hash_payload(s2))


def test_different_picks_diverge_state_hash() -> None:
    s1 = _state_with_partner(seed=99)
    s2 = _state_with_partner(seed=99)
    _drive_quiz(s1, ["correct"] * 5)
    _drive_quiz(s2, ["wrong"] * 5)
    assert state_hash(state_hash_payload(s1)) != state_hash(state_hash_payload(s2))


def test_submit_choice_rejects_invalid_choice_id() -> None:
    state = _state_with_partner()
    challenge = schedule_challenge(1)
    assert challenge is not None
    partner = quiz_partner_id(state)
    challenge.rounds = build_rounds(state, partner, SeededRng(state.seed).fork("compat_quiz_day1"))
    with pytest.raises(ValueError, match="unknown choice_id"):
        submit_choice(challenge, "bogus_choice_id")


def test_has_more_rounds_progression() -> None:
    state = _state_with_partner()
    challenge = schedule_challenge(1)
    assert challenge is not None
    partner = quiz_partner_id(state)
    challenge.rounds = build_rounds(state, partner, SeededRng(state.seed).fork("compat_quiz_day1"))
    assert has_more_rounds(challenge)
    for _ in range(QUIZ_ROUNDS):
        assert has_more_rounds(challenge)
        cur = challenge.rounds[challenge.current_round_index]
        cid = next(c.id for c in cur.choices if c.is_correct)
        challenge = submit_choice(challenge, cid)
    assert not has_more_rounds(challenge)
