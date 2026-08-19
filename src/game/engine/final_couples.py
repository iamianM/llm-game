"""Final Couples Challenge.

Five weighted-sum rounds (knowledge, chemistry, honesty, banter, audacity)
that aggregate the season's earlier minigames. The classification feeds the
final-vote weighting downstream. See ``docs/systems/minigames/final-couples.md``.
"""

from __future__ import annotations

from src.game.content.minigame_balance import load_minigame_balance
from src.game.engine.audience import player_couple
from src.game.engine.challenges import apply_recovery_floor
from src.game.engine.state_access import apply_relationship_delta, find_heartbreaker
from src.game.state.event_models import Challenge, MinigameChoice, MinigameReveal, MinigameRound
from src.game.state.models import GameState, RelationshipDelta
from src.game.state.rng import SeededRng

FACETS = ["knowledge", "chemistry", "honesty", "banter", "audacity"]


def _partner_id(state: GameState) -> str | None:
    couple = player_couple(state)
    if couple is None:
        return None
    return couple.partner_b_id if couple.partner_a_id == "player" else couple.partner_a_id


def build_rounds(state: GameState, partner_id: str, rng: SeededRng) -> list[MinigameRound]:
    assert state.question_bank is not None
    rounds: list[MinigameRound] = []
    partner = find_heartbreaker(state, partner_id)

    # Round 0 — Knowledge: one Compatibility-Quiz-style question on partner
    bank_pool = [p for p in state.question_bank.prompts.get("compatibility_quiz", []) if p.target_id == partner_id]
    bank_pool.sort(key=lambda p: p.id)
    used = set(state.quizzed_traits_this_run.get(partner_id, []))
    knowledge_prompt = next((p for p in bank_pool if p.trait_key not in used), bank_pool[0] if bank_pool else None)
    if knowledge_prompt is not None:
        choices = [MinigameChoice(id="correct", label=knowledge_prompt.correct_value, fact_value=knowledge_prompt.correct_value, is_correct=True, distractor_source="trait_card")]
        for d_index, val in enumerate(knowledge_prompt.distractors[:3]):
            choices.append(MinigameChoice(id=f"distractor_{d_index}", label=val, fact_value=val, is_correct=False, distractor_source="trait_card"))
        rounds.append(MinigameRound(
            index=0, prompt_id=knowledge_prompt.id, target_id=partner_id,
            trait_key=knowledge_prompt.trait_key, tier=knowledge_prompt.tier, mechanical=knowledge_prompt.mechanical,
            stem=(
                "The Final Couples Challenge starts at the flame_deck. The host walks "
                "the surviving couples through five facets: knowledge, chemistry, "
                "honesty, banter, audacity. Round one is Knowledge. The host "
                f"reads a fact about {partner.name} and you pick the right answer "
                "from the choices. This is everything you should have learned this "
                f"season. {knowledge_prompt.stem}"
            ),
            choices=choices,
        ))
    chem = partner.relationship.chemistry
    rounds.append(MinigameRound(
        index=1, prompt_id="final_chemistry", target_id=partner_id, trait_key=None, tier=0, mechanical=False,
        stem=(
            "Round two of five is Chemistry. The host asks you to point to the "
            f"single moment that defined you and {partner.name} as a couple: "
            "no committee, no take-back. The room watches you decide."
        ),
        choices=[
            MinigameChoice(id="chemistry_kiss", label="The kiss after the Pairing Ceremony.", fact_value="kiss", is_correct=True, distractor_source="generator"),
            MinigameChoice(id="chemistry_quiet", label="A quiet morning, just talking.", fact_value="quiet", is_correct=True, distractor_source="generator"),
        ],
        reveals=[MinigameReveal(kind="fact", subject_id=partner_id, payload={"chemistry": chem})],
    ))
    rounds.append(MinigameRound(
        index=2, prompt_id="final_honesty", target_id=partner_id, trait_key=None, tier=0, mechanical=False,
        stem=(
            "Round three is Honesty. Microphones are open and the audience is "
            f"voting at home. The host turns to you: have you been completely "
            f"honest with {partner.name} this whole season?"
        ),
        choices=[
            MinigameChoice(id="truth", label="Yes - tell the truth.", fact_value="truth", is_correct=True, distractor_source="trait_card"),
            MinigameChoice(id="lie_mild", label="Soften it - mostly.", fact_value="lie_mild", is_correct=False, distractor_source="lie"),
            MinigameChoice(id="lie_hard", label="Deny everything.", fact_value="lie_hard", is_correct=False, distractor_source="lie"),
        ],
    ))
    rounds.append(MinigameRound(
        index=3, prompt_id="final_banter", target_id=partner_id, trait_key=None, tier=0, mechanical=False,
        stem=(
            "Round four is Banter. The host plays back three soundbites the "
            f"Sunset Bay heard from {partner.name} this week and asks which one is "
            "the inside joke only the two of you actually get."
        ),
        choices=[
            MinigameChoice(id="callback_inside_joke", label="The one only you two get.", fact_value="match", is_correct=True, distractor_source="generator"),
            MinigameChoice(id="callback_crowd", label="The crowd-pleaser.", fact_value="miss", is_correct=False, distractor_source="generator"),
            MinigameChoice(id="callback_safe", label="The safe one.", fact_value="miss", is_correct=False, distractor_source="generator"),
        ],
    ))
    non_partners = sorted([i for i in state.heartbreakers if not i.eliminated and i.id != "player" and i.id != partner_id], key=lambda i: i.relationship.affection)
    rival = non_partners[0].id if non_partners else partner_id
    friend = non_partners[-1].id if len(non_partners) > 1 else partner_id
    rounds.append(MinigameRound(
        index=4, prompt_id="final_audacity", target_id=partner_id, trait_key=None, tier=0, mechanical=False,
        stem=(
            "Round five is Audacity. The producer hands you one Spotlight card "
            "for the season's sharpest final read. You have to call out one "
            "person in front of the room. Everyone knows who you've clashed "
            "with this season; the cameras are waiting."
        ),
        choices=[
            MinigameChoice(id=f"callout_{rival}", label=f"{find_heartbreaker(state, rival).name}", fact_value=f"rival:{rival}", is_correct=True, distractor_source="generator"),
            MinigameChoice(id=f"callout_{friend}", label=f"{find_heartbreaker(state, friend).name}", fact_value=f"friend:{friend}", is_correct=False, distractor_source="generator"),
            MinigameChoice(id=f"callout_{partner_id}", label=f"{partner.name}", fact_value=f"partner:{partner_id}", is_correct=False, distractor_source="generator"),
        ],
    ))
    return rounds


def submit_choice(challenge: Challenge, choice_id: str) -> Challenge:
    if challenge.classification is not None:
        raise ValueError("final_couples already resolved")
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


def _attach_facet_reveals(challenge: Challenge) -> Challenge:
    """Annotate each round with an explicit facet reveal for narration."""
    new_rounds = list(challenge.rounds)
    for i, r in enumerate(new_rounds):
        facet = FACETS[r.index] if r.index < len(FACETS) else "knowledge"
        # Skip if a facet reveal already present
        if any(rv.kind == "fact" and rv.payload.get("facet") == facet for rv in r.reveals):
            continue
        reveal = MinigameReveal(
            kind="fact",
            subject_id=r.target_id or "",
            payload={"facet": facet, "round_index": r.index},
        )
        new_rounds[i] = r.model_copy(update={"reveals": [*r.reveals, reveal]})
    return challenge.model_copy(update={"rounds": new_rounds})


def score_final_couples(state: GameState, challenge: Challenge) -> Challenge:
    challenge = _attach_facet_reveals(challenge)
    bal = load_minigame_balance().final_couples
    weights = bal.facet_weights
    p = bal.per_round_points
    partner_id = _partner_id(state) or "chloe"
    partner = find_heartbreaker(state, partner_id)

    total = 0
    new_rounds: list[MinigameRound] = []
    for r in challenge.rounds:
        chosen = next((c for c in r.choices if c.id == r.chosen_id), None)
        facet = FACETS[r.index] if r.index < len(FACETS) else "knowledge"
        weight = getattr(weights, facet)
        if chosen is None:
            new_rounds.append(r.model_copy(update={"points": 0}))
            continue
        if facet == "knowledge":
            pts = p.knowledge_correct if chosen.is_correct else p.knowledge_incorrect
        elif facet == "chemistry":
            chem = partner.relationship.chemistry
            pts = p.chemistry_high if chem >= 60 else p.chemistry_low
        elif facet == "honesty":
            if chosen.id == "truth":
                pts = p.honesty_truth
            else:
                # Detect with simple 50-50 against partner familiarity
                roll = SeededRng(state.seed).fork(f"final_couples::r{r.index}").randint(1, 100)
                detected = roll <= max(20, partner.familiarity_with_player)
                pts = p.honesty_lie_caught if detected else p.honesty_lie_undetected
        elif facet == "banter":
            pts = p.banter_match if chosen.fact_value == "match" else p.banter_miss
        elif facet == "audacity":
            tag = (chosen.fact_value or "").split(":")[0]
            if tag == "rival":
                pts = p.audacity_rival_callout
            elif tag == "friend":
                pts = p.audacity_friend_callout
            elif tag == "partner":
                pts = p.audacity_partner_callout
            else:
                pts = 0
        else:
            pts = 0
        weighted = pts * weight
        total += weighted
        new_rounds.append(r.model_copy(update={"points": weighted}))

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


def apply_final_couples_result(state: GameState, challenge: Challenge) -> Challenge:
    partner_id = _partner_id(state) or "chloe"
    partner = find_heartbreaker(state, partner_id)
    cls = challenge.classification or "failure"
    if cls == "success":
        delta = RelationshipDelta(affection=8, trust=4)
    elif cls == "partial":
        delta = RelationshipDelta(affection=3, trust=1)
    else:
        delta = RelationshipDelta(affection=-3, trust=-2)
    apply_relationship_delta(partner, delta)
    state.player.public_perception = max(
        0, min(100, state.player.public_perception + challenge.audience_delta)
    )
    return challenge.model_copy(update={"participants": ["player", partner_id], "deltas": {partner_id: delta}})
