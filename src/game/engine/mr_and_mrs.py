"""The Couples Quiz (mr_and_mrs) minigame.

Six rounds, alternating direction:
  even rounds (0, 2, 4): player answers about partner (standard quiz round)
  odd rounds (1, 3, 5):  partner pre-answers about player; player picks
                         the answer they BELIEVE the partner gave.

Pure-Python partner guess is computed deterministically from partner's
known_facts about the player. See ``docs/minigames/couples-quiz.md``.
"""

from __future__ import annotations

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
from src.game.state.models import GameState, RelationshipDelta
from src.game.state.rng import SeededRng
from src.game.state.traits import KnownFact, TIER_THRESHOLDS


ROUNDS = 6


def _partner_id(state: GameState) -> str | None:
    couple = player_couple(state)
    if couple is None:
        return None
    return couple.partner_b_id if couple.partner_a_id == "player" else couple.partner_a_id


def _bank_for(state: GameState, target_id: str) -> list[QuestionBankPrompt]:
    bank = state.question_bank
    if bank is None:
        return []
    return [p for p in bank.prompts.get("compatibility_quiz", []) if p.target_id == target_id]


def _shuffle(items: list, rng: SeededRng) -> None:
    for i in range(len(items) - 1, 0, -1):
        j = rng.randint(0, i)
        items[i], items[j] = items[j], items[i]


_DISPLAY_LABELS: dict[str, dict[str, str]] = {
    "archetype": {
        "heartthrob": "the Heartthrob",
        "class_clown": "the Class Clown",
        "loyal_friend": "the Loyal Friend",
        "balanced": "all-rounder",
    },
    "gender": {
        "man": "a man",
        "woman": "a woman",
    },
    "perception": {
        "high": "audience favourite",
        "mid": "audience steady",
        "low": "audience cool on them",
    },
}


def _display_label(fact_key: str, raw_value: str) -> str:
    return _DISPLAY_LABELS.get(fact_key, {}).get(raw_value, raw_value)


def _player_self_facts(state: GameState) -> dict[str, str]:
    """Synthesize a simple 'self trait card' from the player state.

    For this minigame partner guesses must compare against player traits.
    The player has no Trait Card in v0; we derive a tiny synthetic set
    from explicit state and known archetype tags.
    """
    facts: dict[str, str] = {
        "archetype": state.player.archetype_id,
        "gender": state.player.gender.value,
        "perception": "high" if state.player.public_perception >= 60 else ("low" if state.player.public_perception < 40 else "mid"),
    }
    return facts


def _partner_guess_about_player(state: GameState, partner_id: str, fact_key: str) -> str:
    """Deterministically compute the partner's belief about a player fact."""
    partner = find_islander(state, partner_id)
    truth = _player_self_facts(state).get(fact_key)
    # If partner familiarity with the player is high, they guess correctly.
    if partner.familiarity_with_player >= 50 and truth is not None:
        return truth
    if partner.familiarity_with_player >= 25:
        return truth or "unknown"
    return "unknown"


def build_rounds(state: GameState, partner_id: str, rng: SeededRng) -> list[MinigameRound]:
    assert state.question_bank is not None
    pool = _bank_for(state, partner_id)
    partner = find_islander(state, partner_id)
    used = set(state.quizzed_traits_this_run.get(partner_id, []))

    # Player-rounds eligibility: same priority ladder as compat quiz
    def eligible(p: QuestionBankPrompt) -> bool:
        if p.trait_key in used:
            return False
        if not p.mechanical:
            return True
        if p.tier <= 1:
            return True
        if partner.familiarity_with_player >= TIER_THRESHOLDS[p.tier]:
            return True
        fact_key = f"{partner_id}.{p.trait_key}"
        kf = state.player.known_facts.get(fact_key)
        return kf is not None and kf.confidence >= 0.7

    eligible_pool = [p for p in pool if eligible(p)]
    eligible_pool.sort(key=lambda p: p.id)

    # Build six rounds: 3 player-rounds (0,2,4) drawn from eligible_pool;
    # 3 partner-rounds (1,3,5) covering player facts in a fixed order.
    partner_keys = ["archetype", "gender", "perception"]
    rounds: list[MinigameRound] = []
    player_picks: list[QuestionBankPrompt] = eligible_pool[:3]

    # Pad if needed (shouldn't happen on Day 3 with normal pool size)
    while len(player_picks) < 3 and pool:
        for p in pool:
            if p not in player_picks:
                player_picks.append(p)
                break

    for index in range(ROUNDS):
        if index % 2 == 0:
            # Player round about partner
            pi = index // 2
            if pi >= len(player_picks):
                break
            prompt = player_picks[pi]
            from src.game.agents.trait_generator import _neutralize_for_distractor
            target_gender = partner.gender.value if partner.gender else None
            peer_genders = {i.id: (i.gender.value if i.gender else None) for i in state.islanders}
            distractors = [
                (_neutralize_for_distractor(d, target_gender) or d) for d in prompt.distractors
            ]
            # Pad distractors from same-key cross-islander values, preferring
            # same-gender peers and stripping/skipping gendered tails so a
            # woman's quiz doesn't show "from his dad" / "his bicycle bell".
            if len(distractors) < 3:
                bank = state.question_bank.prompts.get("compatibility_quiz", [])
                others = [o for o in bank if o.trait_key == prompt.trait_key and o.target_id != prompt.target_id]
                others.sort(key=lambda p: (peer_genders.get(p.target_id) != target_gender, p.id))
                for o in others:
                    if o.correct_value == prompt.correct_value:
                        continue
                    cleaned = _neutralize_for_distractor(o.correct_value, target_gender)
                    if cleaned is None or cleaned in distractors:
                        continue
                    distractors.append(cleaned)
                    if len(distractors) >= 3:
                        break
            round_rng = rng.fork(f"mr_and_mrs::round::{index}")
            _shuffle(distractors, round_rng)
            choices = [
                MinigameChoice(id="correct", label=prompt.correct_value, fact_value=prompt.correct_value, is_correct=True, distractor_source="trait_card"),
            ]
            for d_index, val in enumerate(distractors[:3]):
                choices.append(MinigameChoice(id=f"distractor_{d_index}", label=val, fact_value=val, is_correct=False, distractor_source="trait_card"))
            _shuffle(choices, round_rng)
            if index == 0:
                scene = (
                    f"The Couples Quiz starts. {partner.name} is sat in the soundproof "
                    "booth on one side; you're at the firepit with a clipboard. The "
                    "host alternates — odd rounds you guess what {partner_name} would "
                    "say, even rounds you guess what they wrote about you. Round one is "
                    f"about {partner.name}: "
                ).replace("{partner_name}", partner.name)
                stem = f"{scene}{prompt.stem}"
            else:
                stem = f"Round {index + 1} — about {partner.name}: {prompt.stem}"
            rounds.append(MinigameRound(
                index=index,
                prompt_id=prompt.id,
                target_id=partner_id,
                trait_key=prompt.trait_key,
                tier=prompt.tier,
                mechanical=prompt.mechanical,
                stem=stem,
                choices=choices,
            ))
            state.quizzed_traits_this_run.setdefault(partner_id, []).append(prompt.trait_key)
        else:
            # Partner round about player. The question is "what did the partner
            # GUESS about you?" — so the correct choice is whatever the partner
            # actually guessed, NOT the player's underlying truth. At low
            # familiarity partner_guess can differ from truth and the player
            # has to predict the misread.
            pi = (index - 1) // 2
            if pi >= len(partner_keys):
                break
            fact_key = partner_keys[pi]
            truth = _player_self_facts(state).get(fact_key, "unknown")
            partner_guess = _partner_guess_about_player(state, partner_id, fact_key)
            distractor_pool = {
                "archetype": ["heartthrob", "class_clown", "loyal_friend", "balanced"],
                "gender": ["man", "woman"],
                "perception": ["high", "mid", "low"],
            }.get(fact_key, [])
            # If partner_guess landed on "unknown" (low-familiarity), force a
            # plausible non-truth pick so the choice list reflects something
            # the player can predict against.
            if partner_guess == "unknown" or partner_guess not in distractor_pool:
                # Pick the first deterministic non-truth value as the partner's guess.
                non_truth = [d for d in distractor_pool if d != truth]
                partner_guess = non_truth[0] if non_truth else truth
            # Build choices: correct = partner_guess; other distractor_pool
            # values fill the remaining slots (truth among them if not the
            # guess, so the player has the option to "tell the truth" and
            # be wrong about the prediction).
            other_choices = [d for d in distractor_pool if d != partner_guess][:3]
            round_rng = rng.fork(f"mr_and_mrs::round::{index}")
            _shuffle(other_choices, round_rng)
            choices = [
                MinigameChoice(
                    id="correct",
                    label=_display_label(fact_key, partner_guess),
                    fact_value=partner_guess,
                    is_correct=True,
                    distractor_source="trait_card",
                ),
            ]
            for d_index, val in enumerate(other_choices[:3]):
                choices.append(MinigameChoice(
                    id=f"distractor_{d_index}",
                    label=_display_label(fact_key, val),
                    fact_value=val,
                    is_correct=False,
                    distractor_source="trait_card",
                ))
            _shuffle(choices, round_rng)
            stem_question = {
                "archetype": f"In the booth, {partner.name} was asked what villa type you came in as — what did they write down?",
                "gender": f"In the booth, {partner.name} was asked what they wrote about you on the form — what did they say?",
                "perception": f"In the booth, the host asked {partner.name} how the audience reads you — what did they say?",
            }.get(fact_key, f"What did {partner.name} guess about your {fact_key}?")
            rounds.append(MinigameRound(
                index=index,
                prompt_id=f"mrandmrs_partner_{fact_key}",
                target_id=partner_id,
                trait_key=f"player_{fact_key}",
                tier=0,
                mechanical=False,
                stem=(
                    f"Round {index + 1} — partner's turn. {stem_question} (Pick what "
                    f"{partner.name} actually said, not what's true.)"
                ),
                choices=choices,
                reveals=[
                    MinigameReveal(
                        kind="fact",
                        subject_id=partner_id,
                        payload={"partner_guess": partner_guess, "truth": truth, "fact_key": fact_key, "direction": "partner_about_player"},
                    )
                ],
            ))
    return rounds


def submit_choice(challenge: Challenge, choice_id: str) -> Challenge:
    if challenge.classification is not None:
        raise ValueError("mr_and_mrs already resolved")
    cur = challenge.rounds[challenge.current_round_index]
    if not any(c.id == choice_id for c in cur.choices):
        raise ValueError(f"unknown choice_id {choice_id}")
    new_round = cur.model_copy(update={"chosen_id": choice_id})
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


def score_mr_and_mrs(state: GameState, challenge: Challenge) -> Challenge:
    bal = load_minigame_balance().mr_and_mrs
    p = bal.per_round_points
    total = 0
    new_rounds: list[MinigameRound] = []
    mismatch_streak = 0
    streak_hit = False
    for r in challenge.rounds:
        chosen = next((c for c in r.choices if c.id == r.chosen_id), None)
        if chosen is None:
            new_rounds.append(r); continue
        if r.index % 2 == 0:
            # Player round: simple correct/incorrect
            matched = chosen.is_correct
            pts = p.one_correct if matched else p.mismatch
        else:
            # Partner round: compare to recorded partner_guess
            partner_guess = None
            for rv in r.reveals:
                if rv.kind == "fact" and "partner_guess" in rv.payload:
                    partner_guess = rv.payload["partner_guess"]
                    break
            matched = chosen.fact_value == partner_guess
            pts = p.both_match if matched else p.mismatch
        if matched:
            mismatch_streak = 0
        else:
            mismatch_streak += 1
            if mismatch_streak >= 3:
                streak_hit = True
        total += pts
        new_rounds.append(r.model_copy(update={"points": pts}))
    if total >= bal.thresholds.success:
        classification = "success"
    elif total >= bal.thresholds.partial:
        classification = "partial"
    else:
        classification = "failure"
    audience = getattr(bal.audience, classification)
    if streak_hit:
        audience += bal.audience.streak_three_mismatch_penalty
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


def apply_mr_and_mrs_result(state: GameState, challenge: Challenge) -> Challenge:
    partner_id = _partner_id(state) or "chloe"
    partner = find_islander(state, partner_id)
    cls = challenge.classification or "failure"
    if cls == "success":
        delta = RelationshipDelta(friendship=5, affection=3, trust=2)
    elif cls == "partial":
        delta = RelationshipDelta(friendship=1)
    else:
        delta = RelationshipDelta(friendship=-3, affection=-2)
    apply_relationship_delta(partner, delta)
    state.player.public_perception = max(
        0, min(100, state.player.public_perception + challenge.audience_delta)
    )
    # KnownFact writes for player rounds
    for r in challenge.rounds:
        chosen = next((c for c in r.choices if c.id == r.chosen_id), None)
        if chosen is None or r.trait_key is None:
            continue
        if r.index % 2 != 0:
            continue  # partner-rounds don't write player KnownFacts about the partner
        correct_value = next(c.fact_value for c in r.choices if c.is_correct)
        fact_key = f"{partner_id}.{r.trait_key}"
        state.player.known_facts[fact_key] = KnownFact(
            fact_key=fact_key, value=correct_value or "",
            source="compatibility_quiz" if chosen.is_correct else "quiz_misread",
            source_npc_id=partner_id, learned_on_day=state.day, learned_on_turn=state.turn_index,
            confidence=1.0 if chosen.is_correct else 0.5,
            citation=f"mr_and_mrs day {state.day}",
        )
    return challenge.model_copy(update={"participants": ["player", partner_id], "deltas": {partner_id: delta}})
