"""Opt-in tests for real Event Narrator output."""

from __future__ import annotations

import pytest

from src.game.agents.event_narrator import (
    EventNarration,
    OpenAIEventNarrator,
    _render_context,
    _render_minigame_details,
    mock_event_narration,
    validate_event_narration,
)
from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.ceremonies import CeremonyEvent
from src.game.state.event_models import (
    Challenge,
    MinigameChoice,
    MinigameReveal,
    MinigameRound,
)
from src.game.state.models import Couple, Phase, new_game


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
                islander_id="jordan",
            )
        ],
    )


def test_mock_event_narration_uses_player_facing_event_language() -> None:
    state = new_game(1)

    narration = mock_event_narration(
        state,
        [
            CeremonyEvent(kind="recoupling", message="internal recouple completed"),
            CeremonyEvent(kind="elimination", message="jordan leaves", islander_id="jordan"),
        ],
    )

    assert "Pairing Ceremony" in narration.prose
    assert "Jordan is Heart Out" in narration.prose
    assert "jordan" not in narration.prose


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
                        payload={"observer_id": "blake", "trait_key": "drink_of_choice"},
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
    assert "blake" not in block
    assert "Chloe (Chloe)" not in block
    assert "the player" not in block


def _couples_quiz_partner_round() -> Challenge:
    """A resolved Couples Quiz partner round (partner guessed about the player).

    The reveal payload carries raw enum codes (partner_guess="low",
    truth="high", fact_key="perception") for internal round matching plus the
    *_label display companions the narrator is allowed to quote.
    """
    return Challenge(
        id="couples-1",
        day=3,
        kind="mr_and_mrs",
        stat_tested="combined",
        participants=["player", "chloe"],
        rounds=[
            MinigameRound(
                index=1,
                prompt_id="mrandmrs_partner_perception",
                target_id="chloe",
                trait_key="player_perception",
                tier=0,
                mechanical=False,
                stem="Round 2 — partner's turn. How does the audience read you?",
                chosen_id="correct",
                points=1,
                choices=[
                    MinigameChoice(
                        id="correct",
                        label="audience cool on them",
                        fact_value="low",
                        is_correct=True,
                    ),
                    MinigameChoice(
                        id="distractor_0",
                        label="audience favourite",
                        fact_value="high",
                    ),
                ],
                reveals=[
                    MinigameReveal(
                        kind="fact",
                        subject_id="chloe",
                        payload={
                            "partner_guess": "low",
                            "partner_guess_label": "audience cool on them",
                            "truth": "high",
                            "truth_label": "audience favourite",
                            "fact_key": "perception",
                            "direction": "partner_about_player",
                        },
                    )
                ],
            )
        ],
        current_round_index=2,
        total_points=1,
        classification="partial",
        audience_delta=0,
    )


def test_couples_quiz_block_never_leaks_partner_guess_codes() -> None:
    """The Couples Quiz partner-round recap must quote display labels only.

    Regression for "'low' for perception, 'man' for gender" leaking into the
    recap: raw enum codes and routing keys (fact_key/direction) live only in the
    internal payload; the narrator block exposes the *_label forms.
    """
    state = new_game(1)
    state.pending_challenge = _couples_quiz_partner_round()

    block = _render_minigame_details(state)

    assert block, "expected a rendered minigame block for a resolved quiz"
    # Display labels are present and quotable.
    assert "audience cool on them" in block
    assert "audience favourite" in block
    # Raw enum codes paired against a key ("low" for perception) were the leak —
    # the value column must now carry the label, never the bare code.
    assert ": low" not in block
    assert ": high" not in block
    assert "guess: low" not in block
    # Internal routing keys never reach the narrator.
    assert "partner_about_player" not in block
    assert "partner about player" not in block
    assert "fact_key" not in block
    assert "fact key" not in block
    assert "direction" not in block


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


def test_validate_event_narration_rejects_eq_stat_jargon() -> None:
    """The bare "EQ" stat abbreviation must not reach player-facing prose.

    nano likes to free-associate "Compatibility Quiz" -> "EQ test" and slip the
    raw stat name into a ceremony beat (observed in a live First Spark run).
    """
    with pytest.raises(ValueError, match="leaked engine token"):
        validate_event_narration(
            EventNarration(
                prose=(
                    "The Pairing Ceremony locks in you and Chloe, and the "
                    "Compatibility Quiz's EQ test remains pending."
                )
            ),
            [CeremonyEvent(kind="recoupling", message="couples locked", islander_id="chloe")],
        )


def test_validate_event_narration_allows_eq_inside_words() -> None:
    """The "EQ" guard is word-bounded — ordinary words are never false flags."""
    validate_event_narration(
        EventNarration(
            prose=(
                "Chloe's equal footing with you holds as the sequence of looks "
                "between them settles into something steady."
            )
        ),
        [CeremonyEvent(kind="recoupling", message="couples locked", islander_id="chloe")],
    )


def test_event_narrator_context_names_player_couple() -> None:
    """Current couple context names both partners — never a raw id or "player"."""
    state = new_game(1)
    state.player.name = "Demo"
    state.couples = [Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=1)]

    # Producers now emit display-safe messages (names, not ids or "the player"),
    # so the narrator context can trust the message verbatim.
    rendered = _render_context(
        state,
        [CeremonyEvent(kind="recoupling", message="Chloe couples with Demo.", islander_id="chloe")],
    )

    assert "Current player couple: Demo is coupled with Chloe" in rendered
    assert "(Chloe)" not in rendered


def test_recoupling_narrated_as_evening_after_clock_rolls_to_morning() -> None:
    """A firepit ceremony resolves at night, but the engine rolls the clock to
    the next morning the instant the recoupling pick lands (so the daily recap
    can fire). The narrator must still be told it's the prior evening, or it
    writes "morning tension" over a torch-lit ceremony."""
    state = new_game(1)
    state.day = 4
    state.phase = Phase.MORNING

    rendered = _render_context(
        state,
        [CeremonyEvent(kind="recoupling", message="The Pairing Ceremony locks in the next couples.")],
    )

    assert "Day: 3" in rendered
    assert "Phase: evening" in rendered
    assert "Phase: morning" not in rendered


def test_non_ceremony_morning_events_keep_the_live_clock() -> None:
    """The evening pin is scoped to firepit ceremonies — an ordinary morning
    beat must still narrate as the current morning."""
    state = new_game(1)
    state.day = 4
    state.phase = Phase.MORNING

    rendered = _render_context(
        state,
        [CeremonyEvent(kind="bombshell", message="Aisha enters the villa.", islander_id="aisha")],
    )

    assert "Day: 4" in rendered
    assert "Phase: morning" in rendered


def test_event_producers_emit_display_safe_messages() -> None:
    """Engine event producers resolve ids and the player to display names at the
    source, so no raw id or "the player" meta-token reaches a rendered message,
    a memory, or the narrator context (ENGINEERING R7 — typed at the source,
    never regex-scrubbed downstream)."""
    from src.game.engine.hideaway import hideaway_event
    from src.game.engine.results import MechanicalResult
    from src.game.engine.turn_proposals import proposal_event
    from src.game.state.models import Couple

    state = new_game(1)
    state.player.name = "Demo"
    state.couples = [Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=1)]
    state.hideaway.partner_id = "chloe"

    hideaway = hideaway_event(state)
    assert "the player" not in hideaway.message.lower()
    assert "Demo" in hideaway.message
    assert "Chloe" in hideaway.message

    # A recoupling proposal from a starting-cast NPC (raw id "blake").
    result = MechanicalResult(
        action=PlayerAction(kind=ActionKind.NPC_PROPOSAL_RESPONSE, target_id="player"),
        success=True,
        tags=["npc_proposal_response"],
        proposal_outcome={
            "proposer_id": "blake",
            "target_id": "player",
            "accepted": True,
            "chance": 60,
            "roll": 30,
        },
    )
    event = proposal_event(state, result)
    assert event is not None
    assert "blake" not in event.message
    assert "Blake" in event.message
    assert "Demo" in event.message


def test_event_narrator_context_supplies_cast_pronouns() -> None:
    """Every living islander's pronouns reach the narrator so unisex names don't
    get the wrong third-person pronoun in ceremony prose."""
    state = new_game(1)
    state.player.name = "Demo"
    chloe = next(islander for islander in state.islanders if islander.id == "chloe")

    rendered = _render_context(
        state,
        [CeremonyEvent(kind="elimination", message="Liam leaves.", islander_id="liam")],
    )

    assert "Cast pronouns (use exactly these" in rendered
    expected = "she/her" if chloe.gender.value == "woman" else "he/him"
    assert f"- {chloe.name}: {expected}" in rendered
    # The player is governed by the contestant rule, not the pronoun roster.
    assert f"- {state.player.name}:" not in rendered


def test_event_narrator_context_names_player_in_third_person() -> None:
    """The context tells the narrator the player's third-person name."""
    state = new_game(1)
    state.player.name = "Demo"

    rendered = _render_context(
        state,
        [CeremonyEvent(kind="elimination", message="Liam leaves.", islander_id="liam")],
    )

    assert "named Demo" in rendered


def test_event_narrator_context_addresses_nameless_player_in_second_person() -> None:
    """A nameless player is narrated in second person, never an abstract label.

    Regression for the "Eq stands beside Chloe" garble: when the player kept the
    "You" placeholder, the narrator was told to call them "the islander", which
    gpt-5-nano hallucinated into a fake proper name. The fix narrates the
    nameless player in second person (consistent with the daily recap), which
    cannot be turned into an invented name.
    """
    state = new_game(1)
    # new_game leaves the placeholder "You" name in place.
    state.couples = [Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=1)]

    rendered = _render_context(
        state,
        [CeremonyEvent(kind="recoupling", message="Chloe couples with you.", islander_id="chloe")],
    )

    # The player is addressed in second person, never labelled "the islander".
    # (The phrase may still appear inside the negative instruction that forbids
    # inventing it, so we check the labelling forms, not a bare substring.)
    assert "named the islander" not in rendered
    assert "refer to them as the islander" not in rendered
    assert "SECOND PERSON" in rendered
    # Couple line is grammatical second person, not "you is coupled".
    assert "Current player couple: you are coupled with Chloe" in rendered
    assert "you is coupled" not in rendered
