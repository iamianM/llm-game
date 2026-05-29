"""Opt-in tests for real Event Narrator output."""

from __future__ import annotations

import pytest

from src.game.agents.event_narrator import (
    EventNarration,
    OpenAIEventNarrator,
    _render_context,
    _render_minigame_details,
    _sanitize_event_message,
    mock_event_narration,
    validate_event_narration,
)
from src.game.engine.ceremonies import CeremonyEvent
from src.game.state.event_models import (
    Challenge,
    MinigameChoice,
    MinigameReveal,
    MinigameRound,
)
from src.game.state.models import Couple, new_game


@pytest.mark.llm
@pytest.mark.parametrize(
    "events",
    [
        [CeremonyEvent(kind="bombshell", message="Aisha enters the villa.", islander_id="aisha")],
        [CeremonyEvent(kind="recoupling", message="Chloe couples with the player.", islander_id="chloe")],
        [CeremonyEvent(kind="elimination", message="Liam leaves the villa.", islander_id="liam")],
    ],
)
def test_event_narrator_output_contract(events: list[CeremonyEvent]) -> None:
    """Event Narrator prose stays bounded and references supplied participants."""
    state = new_game(1)
    agent = OpenAIEventNarrator()

    narration = agent.narrate(state, events)

    validate_event_narration(narration, events)


def test_event_narrator_validation_accepts_starting_cast_display_name() -> None:
    """Starting-cast ids may appear in prose as their public first name."""
    validate_event_narration(
        narration=EventNarration(
            prose="The firepit falls quiet as Jordan faces the decision. Every glance sharpens, and the villa absorbs the shock."
        ),
        events=[
            CeremonyEvent(
                kind="elimination",
                message="Jordan leaves the villa.",
                islander_id="jordan_start",
            )
        ],
    )


def test_mock_event_narration_uses_player_facing_event_language() -> None:
    state = new_game(1)

    narration = mock_event_narration(
        state,
        [
            CeremonyEvent(kind="recoupling", message="internal recouple completed"),
            CeremonyEvent(kind="elimination", message="jordan_start leaves", islander_id="jordan_start"),
        ],
    )

    assert "Pairing Ceremony" in narration.prose
    assert "Jordan is Heart Out" in narration.prose
    assert "jordan_start" not in narration.prose


def _quiz_with_round() -> Challenge:
    """A resolved compatibility quiz whose round carries an engine trait key."""
    return Challenge(
        id="quiz-1",
        day=1,
        kind="compatibility_quiz",
        stat_tested="combined",
        participants=["player", "chloe"],
        rounds=[
            MinigameRound(
                index=0,
                prompt_id="p1",
                target_id="chloe",
                trait_key="drink_of_choice",
                tier=2,
                mechanical=True,
                stem="What is Chloe's drink of choice?",
                chosen_id="c2",
                points=0,
                choices=[
                    MinigameChoice(id="c1", label="white wine", is_correct=True),
                    MinigameChoice(id="c2", label="espresso martini"),
                ],
                reveals=[
                    MinigameReveal(
                        kind="fact",
                        subject_id="chloe",
                        payload={"observer_id": "blake_start", "trait_key": "drink_of_choice"},
                    )
                ],
            )
        ],
        current_round_index=1,
        total_points=0,
        classification="failure",
        audience_delta=-1,
    )


def test_minigame_block_never_leaks_engine_tokens() -> None:
    """The narrator context humanizes keys and uses bare names, never raw ids.

    Regression for the leak "missing Chloe (Chloe) on drink_of_choice": the
    block must not contain snake_case keys, key=value metadata, or a doubled
    "Name (Name)" token that the model would echo verbatim.
    """
    state = new_game(1)
    state.pending_challenge = _quiz_with_round()

    block = _render_minigame_details(state)

    assert block, "expected a rendered minigame block for a resolved quiz"
    assert "drink_of_choice" not in block
    assert "drink of choice" in block
    assert "trait=" not in block
    assert "flavor_key=" not in block
    assert "blake_start" not in block
    assert "Chloe (Chloe)" not in block
    assert "the player" not in block


def test_validate_event_narration_rejects_leaked_snake_case_key() -> None:
    """A leaked engine key in prose fails validation."""
    with pytest.raises(ValueError, match="leaked engine token"):
        validate_event_narration(
            EventNarration(
                prose="The quiz ends as you miss Chloe on drink_of_choice by a mile."
            ),
            [CeremonyEvent(kind="challenge", message="quiz resolved", islander_id="chloe")],
        )


def test_validate_event_narration_rejects_key_value_metadata() -> None:
    """Bracketed key=value metadata in prose fails validation."""
    with pytest.raises(ValueError, match="leaked engine token"):
        validate_event_narration(
            EventNarration(prose="Chloe reacts (trait=charm) and the villa stirs."),
            [CeremonyEvent(kind="challenge", message="quiz resolved", islander_id="chloe")],
        )


def test_validate_event_narration_accepts_clean_quiz_prose() -> None:
    """Clean prose quoting the answer text passes validation."""
    validate_event_narration(
        EventNarration(
            prose=(
                "The Compatibility Quiz lands with a wince: you guessed an espresso "
                "martini when Chloe's drink of choice was white wine, and the villa "
                "feels the miss."
            )
        ),
        [CeremonyEvent(kind="challenge", message="quiz resolved", islander_id="chloe")],
    )


def test_event_narrator_context_names_player_couple() -> None:
    """Current couple context names both partners — never a raw id or "player"."""
    state = new_game(1)
    state.player.name = "Demo"
    state.couples = [Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=1)]

    rendered = _render_context(
        state,
        [CeremonyEvent(kind="recoupling", message="Chloe couples with the player.", islander_id="chloe")],
    )

    assert "Current player couple: Demo is coupled with Chloe" in rendered
    # The third-person player name replaces the meta "the player" and raw ids.
    assert "player with chloe" not in rendered
    assert "(Chloe)" not in rendered


def test_event_narrator_context_names_player_in_third_person() -> None:
    """The context tells the narrator the player's third-person name."""
    state = new_game(1)
    state.player.name = "Demo"

    rendered = _render_context(
        state,
        [CeremonyEvent(kind="elimination", message="Liam leaves.", islander_id="liam")],
    )

    assert "named Demo" in rendered


def test_sanitize_event_message_resolves_ids_and_player() -> None:
    """Raw ids and "the player" in engine messages become human names."""
    state = new_game(1)
    state.player.name = "Demo"

    # Mirrors hideaway.py / turn.py message phrasing.
    assert (
        _sanitize_event_message(state, "The player and chloe leave for a private night.")
        == "Demo and Chloe leave for a private night."
    )
    assert (
        _sanitize_event_message(state, "blake_start wants to ask the player to recouple.")
        == "Blake wants to ask Demo to recouple."
    )
