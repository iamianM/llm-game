"""Opt-in tests for real Background Dialogue output."""

from __future__ import annotations

import pytest

from src.game.agents.background_dialogue import (
    BackgroundExchange,
    OpenAIBackgroundDialogue,
    _render_context,
    mock_background_dialogue,
    validate_background_exchange,
)
from src.game.state.models import Gender, Location, NPCNPCConversation, new_game


def test_mock_background_dialogue_contract() -> None:
    """Mock background dialogue satisfies the same validator as live output."""
    state = new_game(1)
    conversation = _conversation()

    exchange = mock_background_dialogue(state, conversation)

    validate_background_exchange(exchange)


def test_background_dialogue_allows_first_person_dialogue_idioms() -> None:
    """Validator only bans first-person body language, not normal dialogue idioms."""
    validate_background_exchange(
        BackgroundExchange(
            speaker_a_line="*grins* You better watch out, Liam. I keep my eyes peeled in here.",
            speaker_b_line="*laughs softly* Good, Maya, because nothing gets past you when snacks are involved.",
            tone="playful",
        )
    )


def test_background_dialogue_rejects_first_person_body_language() -> None:
    """Italic body language remains third-person observable."""
    with pytest.raises(ValueError, match="first-person body language"):
        validate_background_exchange(
            BackgroundExchange(
                speaker_a_line="*my eyes widen* You better watch out, Liam, because I notice everything.",
                speaker_b_line="*laughs softly* Good, Maya, because nothing gets past you when snacks are involved.",
                tone="playful",
            )
        )


def test_background_dialogue_context_supplies_cast_pronouns() -> None:
    """The background voice gets a pronoun roster so unisex names aren't guessed."""
    state = new_game(1)
    chloe = next(i for i in state.islanders if i.id == "chloe")
    liam = next(i for i in state.islanders if i.id == "liam")
    assert chloe.gender is Gender.WOMAN
    assert liam.gender is Gender.MAN

    rendered = _render_context(state, _conversation(), "getting more gossipy")

    assert "Cast pronouns (use exactly these" in rendered
    assert f"{chloe.name}: she/her" in rendered
    assert f"{liam.name}: he/him" in rendered


def test_background_dialogue_cast_pronouns_exclude_eliminated() -> None:
    """A Heart Out islander drops off the background pronoun roster."""
    state = new_game(1)
    eliminated = next(i for i in state.islanders if i.id == "nia")
    eliminated.eliminated = True

    rendered = _render_context(state, _conversation(), "")

    assert f"{eliminated.name}: " not in rendered


@pytest.mark.llm
def test_background_dialogue_contract() -> None:
    """Real Background Dialogue returns a valid NPC-NPC exchange."""
    state = new_game(1)
    conversation = _conversation()
    agent = OpenAIBackgroundDialogue()

    exchange = agent.generate(state, conversation, "getting more gossipy")

    validate_background_exchange(exchange)


def _conversation() -> NPCNPCConversation:
    return NPCNPCConversation(
        id="npcconv_test",
        participants=["chloe", "maya"],
        location_id=Location.POOL,
        topic="comparing notes about the new bombshell",
        started_on_turn=1,
    )
