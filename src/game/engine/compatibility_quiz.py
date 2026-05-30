"""Compatibility Quiz minigame implementation.

Round-based replacement for the legacy ``compatibility_quiz`` single-roll
path in :mod:`src.game.engine.challenges`. See ``docs/minigame-system.md``
for the shared harness contract and ``docs/minigames/compatibility-quiz.md``
for this minigame's contract.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from src.game.content.minigame_balance import load_minigame_balance
from src.game.engine.audience import player_couple
from src.game.engine.challenges import apply_recovery_floor
from src.game.engine.state_access import apply_relationship_delta, find_islander
from src.game.state.event_models import (
    Challenge,
    MinigameChoice,
    MinigameReveal,
    MinigameRound,
    QuestionBankPrompt,
)
from src.game.state.models import GameState, IslanderState, RelationshipDelta
from src.game.state.rng import SeededRng
from src.game.state.traits import TIER_THRESHOLDS, KnownFact

QUIZ_ROUNDS = 5
ROUND_KIND = "compatibility_quiz"
T = TypeVar("T")


def _shuffle_in_place(items: list[T], rng: SeededRng) -> None:
    """Deterministic in-place Fisher-Yates shuffle using SeededRng.randint."""
    n = len(items)
    for i in range(n - 1, 0, -1):
        j = rng.randint(0, i)
        items[i], items[j] = items[j], items[i]




def quiz_partner_id(state: GameState) -> str:
    """Return the islander id the quiz tests. Uses the current player couple."""
    couple = player_couple(state)
    if couple is not None:
        return couple.partner_b_id if couple.partner_a_id == "player" else couple.partner_a_id
    # Fall back to the first islander deterministically.
    for islander in state.islanders:
        if not islander.eliminated:
            return islander.id
    raise ValueError("no eligible quiz partner")


def is_prompt_eligible(state: GameState, prompt: QuestionBankPrompt) -> bool:
    """Eligibility per docs/minigames/compatibility-quiz.md §2."""
    target = find_islander(state, prompt.target_id)
    used = set(state.quizzed_traits_this_run.get(target.id, []))
    if prompt.trait_key in used:
        return False
    if not prompt.mechanical:
        return True
    if prompt.tier <= 1:
        return True
    if target.familiarity_with_player >= TIER_THRESHOLDS[prompt.tier]:
        return True
    fact_key = f"{target.id}.{prompt.trait_key}"
    existing = state.player.known_facts.get(fact_key)
    return existing is not None and existing.confidence >= 0.7


def build_rounds(state: GameState, target_id: str, rng: SeededRng) -> list[MinigameRound]:
    """Build five rounds with the §2 priority ladder.

    Priority: Tier 2+ mechanical -> Tier 1 mechanical -> flavor -> exhaustion fallback.
    """
    assert state.question_bank is not None, "question_bank must be initialized"
    pool = [p for p in state.question_bank.prompts.get("compatibility_quiz", []) if p.target_id == target_id]
    eligible = [p for p in pool if is_prompt_eligible(state, p)]

    def bucket(predicate: Callable[[QuestionBankPrompt], bool]) -> list[QuestionBankPrompt]:
        items = [p for p in eligible if predicate(p)]
        items.sort(key=lambda p: p.id)
        return items

    selected: list[QuestionBankPrompt] = []
    for tier_predicate in (
        lambda p: p.mechanical and p.tier >= 2,
        lambda p: p.mechanical and p.tier == 1,
        lambda p: not p.mechanical,
    ):
        for prompt in bucket(tier_predicate):
            if len(selected) >= QUIZ_ROUNDS:
                break
            if prompt not in selected:
                selected.append(prompt)
        if len(selected) >= QUIZ_ROUNDS:
            break

    # Exhaustion fallback: repeats from the whole pool, marked as repeats below.
    repeats: set[str] = set()
    if len(selected) < QUIZ_ROUNDS:
        for prompt in sorted(pool, key=lambda p: p.id):
            if prompt in selected:
                continue
            selected.append(prompt)
            repeats.add(prompt.id)
            if len(selected) >= QUIZ_ROUNDS:
                break

    # The full bank, used when we need cross-islander distractors (e.g. flavor
    # traits whose trait card has no curated distractors). Without this the
    # fallback used to pull other-trait values from the same target, producing
    # nonsense like "26" as a distractor for a karaoke-song question.
    full_bank = state.question_bank.prompts.get("compatibility_quiz", [])

    rounds: list[MinigameRound] = []
    for index, prompt in enumerate(selected[:QUIZ_ROUNDS]):
        round_rng = rng.fork(f"compat_quiz::round::{index}")
        # Build choice list: correct + up to 3 distractors. Distractors come from
        # the trait card first, then from other islanders' values for the SAME
        # trait_key (so a "karaoke song" question's wrong answers are also
        # karaoke songs), and only as a last resort from other traits on the
        # same target. Cross-islander values get gender-filtered so a
        # woman's quiz doesn't get "from his dad" distractors mixed in.
        from src.game.agents.trait_generator import _neutralize_for_distractor
        round_target = find_islander(state, target_id)
        target_gender = round_target.gender.value if round_target.gender else None
        peer_islander_genders = {i.id: (i.gender.value if i.gender else None) for i in state.islanders}
        distractors: list[str] = []
        for value in prompt.distractors:
            if value != prompt.correct_value and value not in distractors:
                cleaned = _neutralize_for_distractor(value, target_gender) or value
                distractors.append(cleaned)
        if len(distractors) < 3:
            # Prefer same-gender peer values; cross-gender values only if they
            # can be cleanly neutralised.
            same_key_others = [
                other
                for other in full_bank
                if other.trait_key == prompt.trait_key and other.target_id != prompt.target_id
            ]
            same_key_others.sort(key=lambda p: (peer_islander_genders.get(p.target_id) != target_gender, p.id))
            for other in same_key_others:
                if other.correct_value == prompt.correct_value:
                    continue
                cleaned_peer = _neutralize_for_distractor(
                    other.correct_value,
                    target_gender,
                )
                if cleaned_peer is None or cleaned_peer in distractors:
                    continue
                distractors.append(cleaned_peer)
                if len(distractors) >= 3:
                    break
        # Final fallback: pad from any prompt of the same target (these are
        # always gender-safe since they describe the same islander).
        if len(distractors) < 3:
            for other in pool:
                if other.correct_value not in distractors and other.correct_value != prompt.correct_value:
                    distractors.append(other.correct_value)
                    if len(distractors) >= 3:
                        break
        _shuffle_in_place(distractors, round_rng)
        chosen_distractors = distractors[:3]

        choices: list[MinigameChoice] = [
            MinigameChoice(
                id="correct",
                label=prompt.correct_value,
                fact_value=prompt.correct_value,
                is_correct=True,
                distractor_source="trait_card",
            ),
        ]
        for d_index, value in enumerate(chosen_distractors):
            choices.append(
                MinigameChoice(
                    id=f"distractor_{d_index}",
                    label=value,
                    fact_value=value,
                    is_correct=False,
                    distractor_source="trait_card",
                )
            )
        _shuffle_in_place(choices, round_rng)

        if index == 0:
            partner_name = find_islander(state, target_id).name
            scene = (
                f"The Compatibility Quiz starts. {partner_name} is sat across "
                "from you on the bench while the host reads five questions about "
                "them and you pick the right answer. Get them right, win audience "
                "love; get them wrong and the truth pops up after the answer. "
                "Round one: "
            )
            stem = f"{scene}{prompt.stem}"
        else:
            stem = f"Round {index + 1}: {prompt.stem}"
        rounds.append(
            MinigameRound(
                index=index,
                prompt_id=prompt.id,
                target_id=target_id,
                trait_key=prompt.trait_key,
                tier=prompt.tier,
                mechanical=prompt.mechanical,
                stem=stem,
                choices=choices,
            )
        )
        # Update the season repeat-prevention ledger at selection time.
        state.quizzed_traits_this_run.setdefault(target_id, []).append(prompt.trait_key)
    return rounds


def submit_choice(challenge: Challenge, choice_id: str) -> Challenge:
    """Record the player choice for the current round and advance."""
    if challenge.classification is not None:
        raise ValueError("compat quiz already resolved")
    if challenge.current_round_index >= len(challenge.rounds):
        raise ValueError("no more rounds")
    round_ = challenge.rounds[challenge.current_round_index]
    if not any(c.id == choice_id for c in round_.choices):
        raise ValueError(f"unknown choice_id {choice_id} for round {round_.index}")
    new_round = round_.model_copy(update={"chosen_id": choice_id})
    new_rounds = list(challenge.rounds)
    new_rounds[challenge.current_round_index] = new_round
    return challenge.model_copy(
        update={
            "rounds": new_rounds,
            "current_round_index": challenge.current_round_index + 1,
        }
    )


def has_more_rounds(challenge: Challenge) -> bool:
    return challenge.current_round_index < len(challenge.rounds)


def score_compatibility_quiz(state: GameState, challenge: Challenge) -> Challenge:
    """Score the resolved quiz; pure (no state mutation, no LLM calls)."""
    bal = load_minigame_balance().compatibility_quiz
    points = bal.per_round_points
    total = 0
    new_rounds: list[MinigameRound] = []
    for r in challenge.rounds:
        chosen = next((c for c in r.choices if c.id == r.chosen_id), None)
        correct = chosen is not None and chosen.is_correct
        if not correct:
            pts = points.incorrect
        elif not r.mechanical:
            pts = points.correct_flavor
        else:
            pts = getattr(points, f"correct_tier{r.tier}")
        total += pts
        new_rounds.append(r.model_copy(update={"points": pts}))
    if total >= bal.thresholds.success:
        classification = "success"
    elif total >= bal.thresholds.partial:
        classification = "partial"
    else:
        classification = "failure"
    audience = getattr(bal.audience, classification)
    audience = apply_recovery_floor(state, audience, classification)
    return challenge.model_copy(
        update={
            "rounds": new_rounds,
            "total_points": total,
            "classification": classification,
            "audience_delta": audience,
            "result": "failure" if classification == "failure" else "success",
        }
    )


def attach_round_reaction(state: GameState, challenge: Challenge, round_index: int) -> Challenge:
    """Attach a partner reaction reveal to the round at ``round_index``.

    Idempotent: if the round already carries a reaction reveal it is not
    duplicated. Called from rules.py between rounds so the player sees a
    reaction in the same turn they submitted a choice.
    """
    if round_index < 0 or round_index >= len(challenge.rounds):
        return challenge
    r = challenge.rounds[round_index]
    if any(rv.kind == "reaction" and "line" in rv.payload for rv in r.reveals):
        return challenge
    chosen = next((c for c in r.choices if c.id == r.chosen_id), None)
    if chosen is None:
        return challenge
    target_id = (
        challenge.participants[1] if len(challenge.participants) > 1 else (r.target_id or "")
    )
    if not target_id:
        return challenge
    from src.game.engine.compatibility_quiz_reactions import reaction_line
    partner_name = find_islander(state, target_id).name
    # Fork once per quiz (not per round) so all rounds in the same quiz
    # share the same RNG-driven shift, letting round_index rotate cleanly.
    rng = SeededRng(state.seed).fork(f"compat_quiz::reaction::{state.day}")
    line = reaction_line(
        partner_name,
        mechanical=r.mechanical,
        tier=r.tier,
        correct=chosen.is_correct,
        rng=rng,
        round_index=r.index,
    )
    reaction = MinigameReveal(
        kind="reaction",
        subject_id=target_id,
        payload={"line": line, "correct": int(chosen.is_correct), "tier": r.tier},
    )
    new_round = r.model_copy(update={"reveals": [*r.reveals, reaction]})
    new_rounds = list(challenge.rounds)
    new_rounds[round_index] = new_round
    return challenge.model_copy(update={"rounds": new_rounds})


def _delta_for(classification: str) -> RelationshipDelta:
    if classification == "success":
        return RelationshipDelta(affection=6, trust=3)
    if classification == "partial":
        return RelationshipDelta(affection=2)
    return RelationshipDelta(affection=-2, trust=-3)


def apply_compatibility_quiz_result(state: GameState, challenge: Challenge) -> Challenge:
    """Apply side effects: relationship delta, audience, KnownFacts, memories."""
    target_id = quiz_partner_id(state) if len(challenge.participants) < 2 else challenge.participants[1]
    target = find_islander(state, target_id)
    cls = challenge.classification or "failure"
    delta = _delta_for(cls)
    apply_relationship_delta(target, delta)
    state.player.public_perception = max(
        0, min(100, state.player.public_perception + challenge.audience_delta)
    )

    new_rounds = list(challenge.rounds)
    for index, r in enumerate(new_rounds):
        if r.trait_key is None:
            continue
        chosen = next((c for c in r.choices if c.id == r.chosen_id), None)
        if chosen is None:
            continue
        correct_value = next(c.fact_value for c in r.choices if c.is_correct)
        correct = chosen.is_correct
        fact_key = f"{target_id}.{r.trait_key}"
        state.player.known_facts[fact_key] = KnownFact(
            fact_key=fact_key,
            value=correct_value or "",
            source="compatibility_quiz" if correct else "quiz_misread",
            source_npc_id=target_id,
            learned_on_day=state.day,
            learned_on_turn=state.turn_index,
            confidence=1.0 if correct else 0.5,
            citation=f"compatibility_quiz day {state.day}",
        )
        reveal_payload: dict[str, str | int] = {
            "trait_key": r.trait_key,
            "value": correct_value or "",
            "delivery": "confirmed" if correct else "post_reveal",
        }
        fact_reveal = MinigameReveal(kind="fact", subject_id=target_id, payload=reveal_payload)
        # Reaction reveals are attached per-round by rules.py via
        # attach_round_reaction so the player sees them between rounds.
        # Here we only append the fact reveal (avoid duplicates).
        new_rounds[index] = r.model_copy(
            update={"reveals": [*r.reveals, fact_reveal]}
        )
        if not correct:
            _record_caught_unprepared(target, r.trait_key, state.day, state.turn_index)
    # Couple-level reaction reveal on the wrap.
    tone = "delighted" if cls == "success" else "warm" if cls == "partial" else "stung"
    wrap_reveals: list[MinigameReveal] = [
        MinigameReveal(
            kind="reaction",
            subject_id=target_id,
            payload={"tone": tone, "points": challenge.total_points},
        )
    ]
    # Teaching hint: if the player just missed a tier threshold, name the
    # Tier-2 mechanical facts they could have unlocked with one more morning
    # chat. The hint surfaces as a `fact` reveal on the wrap with
    # delivery="hint" so the narrator can phrase it as a producer aside.
    hint = _familiarity_gap_hint(state, target, challenge)
    if hint is not None:
        wrap_reveals.append(hint)

    # Attach wrap reveals onto the final round so report packets and the
    # browser wrap view can render them after the round-by-round breakdown.
    if new_rounds:
        last = new_rounds[-1]
        new_rounds[-1] = last.model_copy(
            update={"reveals": [*last.reveals, *wrap_reveals]}
        )

    return challenge.model_copy(
        update={
            "rounds": new_rounds,
            "participants": ["player", target_id],
            "deltas": {target_id: delta},
        }
    )


def _familiarity_gap_hint(
    state: GameState, target: IslanderState, challenge: Challenge
) -> MinigameReveal | None:
    """Surface a producer-aside if the player was close to unlocking Tier 2.

    Only fires when (a) the partner's familiarity is within 10 of the Tier-2
    threshold (15-24) so the player can realistically reach it in another
    morning chat, AND (b) at least one un-quizzed Tier-2 mechanical fact
    exists on the partner's Trait Card.
    """
    fam = target.familiarity_with_player
    if not (TIER_THRESHOLDS[2] - 10 <= fam < TIER_THRESHOLDS[2]):
        return None
    used = set(state.quizzed_traits_this_run.get(target.id, []))
    locked_tier2 = [
        key for key, fact in target.trait_card.core_traits.items()
        if fact.tier == 2 and key not in used
    ]
    if not locked_tier2:
        return None
    # Name the first eligible key (deterministic by sort).
    locked_tier2.sort()
    return MinigameReveal(
        kind="fact",
        subject_id=target.id,
        payload={
            "trait_key": locked_tier2[0],
            "delivery": "hint",
            "familiarity_gap": TIER_THRESHOLDS[2] - fam,
        },
    )


def _record_caught_unprepared(
    target: IslanderState, trait_key: str, day: int, turn_index: int
) -> None:
    """Attach a ``caught_unprepared`` memory to the partner.

    Tag-only memory so the producer and Conversation Curator can reference it
    later. Emotional weight is moderate (4) so it surfaces in mid-tier
    summaries but does not dominate the partner's long-term memory.
    """
    from src.game.state.memory import Memory  # late import to avoid cycles

    memory_id = f"caught_unprepared::{target.id}::{trait_key}::{day}::{turn_index}"
    target.memories.append(
        Memory(
            id=memory_id,
            holder_id=target.id,
            subject_id="player",
            content=f"The player guessed wrong about my {trait_key.replace('_', ' ')} in the Compatibility Quiz.",
            source="direct",
            formed_on_day=day,
            formed_on_turn=turn_index,
            emotional_weight=4,
            tags=["caught_unprepared", "compatibility_quiz", trait_key],
            durable=True,
        )
    )
