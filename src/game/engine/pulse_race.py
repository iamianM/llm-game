"""Pulse Race (heart_rate) minigame implementation.

Reveal-only minigame: builds an N x N chemistry matrix, exposes hidden
chemistry scores via ``chemistry_rank`` reveals, then offers one reaction
round where the player chooses how to respond to the surprise target.

See ``docs/minigames/heart-rate.md`` and ``docs/minigame-system.md``.
"""

from __future__ import annotations

from src.game.content.minigame_balance import load_minigame_balance
from src.game.engine.audience import player_couple
from src.game.engine.challenges import apply_recovery_floor
from src.game.engine.state_access import apply_relationship_delta, find_heartbreaker
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
    target = find_heartbreaker(state, npc_id)
    return target.relationship.chemistry


def _matrix_entries(state: GameState) -> list[tuple[str, str, int, int]]:
    """Build ordered (performer, observer, bpm, chemistry) tuples.

    Includes player <-> heartbreaker pairs in both directions and heartbreaker <->
    heartbreaker pairs (deterministic ordering by id). For the player side the
    chemistry value comes from the heartbreaker relationship store (the same
    value used elsewhere in the engine).
    """
    entries: list[tuple[str, str, int, int]] = []
    heartbreakers = sorted([i for i in state.heartbreakers if not i.eliminated], key=lambda i: i.id)
    for heartbreaker in heartbreakers:
        chem = heartbreaker.relationship.chemistry
        bpm = 60 + int(chem * 0.4)
        # player -> heartbreaker
        entries.append(("player", heartbreaker.id, bpm, chem))
        # heartbreaker -> player
        entries.append((heartbreaker.id, "player", bpm, chem))
    # NPC pairs: no symmetric chemistry store today (it's player-anchored),
    # so derive an estimate from familiarity + couple status for visual matrix.
    for a in heartbreakers:
        for b in heartbreakers:
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
    for heartbreaker in sorted(state.heartbreakers, key=lambda i: i.id):
        if heartbreaker.eliminated or heartbreaker.id == partner:
            continue
        if heartbreaker.relationship.chemistry > best_chem:
            best_chem = heartbreaker.relationship.chemistry
            best_id = heartbreaker.id
    return best_id, best_chem


def _partner_surprise(state: GameState) -> tuple[str | None, int]:
    """Partner-side surprise: highest chemistry the partner shows to a non-player.
    Approximated from familiarity since NPC<->NPC chemistry isn't stored.
    Returns the partner's "echo" partner id if any meaningful crush exists.
    """
    partner = _partner_id(state)
    if partner is None:
        return None, 0
    # Rough proxy: pick the non-player heartbreaker whose familiarity with the
    # partner is highest (deterministic).
    candidates = [
        i for i in state.heartbreakers
        if not i.eliminated and i.id != "player" and i.id != partner
    ]
    if not candidates:
        return None, 0
    candidates.sort(key=lambda i: (-i.familiarity_with_player, i.id))
    pick = candidates[0]
    # Score the proxy as a fraction of partner familiarity with player.
    partner_heartbreaker = find_heartbreaker(state, partner)
    proxy = min(100, pick.familiarity_with_player + partner_heartbreaker.familiarity_with_player // 4)
    return pick.id, proxy


def build_rounds(state: GameState, partner_id: str, rng: SeededRng) -> list[MinigameRound]:
    """Build a 3-round 'read the room' Pulse Race.

    Pulse Race is the show's chemistry-reveal moment: every heartbreaker wears a
    monitor and reactions are projected publicly. We turn that into a
    playable beat — the player tries to *guess* who pinged hardest at whom.
    The "answer" for every round is the engine's actual highest-chemistry
    pairing for that performer; three plausible non-answers fill the rest
    of the menu. Right guesses surface KnownFacts and tilt audience favour;
    wrong guesses surface the same matrix but read as a misread.

    Round 1: who climbed highest when YOU did your bit.
    Round 2: who climbed highest when your PARTNER did theirs.
    Round 3: who YOU spiked for the most (excluding partner). Can include
             your partner as a decoy so a loyal pick "wholesomely wrong"
             still reads.
    """
    matrix = _matrix_entries(state)
    reveals = _matrix_reveals(matrix)
    cast_ids = [
        heartbreaker.id
        for heartbreaker in sorted(state.heartbreakers, key=lambda i: i.id)
        if not heartbreaker.eliminated and heartbreaker.id != "player"
    ]
    rounds: list[MinigameRound] = []
    partner_name = (
        find_heartbreaker(state, partner_id).name
        if partner_id and partner_id != "player" and any(i.id == partner_id for i in state.heartbreakers)
        else None
    )

    # Round 1 — observers ranked by chemistry toward the player. Stems are
    # self-contained: the player landed on the quiz screen without any
    # producer-intro narration so each question needs to set its own scene.
    rounds.append(_build_guess_round(
        state,
        index=0,
        rng=rng.fork("pulse_race::round_0"),
        prompt_id=f"pulse_race_who_spiked_for_player_{state.day}",
        stem=(
            "The Pulse Race is on. The cast files into the back garden in matching "
            "heart-rate monitors and one by one they take turns doing a quick "
            "flirty bit for each other — eye contact, a slow smile, a lean. "
            "You're first. The monitors light up and the room watches the spikes. "
            "Whose pulse climbed the highest while you were performing?"
        ),
        ranked=_observers_for_player(state, cast_ids),
        decoys=cast_ids,
    ))

    # Round 2 — observers ranked by chemistry toward the partner.
    if partner_name is not None and partner_id is not None:
        ranked_partner = _observers_for_npc(state, partner_id, cast_ids)
        rounds.append(_build_guess_round(
            state,
            index=1,
            rng=rng.fork("pulse_race::round_1"),
            prompt_id=f"pulse_race_who_spiked_for_partner_{state.day}",
            stem=(
                f"{partner_name} steps up next. They work the room with a soft "
                f"flirty bit — same monitors on everyone, same camera tracking "
                f"the screens. Reading the room: whose monitor climbed the "
                f"highest watching {partner_name}?"
            ),
            ranked=ranked_partner,
            decoys=[c for c in cast_ids if c != partner_id],
        ))

    # Round 3 — who the player's own pulse spiked for the most. Excludes
    # nobody — the partner is a valid pick (the "stayed loyal" answer).
    rounds.append(_build_guess_round(
        state,
        index=len(rounds),
        rng=rng.fork("pulse_race::round_2"),
        prompt_id=f"pulse_race_player_spiked_for_{state.day}",
        stem=(
            "Now everyone watches your monitor instead. Each Heartbreaker takes a "
            "turn doing a flirty bit at you while you sit there with the strap on. "
            "Your readings get projected. Out of the cast — whose bit made your "
            "own pulse jump the most? Be honest, the screens already showed it."
        ),
        ranked=_player_chemistry_ranked(state, cast_ids),
        decoys=cast_ids,
    ))

    # Stamp the reveal matrix onto the last round so the wrap UI surfaces
    # the full chemistry table after the player commits their guesses.
    if rounds:
        rounds[-1] = rounds[-1].model_copy(update={"reveals": [*rounds[-1].reveals, *reveals]})
    return rounds


def _matrix_reveals(matrix: list[tuple[str, str, int, int]]) -> list[MinigameReveal]:
    """Filter the chemistry matrix down to the entries strong enough to surface."""
    reveals: list[MinigameReveal] = []
    for performer, observer, bpm, chem in matrix:
        if chem < CHEMISTRY_KNOWN_THRESHOLD:
            continue
        reveals.append(
            MinigameReveal(
                kind="chemistry_rank",
                subject_id=performer,
                payload={"observer_id": observer, "bpm": bpm, "chemistry": chem},
            )
        )
    return reveals


def _observers_for_player(state: GameState, cast_ids: list[str]) -> list[tuple[str, int]]:
    """Return (heartbreaker_id, chemistry) sorted by who's most into the player."""
    ranked: list[tuple[str, int]] = []
    for heartbreaker_id in cast_ids:
        target = find_heartbreaker(state, heartbreaker_id)
        ranked.append((heartbreaker_id, target.relationship.chemistry))
    ranked.sort(key=lambda pair: (-pair[1], pair[0]))
    return ranked


def _observers_for_npc(state: GameState, npc_id: str, cast_ids: list[str]) -> list[tuple[str, int]]:
    """NPC-to-NPC chemistry isn't tracked directly; approximate from familiarity.

    Returns (heartbreaker_id, score) sorted highest score first. The Pulse Race
    spec accepts this estimate because Day 2 has no NPC-NPC chemistry
    interactions to draw from.
    """
    npc = find_heartbreaker(state, npc_id)
    ranked: list[tuple[str, int]] = []
    for heartbreaker_id in cast_ids:
        if heartbreaker_id == npc_id:
            continue
        other = find_heartbreaker(state, heartbreaker_id)
        score = (npc.familiarity_with_player + other.familiarity_with_player) // 4
        ranked.append((heartbreaker_id, score))
    ranked.sort(key=lambda pair: (-pair[1], pair[0]))
    return ranked


def _player_chemistry_ranked(state: GameState, cast_ids: list[str]) -> list[tuple[str, int]]:
    """Same as `_observers_for_player` for Day-2 since chemistry is symmetric."""
    return _observers_for_player(state, cast_ids)


def _build_guess_round(
    state: GameState,
    *,
    index: int,
    rng: SeededRng,
    prompt_id: str,
    stem: str,
    ranked: list[tuple[str, int]],
    decoys: list[str],
) -> MinigameRound:
    """Assemble one guess-the-spike round.

    ``ranked`` is sorted highest-chemistry first; entry 0 is the correct
    answer, entries 1-3 are the natural distractors. If there aren't enough
    ranked candidates, pad from ``decoys``.
    """
    if not ranked:
        # Edge case — no cast left. Build a single-choice round so the
        # minigame stays valid.
        return MinigameRound(
            index=index,
            prompt_id=prompt_id,
            target_id=None,
            trait_key=None,
            tier=0,
            mechanical=False,
            stem=stem,
            choices=[MinigameChoice(id="acknowledge", label="The cast is empty.", is_correct=True, distractor_source="generator")],
        )
    correct_id, correct_score = ranked[0]
    pool: list[str] = []
    for heartbreaker_id, _score in ranked[1:]:
        if heartbreaker_id not in pool and heartbreaker_id != correct_id:
            pool.append(heartbreaker_id)
        if len(pool) >= 3:
            break
    if len(pool) < 3:
        for heartbreaker_id in decoys:
            if heartbreaker_id == correct_id or heartbreaker_id in pool:
                continue
            pool.append(heartbreaker_id)
            if len(pool) >= 3:
                break
    pool = pool[:3]
    choices: list[MinigameChoice] = [
        MinigameChoice(
            id="correct",
            label=find_heartbreaker(state, correct_id).name,
            fact_value=correct_id,
            is_correct=True,
            distractor_source="trait_card",
        ),
    ]
    for d_index, distractor_id in enumerate(pool):
        choices.append(
            MinigameChoice(
                id=f"distractor_{d_index}",
                label=find_heartbreaker(state, distractor_id).name,
                fact_value=distractor_id,
                is_correct=False,
                distractor_source="trait_card",
            )
        )
    _shuffle_choices(choices, rng)
    return MinigameRound(
        index=index,
        prompt_id=prompt_id,
        target_id=correct_id,
        trait_key=None,
        tier=0,
        mechanical=False,
        stem=stem,
        choices=choices,
    )


def _shuffle_choices(items: list[MinigameChoice], rng: SeededRng) -> None:
    """Deterministic in-place Fisher-Yates."""
    n = len(items)
    for i in range(n - 1, 0, -1):
        j = rng.randint(0, i)
        items[i], items[j] = items[j], items[i]


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
    # Score by how many guesses the player got right.
    correct = 0
    for round_ in challenge.rounds:
        chosen = next((c for c in round_.choices if c.id == round_.chosen_id), None)
        if chosen is not None and chosen.is_correct:
            correct += 1
    total_rounds = len(challenge.rounds) or 1
    if correct >= total_rounds:
        classification = "success"
    elif correct >= max(1, total_rounds // 2):
        classification = "partial"
    else:
        classification = "failure"

    audience = getattr(bal.audience, classification)
    audience = apply_recovery_floor(state, audience, classification)

    return challenge.model_copy(
        update={
            "total_points": correct,
            "classification": classification,
            "audience_delta": audience,
            "result": "failure" if classification == "failure" else "success",
        }
    )


def _guess_reaction_deltas(state: GameState, challenge: Challenge) -> dict[str, RelationshipDelta]:
    """Apply small relationship deltas tied to each round's guess.

    Right guesses about the player's own pulse (round 3) reward the picked
    heartbreaker with chemistry +1 — the player publicly clocked the spike.
    Right guesses about the partner (round 2) earn the partner trust +1.
    Right guesses about who's into the player (round 1) earn audience
    favour through the classification path; no per-NPC delta. Wrong
    guesses produce no delta.
    """
    deltas: dict[str, RelationshipDelta] = {}
    partner = _partner_id(state)
    for round_ in challenge.rounds:
        chosen = next((c for c in round_.choices if c.id == round_.chosen_id), None)
        if chosen is None or not chosen.is_correct:
            continue
        prompt = round_.prompt_id
        if "player_spiked_for" in prompt:
            target_id = chosen.fact_value or ""
            if target_id and target_id != "player":
                target = find_heartbreaker(state, target_id)
                delta = RelationshipDelta(chemistry=1)
                apply_relationship_delta(target, delta)
                deltas[target_id] = delta
        elif "who_spiked_for_partner" in prompt and partner:
            target = find_heartbreaker(state, partner)
            delta = RelationshipDelta(trust=1)
            apply_relationship_delta(target, delta)
            deltas[partner] = delta
    return deltas


def apply_pulse_race_result(state: GameState, challenge: Challenge) -> Challenge:
    deltas = _guess_reaction_deltas(state, challenge)
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
    # The minigame's "participants" surface to narrator + report packets;
    # name the player plus the partner so wrap prose centers on the couple.
    partner = _partner_id(state)
    return challenge.model_copy(
        update={"participants": ["player", partner or ""], "deltas": deltas}
    )
