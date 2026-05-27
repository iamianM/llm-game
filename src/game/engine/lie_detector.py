"""Lie Detector minigame.

Five rounds. Each prompt names a past event class (a kiss with another
islander, a hideaway visit, etc.). The player picks one of: truth, mild
lie, hard lie. Detection chance is computed from familiarity and public
visibility; caught lies feed gossip propagation.

See ``docs/minigames/lie-detector.md``.
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
)
from src.game.state.models import GameState, RelationshipDelta
from src.game.state.rng import SeededRng


ROUNDS = 5


def _partner_id(state: GameState) -> str | None:
    couple = player_couple(state)
    if couple is None:
        return None
    return couple.partner_b_id if couple.partner_a_id == "player" else couple.partner_a_id


def _event_truths(state: GameState) -> list[dict[str, object]]:
    """Synthesise the season's lie-worthy events from explicit state.

    Each entry is a dict with a prompt, the truthful answer, severity, and a
    visibility score (0..100) used by the detection model.
    """
    entries: list[dict[str, object]] = []
    partner = _partner_id(state)
    # 1. Hideaway: was anyone else in the hideaway?
    used = state.hideaway.used_on_day is not None
    hideaway_partner = state.hideaway.partner_id
    if used and hideaway_partner is not None and hideaway_partner != partner:
        entries.append({
            "prompt": f"Did you visit the Hideaway with anyone other than {find_islander(state, partner).name if partner else 'your partner'}?",
            "truth": "yes",
            "severity": "high",
            "visibility": 80,
        })
    # 2. Couple feelings: lingering attraction to a non-partner
    for npc in sorted(state.islanders, key=lambda i: i.id):
        if npc.id == partner or npc.eliminated:
            continue
        if npc.relationship.chemistry >= 60:
            entries.append({
                "prompt": f"Do you still feel something for {npc.name}?",
                "truth": "yes",
                "severity": "mid",
                "visibility": min(80, 30 + npc.relationship.chemistry // 2),
            })
            break
    # 3. First spark regret
    if partner:
        partner_islander = find_islander(state, partner)
        if partner_islander.relationship.affection < 30:
            entries.append({
                "prompt": "Are you still glad you paired with your current partner?",
                "truth": "no",
                "severity": "high",
                "visibility": 60,
            })
    # Pad with neutral questions until we have ROUNDS of them
    fallback_questions = [
        ("Have you been authentic with the rest of the cast this week?", "yes", "low", 20),
        ("Do you think you're the strongest connection on the island?", "no", "low", 15),
        ("If a Heart Throb walked in today, would you stay loyal?", "yes", "mid", 40),
        ("Are you here for love or for the show?", "yes", "mid", 30),
        ("Would you tell your partner if you flirted behind their back?", "yes", "mid", 35),
    ]
    for prompt, truth, severity, visibility in fallback_questions:
        if len(entries) >= ROUNDS:
            break
        entries.append({"prompt": prompt, "truth": truth, "severity": severity, "visibility": visibility})
    return entries[:ROUNDS]


def build_rounds(state: GameState, partner_id: str, rng: SeededRng) -> list[MinigameRound]:
    events = _event_truths(state)
    partner_name = (
        find_islander(state, partner_id).name if partner_id and partner_id != "player" else "your partner"
    )
    rounds: list[MinigameRound] = []
    for index, ev in enumerate(events):
        truth = ev["truth"]
        opposite = "no" if truth == "yes" else "yes"
        choices = [
            MinigameChoice(
                id="truth", label="Truth", fact_value=truth,
                is_correct=True, distractor_source="trait_card",
            ),
            MinigameChoice(
                id="lie_mild", label="Spin it: 'Not really.'",
                fact_value="not really", is_correct=False, distractor_source="lie",
            ),
            MinigameChoice(
                id="lie_hard", label=f"Bald-faced: '{opposite.capitalize()}.'",
                fact_value=opposite, is_correct=False, distractor_source="lie",
            ),
        ]
        # Stem sets the lie-detector scene each round, then asks the
        # question. The host's stage direction makes the format obvious
        # even to a player who's never seen the show.
        if index == 0:
            scene = (
                "The cast files into the firepit pit area for the Lie Detector. "
                "Every Heartbreaker straps a sensor pad to two fingers and the "
                f"big screen lights up next to {partner_name}. You're in the hot "
                "seat — the host reads a question and you pick how you answer. "
                "Truth, soft spin, or outright lie. The needle decides what the "
                "villa believes."
            )
        else:
            scene = (
                f"Same hot seat, same sensor pad on your fingers, {partner_name} "
                "still watching the needle. Host moves on to the next question."
            )
        stem = f"{scene} {ev['prompt']}"
        rounds.append(MinigameRound(
            index=index,
            prompt_id=f"lie_d{state.day}_r{index}",
            target_id=partner_id,
            trait_key=None,
            tier=0,
            mechanical=False,
            stem=stem,
            choices=choices,
            reveals=[
                MinigameReveal(
                    kind="fact", subject_id="player",
                    payload={"severity": str(ev["severity"]), "visibility": int(ev["visibility"])},
                ),
            ],
        ))
    return rounds


def submit_choice(challenge: Challenge, choice_id: str) -> Challenge:
    if challenge.classification is not None:
        raise ValueError("lie_detector already resolved")
    cur = challenge.rounds[challenge.current_round_index]
    if not any(c.id == choice_id for c in cur.choices):
        raise ValueError(f"unknown choice_id {choice_id}")
    new_round = cur.model_copy(update={"chosen_id": choice_id})
    new_rounds = list(challenge.rounds)
    new_rounds[challenge.current_round_index] = new_round
    return challenge.model_copy(
        update={"rounds": new_rounds, "current_round_index": challenge.current_round_index + 1}
    )


def has_more_rounds(challenge: Challenge) -> bool:
    return challenge.current_round_index < len(challenge.rounds)


def _detection_chance(state: GameState, partner_id: str, visibility: int) -> int:
    bal = load_minigame_balance().lie_detector.detection
    partner = find_islander(state, partner_id)
    fam = partner.familiarity_with_player
    fam_factor = min(bal.familiarity_factor_max, fam * bal.familiarity_factor_max // 100)
    vis_factor = min(bal.visibility_factor_max, visibility * bal.visibility_factor_max // 100)
    if fam < 30 and visibility < 30:
        return bal.floor  # no-knowledge case
    return max(bal.floor, min(bal.ceiling, bal.base_chance + fam_factor + vis_factor))


def score_lie_detector(state: GameState, challenge: Challenge) -> Challenge:
    bal = load_minigame_balance().lie_detector
    p = bal.per_round_points
    partner_id = _partner_id(state) or "chloe"
    total = 0
    new_rounds: list[MinigameRound] = []
    unverified_bonus = 0
    for r in challenge.rounds:
        chosen = next((c for c in r.choices if c.id == r.chosen_id), None)
        if chosen is None:
            new_rounds.append(r); continue
        # Extract event visibility from reveals
        visibility = 30
        severity = "low"
        for rv in r.reveals:
            if rv.kind == "fact" and "visibility" in rv.payload:
                visibility = int(rv.payload["visibility"])
                severity = str(rv.payload.get("severity", "low"))
                break
        chance = _detection_chance(state, partner_id, visibility)
        roll_rng = SeededRng(state.seed).fork(f"lie_detector::r{state.day}::{r.index}")
        roll = roll_rng.randint(1, 100)
        detected = roll <= chance

        if chosen.is_correct:
            # Truth path
            if detected:
                pts = p.truth_verified
                belief = "believed"
            else:
                pts = p.truth_unverified
                belief = "suspected"
                unverified_bonus = min(3, unverified_bonus + bal.audience.truth_unverified_bonus)
            new_reveals = [
                MinigameReveal(
                    kind="truth_told", subject_id=partner_id,
                    payload={"belief": belief, "chance": chance, "roll": roll, "detected": int(detected)},
                ),
            ]
        else:
            # Lie path
            if detected:
                pts = p.lie_caught
                belief = "caught"
                if severity == "high":
                    pts += p.lie_caught_high_stakes_extra
                new_reveals = [
                    MinigameReveal(
                        kind="lie_caught", subject_id=partner_id,
                        payload={"belief": belief, "chance": chance, "roll": roll, "severity": severity},
                    ),
                ]
            else:
                pts = p.lie_undetected
                belief = "believed"
                new_reveals = [
                    MinigameReveal(
                        kind="lie_caught", subject_id=partner_id,
                        payload={"belief": belief, "chance": chance, "roll": roll, "severity": severity, "caught": 0},
                    ),
                ]
        total += pts
        new_rounds.append(r.model_copy(update={"points": pts, "reveals": [*r.reveals, *new_reveals]}))

    if total >= bal.thresholds.success:
        classification = "success"
    elif total >= bal.thresholds.partial:
        classification = "partial"
    else:
        classification = "failure"
    audience = getattr(bal.audience, classification) + unverified_bonus
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


def apply_lie_detector_result(state: GameState, challenge: Challenge) -> Challenge:
    partner_id = _partner_id(state) or "chloe"
    partner = find_islander(state, partner_id)
    cls = challenge.classification or "failure"
    if cls == "success":
        delta = RelationshipDelta(trust=5, affection=1)
    elif cls == "partial":
        delta = RelationshipDelta(trust=1)
    else:
        delta = RelationshipDelta(trust=-8, affection=-3)
    apply_relationship_delta(partner, delta)
    state.player.public_perception = max(
        0, min(100, state.player.public_perception + challenge.audience_delta)
    )
    return challenge.model_copy(update={"participants": ["player", partner_id], "deltas": {partner_id: delta}})
