"""Audience scoring and rankings."""

from __future__ import annotations

from src.game.state.models import AudienceEntry, AudienceSnapshot, Couple, GameState


def player_couple(state: GameState) -> Couple | None:
    """Return the player's current couple, if any."""
    for couple in state.couples:
        if state.player.id in {couple.partner_a_id, couple.partner_b_id}:
            return couple
    return None


def audience_snapshot(state: GameState) -> AudienceSnapshot:
    """Compute a ranked audience snapshot for current couples."""
    rows: list[tuple[list[str], int, bool]] = []
    for couple in state.couples:
        if any(_is_eliminated(state, partner_id) for partner_id in (couple.partner_a_id, couple.partner_b_id)):
            continue
        partners = [couple.partner_a_id, couple.partner_b_id]
        score = _couple_audience_score(state, couple)
        rows.append((partners, score, state.player.id in partners))
    rows.sort(key=lambda row: (-row[1], row[0]))
    return AudienceSnapshot(
        day=state.day,
        entries=[
            AudienceEntry(rank=index, couple=partners, score=score, is_player_couple=is_player)
            for index, (partners, score, is_player) in enumerate(rows, start=1)
        ],
    )


def record_audience_snapshot(state: GameState) -> AudienceSnapshot:
    """Append and return the current audience snapshot."""
    snapshot = audience_snapshot(state)
    state.audience_snapshots.append(snapshot)
    return snapshot


def couple_audience_score(state: GameState, couple: Couple) -> int:
    """Public helper for final-vote ranking."""
    return _couple_audience_score(state, couple)


def _couple_audience_score(state: GameState, couple: Couple) -> int:
    scores = [_public_perception_for(state, partner_id) for partner_id in (couple.partner_a_id, couple.partner_b_id)]
    base = sum(scores) // len(scores)
    return max(0, min(100, base + _couple_strength_bonus(state, couple)))


def _public_perception_for(state: GameState, actor_id: str) -> int:
    if actor_id == state.player.id:
        return state.player.public_perception
    for islander in state.islanders:
        if islander.id == actor_id:
            return islander.public_perception
    return 0


def _is_eliminated(state: GameState, actor_id: str) -> bool:
    if actor_id == state.player.id:
        return state.player.eliminated
    for islander in state.islanders:
        if islander.id == actor_id:
            return islander.eliminated
    return True


def _couple_strength_bonus(state: GameState, couple: Couple) -> int:
    if state.player.id not in {couple.partner_a_id, couple.partner_b_id}:
        return 0
    partner_id = couple.partner_b_id if couple.partner_a_id == state.player.id else couple.partner_a_id
    for islander in state.islanders:
        if islander.id == partner_id:
            rel = islander.relationship
            return (rel.affection + rel.trust) // 20
    return 0
