"""Deterministic demo-mode dialogue for the Heartbreaker Voice agent.

Demo mode (the default when no LLM key is configured) never calls the model, so
these templates are the first — and often the only — conversation a player ever
sees. They must read like real, in-character Paradise Hearts lines rather than
echoing the raw menu label (the old mock literally said "I wanted to say this
properly, X: <label>", which broke immersion on the very first turn).

Lines are keyed by intent category and outcome. A stable roll seed rotates
between a few index-matched (player, npc) phrasings so repeated demo play does
not feel identical — flirting twice, or with two different Heartbreakers, no longer
returns word-for-word the same reply. The full set of NPC replies stays a small
fixed pool per (category, outcome) so traces remain detectable as mock.
Determinism (same state -> same line) is required for replay parity, so the
only entropy is the already-deterministic dice roll.

This module deliberately avoids importing the OpenAI client (unlike
``heartbreaker_voice``) so the report tooling can read the mock sentinels cheaply.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.game.state.models import Mood

# Mirror of ``Exchange.npc_tone`` (heartbreaker_voice_context). Kept local so this
# module stays dependency-light; an identical Literal is type-compatible.
Tone = Literal[
    "warm",
    "flirty",
    "suspicious",
    "amused",
    "cold",
    "vulnerable",
    "playful",
    "defensive",
]


@dataclass(frozen=True)
class _Line:
    """One (category, outcome) dialogue template.

    ``player`` and ``npc`` are parallel tuples: the reply at ``npc[i]`` is
    written to answer the opener at ``player[i]``. The same roll seed indexes
    both so a coherent pair is always returned.
    """

    player: tuple[str, ...]  # openers containing a single {name} slot
    npc: tuple[str, ...]  # replies, index-matched to ``player``
    tone: Tone
    mood: Mood


# Keyed by IntentCategory.value so callers do not have to import the enum.
_LINES: dict[str, dict[str, _Line]] = {
    "friendly": {
        "success": _Line(
            player=(
                "Come sit with me, {name} — I feel like we just click.",
                "I'm really glad you're here, {name}. You make this place feel easy.",
            ),
            npc=(
                "Aw, stop — I was hoping you'd come over. This is nice.",
                "Honestly? Same. You're really easy to be around.",
            ),
            tone="warm",
            mood=Mood.HAPPY,
        ),
        "miss": _Line(
            player=(
                "So... how are you finding it all, {name}?",
                "I keep meaning to have a proper chat, {name}.",
            ),
            npc=(
                "Yeah, it's good. *glances away* Sorry — my head's a bit all over the place today.",
                "*nods* We should. Just... not caught me at my best today, sorry.",
            ),
            tone="defensive",
            mood=Mood.CONTENT,
        ),
    },
    "flirty": {
        "success": _Line(
            player=(
                "You look unreal tonight, {name} — I can't stop looking over.",
                "I'll just say it, {name}: you're trouble, and I'm into it.",
            ),
            npc=(
                "*bites lip* Smooth. Keep talking like that and you'll turn my head.",
                "*grins* Trouble, am I? You've got no idea yet.",
            ),
            tone="flirty",
            mood=Mood.FLIRTY,
        ),
        "miss": _Line(
            player=(
                "So are you going to make me chase you, {name}, or what?",
                "Be honest, {name} — is it just me, or is there something here?",
            ),
            npc=(
                "*laughs* Easy, tiger. I don't melt quite that fast.",
                "*smirks* Maybe. I'm not making it that easy for you, though.",
            ),
            tone="amused",
            mood=Mood.CONTENT,
        ),
    },
    "deep": {
        "success": _Line(
            player=(
                "Can I be real with you, {name}? I don't open up like this often.",
                "I want to actually know you, {name} — not the version everyone else gets.",
            ),
            npc=(
                "*softens* That means a lot. Honestly... I don't let many people in either.",
                "*quiet* Nobody really asks for that version. I like that you did.",
            ),
            tone="vulnerable",
            mood=Mood.HAPPY,
        ),
        "miss": _Line(
            player=(
                "What's something you've never told anyone in here, {name}?",
                "Do you ever feel like you're putting on a front in here, {name}?",
            ),
            npc=(
                "*pauses* That's a lot, this early. Can we get there slowly?",
                "*shifts* Heavy question. I'm not sure I'm ready to go there yet.",
            ),
            tone="defensive",
            mood=Mood.ANXIOUS,
        ),
    },
    "banter": {
        "success": _Line(
            player=(
                "Be honest, {name} — you've practised that walk in the mirror, haven't you?",
                "I've decided you're my favourite menace in here, {name}.",
            ),
            npc=(
                "*cackles* Oi! The cheek of it. I like you already.",
                "*grins* Took you long enough. Obviously I'm the best one here.",
            ),
            tone="playful",
            mood=Mood.HAPPY,
        ),
        "miss": _Line(
            player=(
                "Bet I could out-flirt you any day of the week, {name}.",
                "You're all talk, {name} — go on, prove me wrong.",
            ),
            npc=(
                "*rolls eyes* Bold words. Bit quieter than I expected, though.",
                "*scoffs* All talk? Cute. You first, then.",
            ),
            tone="amused",
            mood=Mood.CONTENT,
        ),
    },
    "supportive": {
        "success": _Line(
            player=(
                "Hey — you don't have to put the brave face on with me, {name}.",
                "Whatever happens in here, {name}, I've got your back.",
            ),
            npc=(
                "*exhales* I really needed to hear that. Thank you.",
                "*small smile* That actually means everything right now.",
            ),
            tone="warm",
            mood=Mood.HAPPY,
        ),
        "miss": _Line(
            player=(
                "You good, {name}? You've seemed a bit off today.",
                "Talk to me, {name} — what's actually going on in there?",
            ),
            npc=(
                "I'm fine. *small shrug* Just... not ready to get into it.",
                "*looks down* It's nothing. Can we leave it for now?",
            ),
            tone="defensive",
            mood=Mood.ANXIOUS,
        ),
    },
    "gossip": {
        "success": _Line(
            player=(
                "Okay, between us, {name} — you did NOT hear this from me.",
                "Lean in, {name}. I've been dying to tell someone.",
            ),
            npc=(
                "*gasps* No. Right, tell me everything.",
                "*leans in* Oh my god, go on — I'm not breathing till you do.",
            ),
            tone="amused",
            mood=Mood.HAPPY,
        ),
        "miss": _Line(
            player=(
                "So... have you heard what people are saying, {name}?",
                "Can I trust you with something, {name}?",
            ),
            npc=(
                "*frowns* I don't really want to be in the middle of that, if I'm honest.",
                "*hesitates* Depends what it is... I don't love secrets in here.",
            ),
            tone="suspicious",
            mood=Mood.ANXIOUS,
        ),
    },
    "bromance": {
        "success": _Line(
            player=(
                "You're sound, {name}, genuinely — glad I've got you in here.",
                "Proper grateful for you, {name}. You keep me level.",
            ),
            npc=(
                "Likewise, mate. Us against this madhouse, yeah?",
                "*claps your shoulder* Any time. We keep each other right, yeah?",
            ),
            tone="warm",
            mood=Mood.HAPPY,
        ),
        "miss": _Line(
            player=(
                "You and me should team up in here, {name}.",
                "Where's your head at with all this, {name}?",
            ),
            npc=(
                "Maybe. *shrugs* Still working you out, to be fair.",
                "*exhales* All over the place, mate. Give us a bit, yeah?",
            ),
            tone="amused",
            mood=Mood.CONTENT,
        ),
    },
    "gossip_ring": {
        "success": _Line(
            player=(
                "Right, {name}, we need to compare notes — properly.",
                "Tell me I'm not the only one clocking things, {name}.",
            ),
            npc=(
                "*grins* Finally. Sit down — we are comparing everything.",
                "*grins* Oh, you are SO not. I've been clocking it all week.",
            ),
            tone="amused",
            mood=Mood.HAPPY,
        ),
        "miss": _Line(
            player=(
                "Be straight with me, {name} — whose side are you on?",
                "Can I have a little vent, {name}?",
            ),
            npc=(
                "*hesitates* I just don't want this getting twisted, yeah?",
                "*glances around* Quietly, yeah? I don't want it coming back on me.",
            ),
            tone="suspicious",
            mood=Mood.CONTENT,
        ),
    },
}

_DEFAULT: dict[str, _Line] = {
    "success": _Line(
        player=(
            "I just wanted a proper moment with you, {name}.",
            "Come here, {name} — let's actually talk.",
        ),
        npc=(
            "*smiles* I'm really glad you came over. This is nice.",
            "*settles in* Yeah, let's. I've been wanting a proper chat.",
        ),
        tone="warm",
        mood=Mood.HAPPY,
    ),
    "miss": _Line(
        player=(
            "I wanted to catch you for a second, {name}.",
            "Have you got a minute, {name}?",
        ),
        npc=(
            "*nods* Yeah... give me a moment, my head's elsewhere right now.",
            "*distracted* Course... sorry, I'm a bit scattered right now.",
        ),
        tone="defensive",
        mood=Mood.CONTENT,
    ),
}


def mock_exchange_fields(
    *,
    category: str | None,
    success: bool,
    target_name: str,
    roll: int | None,
) -> tuple[str, str, Tone, Mood]:
    """Return ``(player_dialogue, npc_dialogue, npc_tone, npc_mood_after)``.

    ``category`` is an ``IntentCategory`` value (or None for special intents).
    ``roll`` is the deterministic dice roll for the action; it rotates both the
    player opener and the (index-matched) NPC reply so repeated demo play varies
    without breaking replays.
    """
    outcome = "success" if success else "miss"
    line = _LINES.get(category or "", _DEFAULT).get(outcome, _DEFAULT[outcome])
    seed = roll or 0
    player = line.player[seed % len(line.player)].format(name=target_name)
    npc = line.npc[seed % len(line.npc)]
    return player, npc, line.tone, line.mood


# Every possible NPC reply, exposed so report tooling can flag a trace as mock
# without importing the heavyweight agent module. Player lines carry a formatted
# name so they are not stable; NPC lines are drawn from this fixed pool.
MOCK_NPC_LINES: frozenset[str] = frozenset(
    npc
    for table in (*_LINES.values(), _DEFAULT)
    for line in table.values()
    for npc in line.npc
)
