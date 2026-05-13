"""Meta-tests for shared pytest setup and test performance dependencies."""

from __future__ import annotations

import pytest

from src.game.agents.event_narrator import OpenAIEventNarrator
from src.game.content.models import ContentIndex


def test_session_scoped_content_index_fixture(content_index: ContentIndex) -> None:
    assert content_index.archetypes
    assert content_index.locations


def test_openai_client_is_lazy_until_first_call() -> None:
    agent = OpenAIEventNarrator()

    assert "_client" not in agent.__dict__


def test_pytest_xdist_available() -> None:
    pytest.importorskip("xdist")
