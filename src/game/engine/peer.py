"""Deterministic NPC↔NPC attraction — the resort's own love stories.

The player is not the only one falling for someone. Other heartbreakers develop
crushes on *each other*, grow closer the more time they spend together, and —
when two singles click hard enough — quietly couple up off-screen. And the ones
who are *already* coupled aren't immune: spend enough time beside the wrong
person and a wandering eye starts to show, which the resort whispers about ("your
partner's been getting close to someone"). The player feels all of this through
the gossip mill and the morning recap ("while you were busy..."), which makes
the resort breathe instead of orbiting only the player.

Everything here is deterministic: attraction is a pure function of fixed
personality data (Big5 + attachment) plus who is standing where, advanced by a
seeded RNG. The same seed and intent sequence reproduces the same love stories.

Design sources:
- 09-Social-Dynamics.md: autonomous NPC behavior, off-screen relationships
- 07-Gossip-And-Information.md: gossip-generating memories
"""

from __future__ import annotations

from src.game.engine.memory import add_memory_batch, propagate_gossip_seeds
from src.game.state.memory import GossipSeed, MemoryBatch, MemoryDraft
from src.game.state.models import Couple, GameState, HeartbreakerState, Memory
from src.game.state.personality import AttachmentStyle
from src.game.state.rng import SeededRng

# Attraction first reads as "getting close" — a whisper the resort starts to
# notice — well before anyone couples up.
PEER_FRIENDLY_THRESHOLD = 45
# An already-coupled heartbreaker warming to a new face is juicier — and grows at
# half speed — so the resort clocks it earlier, at a lower bar than the single
# "getting close" line. This is the "wandering eye" the morning recap surfaces
# to a betrayed partner (including the player, when it's *their* other half).
PEER_WANDERING_THRESHOLD = 38
# Two singles whose mutual attraction crosses this couple up on their own. Tuned
# against the real compatibility spread (most opposite-gender pairs top out in
# the low 50s–mid 60s): only a genuine, top-decile spark clears it, so peer
# couples stay rare and earned rather than everyone pairing off.
PEER_COUPLE_THRESHOLD = 58
# Fraction of the remaining gap to the compatibility target closed each eligible
# (co-located) resort turn. A slow burn: a strong pair needs many shared turns.
PEER_GROWTH_RATE = 0.18

# Symmetric attachment-pair chemistry. frozenset keys collapse order and make a
# same-style pair a single-element set. Secure stabilises; the anxious↔avoidant
# magnet is real but volatile; two avoidants barely spark.
_ATTACHMENT_PAIR_BONUS: dict[frozenset[AttachmentStyle], int] = {
    frozenset({AttachmentStyle.SECURE}): 12,
    frozenset({AttachmentStyle.SECURE, AttachmentStyle.ANXIOUS}): 8,
    frozenset({AttachmentStyle.SECURE, AttachmentStyle.AVOIDANT}): 6,
    frozenset({AttachmentStyle.SECURE, AttachmentStyle.FEARFUL}): 7,
    frozenset({AttachmentStyle.ANXIOUS, AttachmentStyle.AVOIDANT}): 6,
    frozenset({AttachmentStyle.ANXIOUS}): 2,
    frozenset({AttachmentStyle.ANXIOUS, AttachmentStyle.FEARFUL}): 1,
    frozenset({AttachmentStyle.AVOIDANT}): -4,
    frozenset({AttachmentStyle.AVOIDANT, AttachmentStyle.FEARFUL}): -2,
    frozenset({AttachmentStyle.FEARFUL}): -1,
}


def peer_compatibility(a: HeartbreakerState, b: HeartbreakerState) -> int:
    """Return the symmetric 0..100 attraction ceiling for two heartbreakers.

    Pure function of fixed personality data, so it is identical no matter which
    heartbreaker is passed first. Shared social wavelength (openness/extraversion),
    combined warmth, low combined volatility, and attachment fit all lift it.
    """
    big5_a, big5_b = a.big5, b.big5
    openness_fit = 10 - abs(big5_a.openness - big5_b.openness)  # 1..10
    extraversion_fit = 10 - abs(big5_a.extraversion - big5_b.extraversion)  # 1..10
    warmth = big5_a.agreeableness + big5_b.agreeableness  # 2..20
    volatility = big5_a.neuroticism + big5_b.neuroticism  # 2..20
    attachment_bonus = _ATTACHMENT_PAIR_BONUS.get(
        frozenset({a.attachment, b.attachment}), 0
    )
    raw = (
        20
        + openness_fit * 1.6
        + extraversion_fit * 1.2
        + (warmth - 10) * 1.4
        - (volatility - 8) * 1.0
        + attachment_bonus
    )
    return max(0, min(100, round(raw)))


def peer_affinity_between(state: GameState, a_id: str, b_id: str) -> int:
    """Return the current mutual attraction between two heartbreakers (0 if none)."""
    for heartbreaker in state.heartbreakers:
        if heartbreaker.id == a_id:
            return heartbreaker.peer_affinity.get(b_id, 0)
    return 0


def advance_peer_attractions(state: GameState, rng: SeededRng) -> list[Memory]:
    """Nudge co-located, opposite-gender pairs toward their compatibility ceiling.

    Returns any memories created when a pair crosses a visibility line: a
    "getting close" whisper for two singles, or a "wandering eye" whisper (plus a
    jealousy memory for the betrayed partner, the player included) when one of
    them is already coupled. The caller folds these into the turn's recorded
    changes. Attraction only grows while two heartbreakers are actually together, so
    where people choose to spend their time quietly shapes who falls for whom.
    """
    created: list[Memory] = []
    active = [heartbreaker for heartbreaker in state.heartbreakers if not heartbreaker.eliminated]
    for index, first in enumerate(active):
        for second in active[index + 1 :]:
            if first.gender == second.gender:
                continue
            if first.location_id != second.location_id:
                continue
            target = peer_compatibility(first, second)
            current = first.peer_affinity.get(second.id, 0)
            if current >= target:
                continue
            pair_rng = rng.fork(
                f"peer:{state.day}:{state.turn_index}:"
                f"{min(first.id, second.id)}:{max(first.id, second.id)}"
            )
            gap = target - current
            step = max(1, int(gap * PEER_GROWTH_RATE) + pair_rng.randint(0, 1))
            # Loyalty draw: someone already coupled drifts toward a new face at
            # half speed (they rarely reach the couple threshold while attached).
            anyone_coupled = _is_coupled(state, first.id) or _is_coupled(state, second.id)
            if anyone_coupled:
                step = max(1, step // 2)
            updated = min(target, current + step)
            _set_mutual(first, second, updated)
            if anyone_coupled:
                # A wandering eye: at least one of them is taken, so this isn't a
                # budding romance — it's a quiet betrayal the resort starts to
                # whisper about (and the betrayed partner, player included, hears).
                # But skip a pair who are each other's partners: a couple warming
                # to *each other* is just their bond, not a betrayal of anyone.
                if (
                    current < PEER_WANDERING_THRESHOLD <= updated
                    and _partner_id(state, first.id) != second.id
                ):
                    created.extend(_commit_batch(state, _wandering_eye_batch(state, first, second)))
            elif current < PEER_FRIENDLY_THRESHOLD <= updated:
                created.extend(_commit_batch(state, _closeness_batch(state, first, second)))
    return created


def maybe_form_peer_couples(state: GameState, rng: SeededRng) -> list[Memory]:
    """Couple up the single pair whose mutual attraction has crossed the line.

    At most one new peer couple forms per call so the resort pairs off gradually
    rather than snapping into couples all at once. Returns the memories created
    (couple announcement + gossip seeds) for the caller to record.
    """
    active = [heartbreaker for heartbreaker in state.heartbreakers if not heartbreaker.eliminated]
    best: tuple[int, HeartbreakerState, HeartbreakerState] | None = None
    for index, first in enumerate(active):
        for second in active[index + 1 :]:
            if first.gender == second.gender:
                continue
            if _is_coupled(state, first.id) or _is_coupled(state, second.id):
                continue
            affinity = first.peer_affinity.get(second.id, 0)
            if affinity < PEER_COUPLE_THRESHOLD:
                continue
            if best is None or affinity > best[0]:
                best = (affinity, first, second)
    if best is None:
        return []
    _affinity, first, second = best
    _form_peer_couple(state, first, second)
    return _commit_batch(state, _peer_couple_batch(state, first, second))


def _form_peer_couple(state: GameState, first: HeartbreakerState, second: HeartbreakerState) -> None:
    # Both are single (the caller guarantees it), so there is no existing couple
    # to dissolve and no player partner reveal to trigger.
    state.couples.append(
        Couple(
            partner_a_id=first.id,
            partner_b_id=second.id,
            formed_on_day=state.day,
            formed_via="proposal",
            rebound=True,
        )
    )


def _closeness_batch(state: GameState, first: HeartbreakerState, second: HeartbreakerState) -> MemoryBatch:
    return _pair_batch(
        state,
        first,
        second,
        gist=f"{first.name} and {second.name} have been gravitating toward each other.",
        weight=5,
        tags=["peer_attraction", "getting_close"],
    )


def _wandering_eye_batch(state: GameState, first: HeartbreakerState, second: HeartbreakerState) -> MemoryBatch:
    """Build the gossip a coupled heartbreaker's drifting attention sets off.

    At least one of ``first``/``second`` is coupled. Both principals remember
    the moment; every *betrayed partner* (the coupled heartbreakers' other halves —
    the player among them when it's their partner who is wandering) gets a
    heavier, jealousy-tagged memory so the recap reads it as personal and the
    arrival-roll drama heuristics treat them as freshly wound up. A single
    shared gist keeps the recap to one clean whisper.
    """
    first_partner = _partner_id(state, first.id)
    second_partner = _partner_id(state, second.id)
    if first_partner and second_partner:
        a_ref = _partner_reference(state, first_partner)
        b_ref = _partner_reference(state, second_partner)
        gist = (
            f"{first.name} and {second.name} keep gravitating toward each other"
            f" — {a_ref} and {b_ref} have no idea."
        )
        betrayed = [(first_partner, first.id), (second_partner, second.id)]
    else:
        wanderer, other = (first, second) if first_partner else (second, first)
        partner_id = first_partner or second_partner
        assert partner_id is not None  # caller guarantees one is coupled
        gist = (
            f"{wanderer.name} has been getting cosy with {other.name}"
            f" — and {wanderer.name}'s meant to be coupled up with"
            f" {_partner_reference(state, partner_id)}."
        )
        betrayed = [(partner_id, wanderer.id)]

    tags = ["peer_attraction", "wandering_eye", "drama"]
    # Weight hierarchy: a peer couple forming (7) outranks a wandering eye (the
    # betrayed partner's copy, 6) which outranks the principals' own version and
    # the single-pair closeness whisper (5) — so drama stays visible in the
    # recap without burying the player's own beats every single day.
    memories = [
        MemoryDraft(
            holder_id=first.id,
            subject_id=second.id,
            content=gist,
            source="direct",
            emotional_weight=5,
            tags=tags,
        ),
        MemoryDraft(
            holder_id=second.id,
            subject_id=first.id,
            content=gist,
            source="direct",
            emotional_weight=5,
            tags=tags,
        ),
    ]
    for partner_id, wanderer_id in betrayed:
        # A partner who has already left the resort is no longer a memory holder;
        # skip their copy rather than crash. The principals' whisper + gossip
        # still surface the drama.
        if not _is_valid_holder(state, partner_id):
            continue
        memories.append(
            MemoryDraft(
                holder_id=partner_id,
                subject_id=wanderer_id,
                content=gist,
                # They didn't see it themselves — it drifted back to them — but
                # "witnessed" keeps the draft source_id-free while the drama and
                # jealousy tags carry the weight that stirs their behaviour.
                source="witnessed",
                emotional_weight=6,
                tags=["wandering_eye", "jealousy", "drama", "gossip"],
            )
        )
    excluded = {first.id, second.id, *(partner_id for partner_id, _ in betrayed)}
    return MemoryBatch(
        kind="background",
        memories=memories,
        summary=gist,
        gossip_seeds=[
            GossipSeed(
                subject_id=first.id,
                holder_id=second.id,
                gist=gist,
                spreadable_to=_onlookers(state, excluded),
                emotional_weight=6,
                tags=["wandering_eye", "drama", "gossip"],
            )
        ],
    )


def _peer_couple_batch(state: GameState, first: HeartbreakerState, second: HeartbreakerState) -> MemoryBatch:
    return _pair_batch(
        state,
        first,
        second,
        gist=f"{first.name} and {second.name} quietly decided to couple up.",
        weight=7,
        tags=["peer_couple", "got_together"],
    )


def _pair_batch(
    state: GameState,
    first: HeartbreakerState,
    second: HeartbreakerState,
    *,
    gist: str,
    weight: int,
    tags: list[str],
) -> MemoryBatch:
    # Both principals remember the moment in the same third-person voice. The
    # daily recap dedupes on identical content, so this surfaces as a single
    # clean whisper to the player rather than two near-duplicate lines.
    return MemoryBatch(
        kind="background",
        memories=[
            MemoryDraft(
                holder_id=first.id,
                subject_id=second.id,
                content=gist,
                source="direct",
                emotional_weight=weight,
                tags=tags,
            ),
            MemoryDraft(
                holder_id=second.id,
                subject_id=first.id,
                content=gist,
                source="direct",
                emotional_weight=weight,
                tags=tags,
            ),
        ],
        summary=gist,
        gossip_seeds=[
            GossipSeed(
                subject_id=first.id,
                holder_id=second.id,
                gist=gist,
                spreadable_to=_onlookers(state, {first.id, second.id}),
                emotional_weight=weight,
                tags=[*tags, "gossip"],
            )
        ],
    )


def _commit_batch(state: GameState, batch: MemoryBatch) -> list[Memory]:
    created = add_memory_batch(state, batch, day=state.day, turn=state.turn_index)
    created.extend(
        propagate_gossip_seeds(state, batch.gossip_seeds, day=state.day, turn=state.turn_index)
    )
    return created


def _onlookers(state: GameState, principals: set[str]) -> list[str]:
    return [
        heartbreaker.id
        for heartbreaker in state.heartbreakers
        if not heartbreaker.eliminated and heartbreaker.id not in principals
    ][:3]


def _set_mutual(first: HeartbreakerState, second: HeartbreakerState, value: int) -> None:
    first.peer_affinity[second.id] = value
    second.peer_affinity[first.id] = value


def _is_coupled(state: GameState, heartbreaker_id: str) -> bool:
    return any(
        heartbreaker_id in {couple.partner_a_id, couple.partner_b_id}
        for couple in state.couples
    )


def _partner_id(state: GameState, heartbreaker_id: str) -> str | None:
    """Return ``heartbreaker_id``'s current partner id, or None if single.

    The partner may be the player ("player"), which is exactly when a wandering
    eye becomes the player's own business.
    """
    for couple in state.couples:
        ids = {couple.partner_a_id, couple.partner_b_id}
        if heartbreaker_id in ids:
            others = ids - {heartbreaker_id}
            if others:
                return others.pop()
    return None


def _partner_reference(state: GameState, partner_id: str) -> str:
    """Human-readable name for a betrayed partner in whisper text.

    The player is referred to with the name-agnostic "the player" token so the
    daily recap rewrites it to second person ("...coupled up with you.")."""
    if partner_id == state.player.id:
        return "the player"
    for heartbreaker in state.heartbreakers:
        if heartbreaker.id == partner_id:
            return heartbreaker.name
    return "their partner"


def _is_valid_holder(state: GameState, holder_id: str) -> bool:
    if holder_id == state.player.id:
        return True
    return any(heartbreaker.id == holder_id and not heartbreaker.eliminated for heartbreaker in state.heartbreakers)
