"""Day and phase progression.

Design sources:
- 08-Daily-Loop.md: Four Phases, Run Length and Pacing
- 10-Elimination-System.md: weekly flow and ceremonies
"""

from src.game.state.models import GameState, Phase
from src.game.state.phase_clock import PhaseClock

PHASE_ORDER = [
    Phase.MORNING,
    Phase.INTROS,
    Phase.CHALLENGE,
    Phase.AFTERNOON,
    Phase.TEXT,
    Phase.EVENING,
]

MAX_DAYS = 6

PHASE_BUDGETS: dict[Phase, int] = {
    Phase.MORNING: 120,
    Phase.INTROS: 180,
    Phase.CHALLENGE: 0,
    Phase.AFTERNOON: 120,
    Phase.TEXT: 30,
    Phase.EVENING: 60,
    Phase.COMPLETE: 0,
}


def is_finale_evening(state: GameState) -> bool:
    """True on the last night, once the Final Vote is the only beat left.

    On Day ``MAX_DAYS`` evening the resort is winding down to the Final Vote — the
    climactic gather that ``advance_phase_with_events`` convenes when the evening
    budget expires. Letting fresh NPC approaches and conversation interruptions
    keep firing on this night buries the one action that matters (gathering the
    cast at the flame_deck) under endless unsolicited small talk, so callers use
    this to let the resort settle and surface the Final Vote CTA cleanly. The
    player can still start their own conversations and the cast still mills
    about — only unsolicited demands on the player are held back.
    """
    return state.phase is Phase.EVENING and state.day >= MAX_DAYS


def advance_phase(state: GameState) -> None:
    """Advance the multi-day v0 clock and disperse NPCs into the new phase."""
    state.player.private_chat_attempts_this_phase = {}
    state.active_ambient_id = None
    state.consecutive_ambient_turns = 0
    state.pending_npc_approach = None
    _advance_phase_clock(state)
    _disperse_into_phase(state)


def _advance_phase_clock(state: GameState) -> None:
    if state.phase is Phase.COMPLETE:
        _reset_phase_clock(state)
        return
    if state.phase is Phase.EVENING:
        if state.day >= MAX_DAYS:
            state.phase = Phase.COMPLETE
            _reset_phase_clock(state)
            return
        # The night passes: bonds settle toward the shape of the couples before
        # the new day begins. Single chokepoint, so it fires exactly once per
        # night whether the rollover comes from a quiet evening or from the path
        # that resolves a Pairing Ceremony first.
        _apply_overnight_drift(state)
        state.day += 1
        state.phase = Phase.MORNING
        _reset_phase_clock(state)
        return
    if state.phase is Phase.MORNING:
        if state.day == 1 and state.couples and not state.intro_memory_created:
            state.phase = Phase.INTROS
        else:
            state.phase = Phase.CHALLENGE
        _reset_phase_clock(state)
        return
    if state.phase is Phase.INTROS and state.day == 1 and not state.couples:
        # Day-1 intros are the greeting circle that precedes First Spark.
        # Once everyone is met, drop into MORNING so the coupling actions fire.
        state.phase = Phase.MORNING
        _reset_phase_clock(state)
        return
    index = PHASE_ORDER.index(state.phase)
    state.phase = PHASE_ORDER[index + 1]
    _reset_phase_clock(state)


def _apply_overnight_drift(state: GameState) -> None:
    """Settle every bond one night toward the shape of the couples.

    Imported locally to mirror this module's other engine hooks and keep the
    phase-clock import surface flat.
    """
    from src.game.engine.bond_drift import apply_overnight_drift

    apply_overnight_drift(state)


def _disperse_into_phase(state: GameState) -> None:
    """Scatter free NPCs to where the new time of day motivates them.

    The Sims-style needs layer only advertises during free-roam phases, so this
    is a no-op during CHALLENGE / INTROS / COMPLETE. It is the single chokepoint
    that makes the cast leave the flame_deck after an event and re-cluster by phase
    (morning -> bedroom/kitchen, afternoon -> pool, night -> terrace/flame_deck).
    Deterministic: the jitter rng is forked from the seed, day, and new phase.
    """
    from src.game.engine.needs import plan_and_apply
    from src.game.state.rng import SeededRng

    plan_and_apply(state, SeededRng(f"{state.seed}:disperse:{state.day}:{state.phase.value}"))


def _reset_phase_clock(state: GameState) -> None:
    state.phase_clock = PhaseClock(
        phase=state.phase.value,
        budget_minutes=PHASE_BUDGETS[state.phase],
    )
