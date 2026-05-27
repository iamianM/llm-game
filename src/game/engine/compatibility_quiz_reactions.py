"""Per-round partner reaction templates for the Compatibility Quiz.

Lightweight curated lines keyed by (mechanical/flavor, correct, tier).
The live Islander Voice agent can swap these for personalised lines in
a future pass; the templates exist so the round-by-round texture is
present even in mock mode.
"""

from __future__ import annotations

from src.game.state.rng import SeededRng


def reaction_line(
    partner_name: str,
    *,
    mechanical: bool,
    tier: int,
    correct: bool,
    rng: SeededRng,
    round_index: int = 0,
) -> str:
    """Return one short reaction line for a partner after a round resolves.

    The RNG is consumed once for an across-quizzes shift (so different seeds
    yield different opening lines), then ``round_index`` adds a per-round
    rotation. Because each round in the same quiz shares the same base
    offset (the caller passes the same RNG only for the shift, not for
    selection within the bucket), back-to-back same-bucket rounds always
    pick distinct lines until the bucket cycles back round.
    """
    bucket = _BUCKETS[(mechanical, correct, _tier_bucket(tier))]
    # Shift once for variety across seeds; rotation by round_index for
    # within-quiz variety. The shift is stable within a single quiz because
    # callers fork a quiz-level RNG once and pass it in.
    shift = rng.randint(0, len(bucket) - 1)
    index = (shift + round_index) % len(bucket)
    return bucket[index].format(name=partner_name)


def _tier_bucket(tier: int) -> str:
    if tier <= 1:
        return "low"
    if tier == 2:
        return "mid"
    return "high"


# Format strings; ``{name}`` is the partner's name. Each bucket has 3 lines
# so the same seed produces a stable, deterministic-but-varied feel.
_BUCKETS: dict[tuple[bool, bool, str], list[str]] = {
    # mechanical, correct
    (True, True, "low"):  [
        "{name} nods. 'Yeah, that's me — basic info, but you were listening.'",
        "{name} smiles. 'Easy one, but I'll take it.'",
        "{name} squints, half-pleased. 'You actually paid attention, then.'",
    ],
    (True, True, "mid"):  [
        "{name} grins. 'How did you even pick that up so fast?'",
        "{name} bites her lip. 'Okay. That's the kind of thing only someone *trying* would know.'",
        "{name} laughs, a bit thrown. 'Right. Yeah. That's me.'",
    ],
    (True, True, "high"): [
        "{name} stares at you for a beat. 'You remembered. I didn't think you'd remembered.'",
        "{name} touches her necklace. 'That's… not something I tell people lightly.'",
        "{name} quiet, suddenly soft. 'Yeah. That's right. How did you know that?'",
    ],
    # mechanical, wrong
    (True, False, "low"): [
        "{name} laughs, but it lands a little flat. 'Mate, that's the basics.'",
        "{name} pulls a face. 'I told you that on day one.'",
        "{name} blinks. 'Genuinely? That's where you went?'",
    ],
    (True, False, "mid"): [
        "{name} tilts her head. 'I mean, you've never *asked*, so fair.'",
        "{name} shrugs, but her eyes do a thing. 'Cool. Okay. Noted.'",
        "{name} forces a smile. 'No worries, it's only been four days.'",
    ],
    (True, False, "high"):[
        "{name} goes very still. 'That's not me at all. Not even close.'",
        "{name} looks away. 'Right. That's good to know.'",
        "{name} folds her arms. 'You don't actually know me yet, do you.'",
    ],
    # flavor, correct
    (False, True, "low"): [
        "{name} laughs, surprised. 'Stop. You actually clocked that?'",
        "{name} tips her head. 'That's such a stupid detail to get right. I love it.'",
        "{name} grins. 'Okay, you've been watching me.'",
    ],
    (False, True, "mid"): [
        "{name} grins. 'Okay, you've been watching me.'",
        "{name} laughs, surprised. 'Stop. You actually clocked that?'",
        "{name} tips her head. 'That's such a stupid detail to get right. I love it.'",
    ],
    (False, True, "high"):[
        "{name} grins. 'Okay, you've been watching me.'",
        "{name} laughs, surprised. 'Stop. You actually clocked that?'",
        "{name} tips her head. 'That's such a stupid detail to get right. I love it.'",
    ],
    # flavor, wrong
    (False, False, "low"):[
        "{name} cracks up. 'Mate, no. Not even in the right *genre*.'",
        "{name} laughs, but there's a flicker behind it. 'Sweet guess.'",
        "{name} shakes her head, smiling. 'I'll let you off — it's a vibe question.'",
    ],
    (False, False, "mid"):[
        "{name} laughs. 'Cute guess. Wrong, but cute.'",
        "{name} pulls a face. 'You think *I'd* do that? Genuinely?'",
        "{name} grins, but barely. 'Okay, that one stung a little.'",
    ],
    (False, False, "high"):[
        "{name} laughs. 'Cute guess. Wrong, but cute.'",
        "{name} pulls a face. 'You think *I'd* do that? Genuinely?'",
        "{name} grins, but barely. 'Okay, that one stung a little.'",
    ],
}
