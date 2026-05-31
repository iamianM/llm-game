"""Tests for deterministic NPC↔NPC peer attraction (the villa's own love stories).

Covers the pure compatibility function, co-location-driven growth toward the
compatibility ceiling, single-pair couple formation (and the refusal to pair
already-coupled islanders), and the gossip/recap surfacing of both the
"getting close" whisper and the off-screen couple-up.
"""

from __future__ import annotations

from src.game.engine.peer import (
    PEER_COUPLE_THRESHOLD,
    PEER_FRIENDLY_THRESHOLD,
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
    chloe = next(i for i in state.islanders if i.id == "chloe")
    liam = next(i for i in state.islanders if i.id == "liam")
    liam.location_id = chloe.location_id
    for other in state.islanders:
        if other.id not in {"chloe", "liam"}:
            other.eliminated = True
    return state, chloe, liam


# --- pure compatibility ---------------------------------------------------


def test_compatibility_is_symmetric() -> None:
    state = new_game(1)
    for a in state.islanders:
        for b in state.islanders:
            assert peer_compatibility(a, b) == peer_compatibility(b, a)


def test_compatibility_in_range() -> None:
    state = new_game(1)
    for a in state.islanders:
        for b in state.islanders:
            assert 0 <= peer_compatibility(a, b) <= 100


def test_secure_pair_beats_avoidant_pair() -> None:
    """Attachment fit lifts attraction: a secure↔secure pair out-sparks an
    otherwise-identical avoidant↔avoidant pair."""
    state = new_game(1)
    a, b = state.islanders[0], state.islanders[1]
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
    chloe = next(i for i in state.islanders if i.id == "chloe")
    maya = next(i for i in state.islanders if i.id == "maya")  # both women
    maya.location_id = chloe.location_id
    for other in state.islanders:
        if other.id not in {"chloe", "maya"}:
            other.eliminated = True
    advance_peer_attractions(state, SeededRng(1))
    assert peer_affinity_between(state, "chloe", "maya") == 0


def test_coupled_islander_grows_slower() -> None:
    """The loyalty pull: an already-coupled islander drifts toward a new face
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


def test_already_coupled_islander_does_not_form_peer_couple() -> None:
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
    the villa pairs off gradually rather than all at once."""
    state = new_game(1)
    # Co-locate everyone and make every opposite-gender single pair red-hot.
    home = state.islanders[0].location_id
    for islander in state.islanders:
        islander.location_id = home
        for other in state.islanders:
            if other.id != islander.id:
                islander.peer_affinity[other.id] = 100

    formed = maybe_form_peer_couples(state, SeededRng(1))

    assert formed  # something coupled
    assert len(state.couples) == 1


# --- gossip + recap surfacing --------------------------------------------


def test_crossing_friendly_threshold_emits_whisper_and_gossip() -> None:
    state = new_game(1)
    chloe = next(i for i in state.islanders if i.id == "chloe")
    liam = next(i for i in state.islanders if i.id == "liam")
    liam.location_id = chloe.location_id
    # Park them just under the "getting close" line so a single turn crosses it.
    chloe.peer_affinity["liam"] = PEER_FRIENDLY_THRESHOLD - 1
    liam.peer_affinity["chloe"] = PEER_FRIENDLY_THRESHOLD - 1

    created = advance_peer_attractions(state, SeededRng(1))

    assert peer_affinity_between(state, "chloe", "liam") >= PEER_FRIENDLY_THRESHOLD
    # Both principals carry the closeness memory.
    assert any("getting_close" in m.tags and m.holder_id == "chloe" for m in created)
    assert any("getting_close" in m.tags and m.holder_id == "liam" for m in created)
    # The villa overhears it: a third party picks up the gossip.
    gossip = [
        m for m in created
        if "gossip" in m.tags and m.holder_id not in {"chloe", "liam"}
    ]
    assert gossip


def test_coupled_pair_does_not_emit_closeness_whisper() -> None:
    """A coupled islander can still warm to a new face, but it stays quiet — no
    'getting close' whisper fires while either party is attached."""
    state = new_game(1)
    chloe = next(i for i in state.islanders if i.id == "chloe")
    liam = next(i for i in state.islanders if i.id == "liam")
    liam.location_id = chloe.location_id
    state.couples = [Couple(partner_a_id="liam", partner_b_id="ghost", formed_on_day=1)]
    chloe.peer_affinity["liam"] = PEER_FRIENDLY_THRESHOLD - 1
    liam.peer_affinity["chloe"] = PEER_FRIENDLY_THRESHOLD - 1

    created = advance_peer_attractions(state, SeededRng(1))

    assert not any("getting_close" in m.tags for m in created)
