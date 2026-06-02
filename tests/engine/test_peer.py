"""Tests for deterministic NPC↔NPC peer attraction (the resort's own love stories).

Covers the pure compatibility function, co-location-driven growth toward the
compatibility ceiling, single-pair couple formation (and the refusal to pair
already-coupled heartbreakers), and the gossip/recap surfacing of both the
"getting close" whisper and the off-screen couple-up.
"""

from __future__ import annotations

from src.game.engine.daily_recap import humanize_player_reference
from src.game.engine.peer import (
    PEER_COUPLE_THRESHOLD,
    PEER_FRIENDLY_THRESHOLD,
    PEER_WANDERING_THRESHOLD,
    advance_peer_attractions,
    maybe_form_peer_couples,
    peer_affinity_between,
    peer_compatibility,
)
from src.game.state.models import Couple, new_game
from src.game.state.personality import AttachmentStyle
from src.game.state.rng import SeededRng


def _isolated_pair(seed: int = 1):
    """Return (state, chloe, liam) co-located and single, with everyone else
    eliminated so the only opposite-gender pair in play is chloe↔liam."""
    state = new_game(seed)
    chloe = next(i for i in state.heartbreakers if i.id == "chloe")
    liam = next(i for i in state.heartbreakers if i.id == "liam")
    liam.location_id = chloe.location_id
    for other in state.heartbreakers:
        if other.id not in {"chloe", "liam"}:
            other.eliminated = True
    return state, chloe, liam


# --- pure compatibility ---------------------------------------------------


def test_compatibility_is_symmetric() -> None:
    state = new_game(1)
    for a in state.heartbreakers:
        for b in state.heartbreakers:
            assert peer_compatibility(a, b) == peer_compatibility(b, a)


def test_compatibility_in_range() -> None:
    state = new_game(1)
    for a in state.heartbreakers:
        for b in state.heartbreakers:
            assert 0 <= peer_compatibility(a, b) <= 100


def test_secure_pair_beats_avoidant_pair() -> None:
    """Attachment fit lifts attraction: a secure↔secure pair out-sparks an
    otherwise-identical avoidant↔avoidant pair."""
    state = new_game(1)
    a, b = state.heartbreakers[0], state.heartbreakers[1]
    a.attachment = b.attachment = AttachmentStyle.SECURE
    secure_score = peer_compatibility(a, b)
    a.attachment = b.attachment = AttachmentStyle.AVOIDANT
    avoidant_score = peer_compatibility(a, b)
    assert secure_score > avoidant_score


# --- growth toward the ceiling -------------------------------------------


def test_attraction_grows_toward_target_and_stops() -> None:
    state, chloe, liam = _isolated_pair()
    target = peer_compatibility(chloe, liam)
    assert target > 0

    last = 0
    for turn in range(50):
        state.turn_index = turn
        advance_peer_attractions(state, SeededRng(turn))
        current = peer_affinity_between(state, "chloe", "liam")
        assert current >= last  # monotonic, never decreases
        assert current <= target  # never overshoots the ceiling
        last = current
    assert last == target  # converges exactly


def test_attraction_kept_mutual() -> None:
    state, chloe, liam = _isolated_pair()
    advance_peer_attractions(state, SeededRng(7))
    assert chloe.peer_affinity["liam"] == liam.peer_affinity["chloe"]
    assert chloe.peer_affinity["liam"] > 0


def test_no_growth_when_apart() -> None:
    state, chloe, liam = _isolated_pair()
    liam.location_id = next(
        loc for loc in type(chloe.location_id) if loc != chloe.location_id
    )
    advance_peer_attractions(state, SeededRng(1))
    assert peer_affinity_between(state, "chloe", "liam") == 0


def test_same_gender_never_attracts() -> None:
    state = new_game(1)
    chloe = next(i for i in state.heartbreakers if i.id == "chloe")
    maya = next(i for i in state.heartbreakers if i.id == "maya")  # both women
    maya.location_id = chloe.location_id
    for other in state.heartbreakers:
        if other.id not in {"chloe", "maya"}:
            other.eliminated = True
    advance_peer_attractions(state, SeededRng(1))
    assert peer_affinity_between(state, "chloe", "maya") == 0


def test_coupled_heartbreaker_grows_slower() -> None:
    """The loyalty draw: an already-coupled heartbreaker drifts toward a new face
    at half speed, so a single pair outpaces a coupled one from the same start."""
    state, chloe, liam = _isolated_pair()
    # Single baseline.
    advance_peer_attractions(state, SeededRng(3))
    single_step = peer_affinity_between(state, "chloe", "liam")

    state2, chloe2, liam2 = _isolated_pair()
    state2.couples = [Couple(partner_a_id="liam", partner_b_id="ghost", formed_on_day=1)]
    advance_peer_attractions(state2, SeededRng(3))
    coupled_step = peer_affinity_between(state2, "chloe", "liam")

    assert coupled_step <= single_step


# --- couple formation -----------------------------------------------------


def test_single_pair_couples_at_threshold() -> None:
    state, chloe, liam = _isolated_pair()
    chloe.peer_affinity["liam"] = PEER_COUPLE_THRESHOLD
    liam.peer_affinity["chloe"] = PEER_COUPLE_THRESHOLD

    memories = maybe_form_peer_couples(state, SeededRng(1))

    paired = [
        c for c in state.couples
        if {c.partner_a_id, c.partner_b_id} == {"chloe", "liam"}
    ]
    assert len(paired) == 1
    assert any("peer_couple" in m.tags for m in memories)


def test_below_threshold_does_not_couple() -> None:
    state, chloe, liam = _isolated_pair()
    chloe.peer_affinity["liam"] = PEER_COUPLE_THRESHOLD - 1
    liam.peer_affinity["chloe"] = PEER_COUPLE_THRESHOLD - 1

    memories = maybe_form_peer_couples(state, SeededRng(1))

    assert memories == []
    assert state.couples == []


def test_already_coupled_heartbreaker_does_not_form_peer_couple() -> None:
    state, chloe, liam = _isolated_pair()
    state.couples = [Couple(partner_a_id="liam", partner_b_id="ghost", formed_on_day=1)]
    chloe.peer_affinity["liam"] = 100
    liam.peer_affinity["chloe"] = 100

    memories = maybe_form_peer_couples(state, SeededRng(1))

    assert memories == []
    assert not any(
        {c.partner_a_id, c.partner_b_id} == {"chloe", "liam"} for c in state.couples
    )


def test_at_most_one_peer_couple_per_call() -> None:
    """Even with several eligible single pairs, only one couple forms per call so
    the resort pairs off gradually rather than all at once."""
    state = new_game(1)
    # Co-locate everyone and make every opposite-gender single pair red-hot.
    home = state.heartbreakers[0].location_id
    for heartbreaker in state.heartbreakers:
        heartbreaker.location_id = home
        for other in state.heartbreakers:
            if other.id != heartbreaker.id:
                heartbreaker.peer_affinity[other.id] = 100

    formed = maybe_form_peer_couples(state, SeededRng(1))

    assert formed  # something coupled
    assert len(state.couples) == 1


# --- gossip + recap surfacing --------------------------------------------


def test_crossing_friendly_threshold_emits_whisper_and_gossip() -> None:
    state = new_game(1)
    chloe = next(i for i in state.heartbreakers if i.id == "chloe")
    liam = next(i for i in state.heartbreakers if i.id == "liam")
    liam.location_id = chloe.location_id
    # Park them just under the "getting close" line so a single turn crosses it.
    chloe.peer_affinity["liam"] = PEER_FRIENDLY_THRESHOLD - 1
    liam.peer_affinity["chloe"] = PEER_FRIENDLY_THRESHOLD - 1

    created = advance_peer_attractions(state, SeededRng(1))

    assert peer_affinity_between(state, "chloe", "liam") >= PEER_FRIENDLY_THRESHOLD
    # Both principals carry the closeness memory.
    assert any("getting_close" in m.tags and m.holder_id == "chloe" for m in created)
    assert any("getting_close" in m.tags and m.holder_id == "liam" for m in created)
    # The resort overhears it: a third party picks up the gossip.
    gossip = [
        m for m in created
        if "gossip" in m.tags and m.holder_id not in {"chloe", "liam"}
    ]
    assert gossip


def test_coupled_pair_does_not_emit_closeness_whisper() -> None:
    """A coupled heartbreaker warming to a new face never reads as a budding romance:
    no single-pair 'getting close' whisper fires while either party is attached
    (it surfaces as a wandering-eye whisper instead — covered separately)."""
    state = new_game(1)
    chloe = next(i for i in state.heartbreakers if i.id == "chloe")
    liam = next(i for i in state.heartbreakers if i.id == "liam")
    liam.location_id = chloe.location_id
    state.couples = [Couple(partner_a_id="liam", partner_b_id="ghost", formed_on_day=1)]
    chloe.peer_affinity["liam"] = PEER_FRIENDLY_THRESHOLD - 1
    liam.peer_affinity["chloe"] = PEER_FRIENDLY_THRESHOLD - 1

    created = advance_peer_attractions(state, SeededRng(1))

    assert not any("getting_close" in m.tags for m in created)


# --- wandering eye (coupled heartbreakers) -----------------------------------


def _coupled_pair(seed: int = 1):
    """Return (state, chloe, liam, marcus) with chloe↔liam co-located and chloe
    already coupled to marcus, so her growing draw toward liam reads as a
    wandering eye. marcus is alive but parked elsewhere; everyone else is
    eliminated, so chloe↔liam is the only opposite-gender pair that can grow."""
    state = new_game(seed)
    chloe = next(i for i in state.heartbreakers if i.id == "chloe")
    liam = next(i for i in state.heartbreakers if i.id == "liam")
    marcus = next(i for i in state.heartbreakers if i.id == "marcus")
    liam.location_id = chloe.location_id
    marcus.location_id = next(
        loc for loc in type(chloe.location_id) if loc != chloe.location_id
    )
    for other in state.heartbreakers:
        if other.id not in {"chloe", "liam", "marcus"}:
            other.eliminated = True
    state.couples = [Couple(partner_a_id="chloe", partner_b_id="marcus", formed_on_day=1)]
    return state, chloe, liam, marcus


def test_wandering_eye_fires_when_coupled_crosses_threshold() -> None:
    state, chloe, liam, _marcus = _coupled_pair()
    # Park just under the wandering line so one co-located turn crosses it.
    chloe.peer_affinity["liam"] = PEER_WANDERING_THRESHOLD - 1
    liam.peer_affinity["chloe"] = PEER_WANDERING_THRESHOLD - 1

    created = advance_peer_attractions(state, SeededRng(1))

    assert peer_affinity_between(state, "chloe", "liam") >= PEER_WANDERING_THRESHOLD
    # Both principals remember it; it is tagged as a wandering eye, not a budding
    # single-pair romance.
    assert any("wandering_eye" in m.tags and m.holder_id == "chloe" for m in created)
    assert any("wandering_eye" in m.tags and m.holder_id == "liam" for m in created)
    assert not any("getting_close" in m.tags for m in created)


def test_wandering_eye_gives_betrayed_partner_jealousy_memory() -> None:
    state, chloe, liam, _marcus = _coupled_pair()
    chloe.peer_affinity["liam"] = PEER_WANDERING_THRESHOLD - 1
    liam.peer_affinity["chloe"] = PEER_WANDERING_THRESHOLD - 1

    created = advance_peer_attractions(state, SeededRng(1))

    # chloe's partner (marcus) is the betrayed party and gets a heavier,
    # jealousy-tagged memory so the recap reads it as personal.
    betrayed = [m for m in created if m.holder_id == "marcus"]
    assert betrayed
    assert all("jealousy" in m.tags and "drama" in m.tags for m in betrayed)
    assert all(m.emotional_weight >= 6 for m in betrayed)


def test_wandering_eye_betraying_the_player_addresses_them_directly() -> None:
    """When the wandering heartbreaker is coupled with the *player*, the whisper
    names 'the player' so the recap humanizer rewrites it to second person."""
    state, chloe, liam, _marcus = _coupled_pair()
    # Re-point chloe's couple at the player instead of marcus.
    state.couples = [Couple(partner_a_id="chloe", partner_b_id="player", formed_on_day=1)]
    chloe.peer_affinity["liam"] = PEER_WANDERING_THRESHOLD - 1
    liam.peer_affinity["chloe"] = PEER_WANDERING_THRESHOLD - 1

    created = advance_peer_attractions(state, SeededRng(1))

    player_memory = next((m for m in created if m.holder_id == "player"), None)
    assert player_memory is not None
    assert "jealousy" in player_memory.tags
    # Stored name-agnostic, but reads as second person once humanized for the recap.
    assert "the player" in player_memory.content
    assert "you" in humanize_player_reference(player_memory.content).lower()


def test_partners_growing_close_is_not_a_wandering_eye() -> None:
    """A couple warming to *each other* is their bond, not a betrayal — no
    wandering-eye whisper fires for a pair who are each other's partners."""
    state, chloe, liam = _isolated_pair()
    state.couples = [Couple(partner_a_id="chloe", partner_b_id="liam", formed_on_day=1)]
    chloe.peer_affinity["liam"] = PEER_WANDERING_THRESHOLD - 1
    liam.peer_affinity["chloe"] = PEER_WANDERING_THRESHOLD - 1

    created = advance_peer_attractions(state, SeededRng(1))

    assert not any("wandering_eye" in m.tags for m in created)


def test_wandering_eye_only_fires_once_on_crossing() -> None:
    """Past the threshold, continued growth stays quiet — no repeat whisper."""
    state, chloe, liam, _marcus = _coupled_pair()
    chloe.peer_affinity["liam"] = PEER_WANDERING_THRESHOLD + 5
    liam.peer_affinity["chloe"] = PEER_WANDERING_THRESHOLD + 5

    created = advance_peer_attractions(state, SeededRng(1))

    assert not any("wandering_eye" in m.tags for m in created)


def test_wandering_eye_surfaces_in_recap_as_single_whisper() -> None:
    """The shared gist dedupes to one clean recap line rather than one per holder."""
    state, chloe, liam, _marcus = _coupled_pair()
    chloe.peer_affinity["liam"] = PEER_WANDERING_THRESHOLD - 1
    liam.peer_affinity["chloe"] = PEER_WANDERING_THRESHOLD - 1

    created = advance_peer_attractions(state, SeededRng(1))

    contents = {m.content for m in created if "wandering_eye" in m.tags}
    assert len(contents) == 1
