"""Pulse Race (heart_rate) minigame implementation.

Reveal-only minigame: builds an N x N chemistry matrix, exposes hidden
chemistry scores via ``chemistry_rank`` reveals, then offers one reaction
round where the player chooses how to respond to the surprise target.

See ``docs/minigames/heart-rate.md`` and ``docs/minigame-system.md``.
"""

from __future__ import annotations

from src.game.content.minigame_balance import load_minigame_balance
from src.game.engine.challenges import apply_recovery_floor
from src.game.engine.audience import player_couple
from src.game.engine.state_access import apply_relationship_delta, find_islander
from src.game.state.event_models import (
    Challenge,
    MinigameChoice,
    MinigameReveal,
    MinigameRound,
)
from src.game.state.models import GameState, RelationshipDelta
from src.game.state.rng import SeededRng


CHEMISTRY_KNOWN_THRESHOLD = 50  # write KnownFact when chemistry >= this


def _partner_id(state: GameState) -> str | None:
    couple = player_couple(state)
    if couple is None:
        return None
    return couple.partner_b_id if couple.partner_a_id == "player" else couple.partner_a_id


def _player_chemistry_with(state: GameState, npc_id: str) -> int:
    target = find_islander(state, npc_id)
    return target.relationship.chemistry


def _matrix_entries(state: GameState) -> list[tuple[str, str, int, int]]:
    """Build ordered (performer, observer, bpm, chemistry) tuples.

    Includes player <-> islander pairs in both directions and islander <->
    islander pairs (deterministic ordering by id). For the player side the
    chemistry value comes from the islander relationship store (the same
    value used elsewhere in the engine).
    """
    entries: list[tuple[str, str, int, int]] = []
    islanders = sorted([i for i in state.islanders if not i.eliminated], key=lambda i: i.id)
    for islander in islanders:
        chem = islander.relationship.chemistry
        bpm = 60 + int(chem * 0.4)
        # player -> islander
        entries.append(("player", islander.id, bpm, chem))
        # islander -> player
        entries.append((islander.id, "player", bpm, chem))
    # NPC pairs: no symmetric chemistry store today (it's player-anchored),
    # so derive an estimate from familiarity + couple status for visual matrix.
    for a in islanders:
        for b in islanders:
            if a.id >= b.id:
                continue
            estimate = (a.familiarity_with_player + b.familiarity_with_player) // 4
            entries.append((a.id, b.id, 60 + int(estimate * 0.4), estimate))
    return entries


def _surprise_target_id(state: GameState) -> tuple[str | None, int]:
    """Return (surprise_target_id, chemistry) — highest non-partner chemistry."""
    partner = _partner_id(state)
    best_id: str | None = None
    best_chem = -1
    for islander in sorted(state.islanders, key=lambda i: i.id):
        if islander.eliminated or islander.id == partner:
            continue
        if islander.relationship.chemistry > best_chem:
            best_chem = islander.relationship.chemistry
            best_id = islander.id
    return best_id, best_chem


def _partner_surprise(state: GameState) -> tuple[str | None, int]:
    """Partner-side surprise: highest chemistry the partner shows to a non-player.
    Approximated from familiarity since NPC<->NPC chemistry isn't stored.
    Returns the partner's "echo" partner id if any meaningful crush exists.
    """
    partner = _partner_id(state)
    if partner is None:
        return None, 0
    # Rough proxy: pick the non-player islander whose familiarity with the
    # partner is highest (deterministic).
    candidates = [
        i for i in state.islanders
        if not i.eliminated and i.id != "player" and i.id != partner
    ]
    if not candidates:
        return None, 0
    candidates.sort(key=lambda i: (-i.familiarity_with_player, i.id))
    pick = candidates[0]
    # Score the proxy as a fraction of partner familiarity with player.
    partner_islander = find_islander(state, partner)
    proxy = min(100, pick.familiarity_with_player + partner_islander.familiarity_with_player // 4)
    return pick.id, proxy


def build_rounds(state: GameState, partner_id: str, rng: SeededRng) -> list[MinigameRound]:
    """Build the reveal matrix and the optional reaction round.

    Returns either one round (the reaction) or zero rounds (flat week,
    classification will be ``failure`` with no player input required).
    """
    bal = load_minigame_balance().heart_rate
    surprise_target, surprise_chem = _surprise_target_id(state)
    matrix = _matrix_entries(state)

    # Build matrix reveals (chemistry_rank) on the synthetic announce round
    # if there's no surprise high enough; otherwise attach them to the
    # reaction round so the browser/CLI render them before the choices.
    reveals: list[MinigameReveal] = []
    for performer, observer, bpm, chem in matrix:
        if chem < CHEMISTRY_KNOWN_THRESHOLD:
            continue
        reveals.append(
            MinigameReveal(
                kind="chemistry_rank",
                subject_id=performer,
                payload={
                    "observer_id": observer,
                    "bpm": bpm,
                    "chemistry": chem,
                },
            )
        )

    if surprise_target is None or surprise_chem < bal.thresholds.surprise_chemistry:
        # Flat week — the matrix didn't surface anyone hot enough to be a
        # surprise. The minigame still fires (the cast is rigged up), so give
        # the player something meaningful to do with the calm: own it, stir
        # it, or steady their partner. These all resolve into a "failure"
        # classification at the engine level (no real spike) but the player
        # pick shapes audience and the partner relationship.
        partner_name = find_islander(state, partner_id).name if partner_id else "your partner"
        return [
            MinigameRound(
                index=0,
                prompt_id=f"pulse_race_flat_{state.day}",
                target_id=partner_id,
                trait_key=None,
                tier=0,
                mechanical=False,
                stem=(
                    "The Pulse Race plays out and nobody's reading hits a real spike. "
                    f"The producers cut to {partner_name} watching you. How do you sell it?"
                ),
                choices=[
                    MinigameChoice(
                        id="lean_in",
                        label=f"Pull {partner_name} closer and own the calm.",
                        fact_value="lean_in",
                        is_correct=True,
                        distractor_source="generator",
                    ),
                    MinigameChoice(
                        id="play_cool",
                        label="Crack a joke about no one fancying you.",
                        fact_value="play_cool",
                        is_correct=True,
                        distractor_source="generator",
                    ),
                    MinigameChoice(
                        id="apologize",
                        label=f"Reassure {partner_name} that this means it's solid.",
                        fact_value="apologize",
                        is_correct=True,
                        distractor_source="generator",
                    ),
                ],
                reveals=reveals,
            )
        ]

    surprise_name = find_islander(state, surprise_target).name
    choices = [
        MinigameChoice(
            id="lean_in",
            label=f"Lean into it with {surprise_name}.",
            fact_value="lean_in",
            is_correct=True,
            distractor_source="generator",
        ),
        MinigameChoice(
            id="play_cool",
            label="Play it cool — laugh it off.",
            fact_value="play_cool",
            is_correct=True,
            distractor_source="generator",
        ),
        MinigameChoice(
            id="apologize",
            label=f"Apologise to your partner.",
            fact_value="apologize",
            is_correct=True,
            distractor_source="generator",
        ),
    ]
    return [
        MinigameRound(
            index=0,
            prompt_id=f"pulse_race_react_{state.day}",
            target_id=surprise_target,
            trait_key=None,
            tier=0,
            mechanical=False,
            stem=(
                f"Pulse spike. The room sees you and {surprise_name} pinned at "
                f"{60 + int(surprise_chem * 0.4)} BPM. The cameras cut to your partner. "
                "What do you do?"
            ),
            choices=choices,
            reveals=reveals,
        )
    ]


def submit_choice(challenge: Challenge, choice_id: str) -> Challenge:
    if challenge.classification is not None:
        raise ValueError("pulse_race already resolved")
    if challenge.current_round_index >= len(challenge.rounds):
        raise ValueError("no more rounds")
    round_ = challenge.rounds[challenge.current_round_index]
    if not any(c.id == choice_id for c in round_.choices):
        raise ValueError(f"unknown choice_id {choice_id}")
    new_round = round_.model_copy(update={"chosen_id": choice_id, "points": 0})
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


def score_pulse_race(state: GameState, challenge: Challenge) -> Challenge:
    bal = load_minigame_balance().heart_rate
    surprise_target, surprise_chem = _surprise_target_id(state)
    partner_surprise_id, partner_surprise_chem = _partner_surprise(state)
    if surprise_target is not None and surprise_chem >= bal.thresholds.surprise_chemistry:
        classification = "success"
    elif partner_surprise_id is not None and partner_surprise_chem >= bal.thresholds.surprise_chemistry:
        classification = "partial"
    else:
        classification = "failure"

    audience = getattr(bal.audience, classification)
    # Player-pick bonus/penalty
    if challenge.rounds:
        last = challenge.rounds[-1]
        if last.chosen_id == "lean_in":
            audience += bal.audience.lean_in_bonus
        elif last.chosen_id == "apologize":
            audience += bal.audience.apologize_penalty
    audience = apply_recovery_floor(state, audience, classification)

    # Surface a coherent score: peak BPM observed in the matrix (deterministic,
    # always >=60). Avoids the "success but 0 pts" confusion the narrator
    # flagged in the live eval.
    peak_bpm = 60
    for round_ in challenge.rounds:
        for reveal in round_.reveals:
            if reveal.kind == "chemistry_rank":
                bpm = int(reveal.payload.get("bpm", 0))
                if bpm > peak_bpm:
                    peak_bpm = bpm

    return challenge.model_copy(
        update={
            "total_points": peak_bpm,
            "classification": classification,
            "audience_delta": audience,
            "result": "failure" if classification == "failure" else "success",
        }
    )


def _apply_reaction_delta(state: GameState, choice_id: str | None, surprise_target: str | None) -> dict[str, RelationshipDelta]:
    deltas: dict[str, RelationshipDelta] = {}
    if choice_id == "lean_in" and surprise_target is not None:
        target = find_islander(state, surprise_target)
        delta = RelationshipDelta(chemistry=3)
        apply_relationship_delta(target, delta)
        deltas[surprise_target] = delta
    elif choice_id == "apologize":
        partner = _partner_id(state)
        if partner is not None:
            target = find_islander(state, partner)
            delta = RelationshipDelta(trust=2)
            apply_relationship_delta(target, delta)
            deltas[partner] = delta
            if surprise_target is not None:
                surprise = find_islander(state, surprise_target)
                surprise_delta = RelationshipDelta(chemistry=-1)
                apply_relationship_delta(surprise, surprise_delta)
                deltas[surprise_target] = surprise_delta
    return deltas


def apply_pulse_race_result(state: GameState, challenge: Challenge) -> Challenge:
    surprise_target, _ = _surprise_target_id(state)
    chosen = (challenge.rounds[-1].chosen_id if challenge.rounds else None)
    deltas = _apply_reaction_delta(state, chosen, surprise_target)
    state.player.public_perception = max(
        0, min(100, state.player.public_perception + challenge.audience_delta)
    )
    # Write chemistry_observation KnownFacts for every exposed pair >=50
    from src.game.state.traits import KnownFact
    for round_ in challenge.rounds:
        for reveal in round_.reveals:
            if reveal.kind != "chemistry_rank":
                continue
            chem = int(reveal.payload.get("chemistry", 0))
            if chem < CHEMISTRY_KNOWN_THRESHOLD:
                continue
            performer = reveal.subject_id
            observer = str(reveal.payload.get("observer_id", ""))
            if "player" not in (performer, observer):
                continue  # player only learns about pairs involving themself
            other = observer if performer == "player" else performer
            fact_key = f"{other}.chemistry_with_player"
            state.player.known_facts[fact_key] = KnownFact(
                fact_key=fact_key,
                value=str(chem),
                source="witnessed",
                source_npc_id=other,
                learned_on_day=state.day,
                learned_on_turn=state.turn_index,
                confidence=1.0,
                citation=f"pulse_race day {state.day}",
            )
    return challenge.model_copy(update={"participants": ["player", surprise_target or _partner_id(state) or ""], "deltas": deltas})
