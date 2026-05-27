"""Kiss Wed Pass (snog_marry_pie) minigame.

Three rounds — snog, marry, pie. Each round narrows the pool by one. Targets
are chosen from current relationship state: partner, top-chemistry non-partner,
lowest-affection non-partner. Pie-partner is the season-defining self-destruct.

See ``docs/minigames/snog-marry-pie.md``.
"""

from __future__ import annotations

from src.game.content.minigame_balance import load_minigame_balance
from src.game.engine.challenges import apply_recovery_floor
from src.game.engine.audience import player_couple
from src.game.engine.state_access import apply_relationship_delta, find_islander
from src.game.state.event_models import Challenge, MinigameChoice, MinigameReveal, MinigameRound
from src.game.state.models import GameState, RelationshipDelta
from src.game.state.rng import SeededRng


LABELS = ["snog", "marry", "pie"]


def _partner_id(state: GameState) -> str | None:
    couple = player_couple(state)
    if couple is None:
        return None
    return couple.partner_b_id if couple.partner_a_id == "player" else couple.partner_a_id


def _available_targets(state: GameState) -> list[tuple[str, str]]:
    """Three candidate (target_id, role) tuples.

    Role is one of ``partner``, ``chemistry`` (top non-partner chemistry),
    ``friend`` (top non-partner friendship), ``rival`` (lowest non-partner
    affection). Deterministic by stable sort + id tiebreak.
    """
    partner = _partner_id(state)
    islanders = [i for i in state.islanders if not i.eliminated and i.id != "player"]
    if not islanders:
        return []
    targets: list[tuple[str, str]] = []
    if partner is not None:
        targets.append((partner, "partner"))
    non_partners = sorted([i for i in islanders if i.id != partner], key=lambda i: i.id)
    if non_partners:
        chem_pick = max(non_partners, key=lambda i: (i.relationship.chemistry, -ord(i.id[0])))
        targets.append((chem_pick.id, "chemistry"))
        remaining = [i for i in non_partners if i.id != chem_pick.id]
        if remaining:
            rival_pick = min(remaining, key=lambda i: (i.relationship.affection, i.id))
            targets.append((rival_pick.id, "rival"))
    return targets[:3]


def build_rounds(state: GameState, rng: SeededRng) -> list[MinigameRound]:
    targets = _available_targets(state)
    if len(targets) < 3:
        # Edge case: padded with deterministic next-best picks
        non_partners = sorted(
            [i for i in state.islanders if not i.eliminated and i.id != "player"], key=lambda i: i.id
        )
        seen_ids = {t[0] for t in targets}
        for npc in non_partners:
            if npc.id in seen_ids:
                continue
            targets.append((npc.id, "friend"))
            seen_ids.add(npc.id)
            if len(targets) >= 3:
                break

    rounds: list[MinigameRound] = []
    # We do NOT shrink the pool inside build_rounds because the engine builds
    # one MinigameRound per label; pool-shrinking happens at submit_choice
    # time by re-emitting available choices from the remaining pool.
    target_roles = {tid: role for tid, role in targets}
    label_stems: dict[str, str] = {
        "kiss": (
            "Kiss Wed Pass time. The cast is laid out shoulder-to-shoulder on the "
            "firepit benches. The producer hands you three name cards from the "
            "Heartbreaker pool — you have to use each card exactly once. The "
            "rest of the villa watches every pick. First card: **kiss**. Of "
            "these three, who do you walk over and kiss?"
        ),
        "wed": (
            "Two cards left. You already used your kiss. Same Heartbreakers in "
            "front of you, same audience. Second card: **wed**. Which of the "
            "remaining two are you committing to, real-relationship?"
        ),
        "pass": (
            "Last card. One Heartbreaker left from your three. The cast knows "
            "what's coming. The producer hands you the **pass** card — give it "
            "to the only person you haven't picked yet."
        ),
    }
    for index, label in enumerate(LABELS):
        choices = [
            MinigameChoice(
                id=f"target_{tid}",
                label=find_islander(state, tid).name,
                fact_value=tid,
                is_correct=True,  # all picks are 'legal' — scoring varies
                distractor_source="generator",
            )
            for tid, _ in targets
        ]
        rounds.append(
            MinigameRound(
                index=index,
                prompt_id=f"smp_{label}_{state.day}",
                target_id=None,
                trait_key=None,
                tier=0,
                mechanical=False,
                stem=label_stems.get(label, f"Round {index + 1} of 3: {label.capitalize()} one."),
                choices=choices,
            )
        )
    return rounds


def submit_choice(challenge: Challenge, choice_id: str) -> Challenge:
    if challenge.classification is not None:
        raise ValueError("snog_marry_pie already resolved")
    cur = challenge.rounds[challenge.current_round_index]
    if not any(c.id == choice_id for c in cur.choices):
        raise ValueError(f"unknown choice_id {choice_id}")
    # Shrink remaining rounds: drop the chosen target from later round choices.
    chosen_target = next(c.fact_value for c in cur.choices if c.id == choice_id)
    new_rounds = list(challenge.rounds)
    new_rounds[challenge.current_round_index] = cur.model_copy(update={"chosen_id": choice_id})
    for i in range(challenge.current_round_index + 1, len(new_rounds)):
        nr = new_rounds[i]
        remaining_choices = [c for c in nr.choices if c.fact_value != chosen_target]
        new_rounds[i] = nr.model_copy(update={"choices": remaining_choices})
    return challenge.model_copy(
        update={
            "rounds": new_rounds,
            "current_round_index": challenge.current_round_index + 1,
        }
    )


def has_more_rounds(challenge: Challenge) -> bool:
    return challenge.current_round_index < len(challenge.rounds)


def _role_for(state: GameState, target_id: str) -> str:
    partner = _partner_id(state)
    if target_id == partner:
        return "partner"
    targets = _available_targets(state)
    for tid, role in targets:
        if tid == target_id:
            return role
    # Default to friend if not in canonical targets
    return "friend"


def score_snog_marry_pie(state: GameState, challenge: Challenge) -> Challenge:
    bal = load_minigame_balance().snog_marry_pie
    p = bal.per_round_points
    total = 0
    new_rounds: list[MinigameRound] = []
    pie_partner = False
    pie_friend = False
    for r in challenge.rounds:
        label = LABELS[r.index]
        if r.chosen_id is None:
            new_rounds.append(r.model_copy(update={"points": 0}))
            continue
        target_id = next(c.fact_value for c in r.choices if c.id == r.chosen_id)
        role = _role_for(state, target_id)
        key = f"{label}_{role}"
        pts = getattr(p, key, 0)
        if label == "pie" and role == "partner":
            pie_partner = True
        if label == "pie" and role in {"friend"}:
            pie_friend = True
        total += pts
        new_rounds.append(r.model_copy(update={"points": pts}))
    if total >= bal.thresholds.success:
        classification = "success"
    elif total >= bal.thresholds.partial:
        classification = "partial"
    else:
        classification = "failure"
    audience = getattr(bal.audience, classification)
    if pie_partner:
        audience += bal.audience.pie_partner_extra
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


def apply_snog_marry_pie_result(state: GameState, challenge: Challenge) -> Challenge:
    deltas: dict[str, RelationshipDelta] = {}
    for r in challenge.rounds:
        if r.chosen_id is None:
            continue
        target_id = next(c.fact_value for c in r.choices if c.id == r.chosen_id)
        label = LABELS[r.index]
        role = _role_for(state, target_id)
        target = find_islander(state, target_id)
        if label == "snog":
            delta = RelationshipDelta(chemistry=3)
        elif label == "marry":
            delta = RelationshipDelta(affection=2, trust=2)
        else:  # pie
            if role == "partner":
                delta = RelationshipDelta(affection=-5, trust=-5)
            elif role == "rival":
                delta = RelationshipDelta(friendship=-2)
            else:
                delta = RelationshipDelta(friendship=-2)
        apply_relationship_delta(target, delta)
        deltas[target_id] = delta
        # Reveal
        reaction = MinigameReveal(
            kind="reaction",
            subject_id=target_id,
            payload={"label": label, "role": role},
        )
        idx = challenge.rounds.index(r)
        challenge.rounds[idx].reveals.append(reaction)
    state.player.public_perception = max(
        0, min(100, state.player.public_perception + challenge.audience_delta)
    )
    return challenge.model_copy(update={"deltas": deltas, "participants": ["player", _partner_id(state) or ""]})
