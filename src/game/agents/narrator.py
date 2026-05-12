"""Narrator agent construction and narration calls.

Design sources:
- 03-LLM-Architecture.md: Dialogue Writing, Event Narration
- 11-Conversation-Flow.md: single exchange generation and continuity

Implementation rule:
The Narrator receives resolved mechanical results and visible context. It does
not mutate game state or decide outcomes.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel, ConfigDict

from src.game.content.loader import load_content
from src.game.content.models import ContentIndex
from src.game.engine.actions import ActionKind
from src.game.engine.rules import MechanicalResult
from src.game.state.models import GameState

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_BUDGET_USD = 5.0
ESTIMATED_COST_PER_CALL_USD = 0.002


class Narration(BaseModel):
    """Narrator output committed through the agent boundary."""

    model_config = ConfigDict(extra="forbid")

    prose: str
    tone: str


class VisibleContext(BaseModel):
    """Filtered per-turn context given to the Narrator."""

    model_config = ConfigDict(extra="forbid")

    day: int
    phase: str
    location: str
    visible_islanders: list[str]
    location_flavor: str
    archetype_flavor: dict[str, str]


NarratorFn = Callable[[GameState, MechanicalResult], str]


class OpenAINarrator:
    """Single real Narrator backed by the available OpenAI key."""

    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        budget_usd: float | None = None,
        content: ContentIndex | None = None,
    ) -> None:
        _load_dotenv_local()
        self._client = OpenAI()
        self._model = model
        self._budget_usd = (
            float(os.environ.get("LLM_BUDGET_USD", DEFAULT_BUDGET_USD))
            if budget_usd is None
            else budget_usd
        )
        self._spent_usd = 0.0
        self._content = content if content is not None else load_content()

    @property
    def spent_usd(self) -> float:
        """Return estimated spend for this process."""
        return self._spent_usd

    def narrate(self, state: GameState, result: MechanicalResult) -> str:
        """Generate narration for one resolved mechanical result."""
        self._reserve_budget()
        context = visible_context(state, result, self._content)
        response = self._client.responses.create(
            model=self._model,
            input=[
                {
                    "role": "system",
                    "content": Path("src/game/agents/prompts/narrator.md").read_text(
                        encoding="utf-8"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Write 35-90 words of Love Island-style narration. "
                        "No digits. Do not mention hidden stats.\n"
                        f"Context: {context.model_dump_json()}\n"
                        f"Mechanical result: {result.model_dump_json()}"
                    ),
                },
            ],
            max_output_tokens=220,
        )
        prose = response.output_text.strip()
        return prose if prose else mock_narration(state, result)

    def _reserve_budget(self) -> None:
        projected = self._spent_usd + ESTIMATED_COST_PER_CALL_USD
        if projected > self._budget_usd:
            raise RuntimeError("LLM budget exceeded")
        self._spent_usd = projected


def visible_context(
    state: GameState,
    result: MechanicalResult,
    content: ContentIndex | None = None,
) -> VisibleContext:
    """Build the visible context given to the Narrator."""
    index = content if content is not None else load_content()
    visible = [
        islander
        for islander in state.islanders
        if islander.location_id == state.location_id and not islander.eliminated
    ]
    location_content = index.locations.get(state.location_id.value)
    return VisibleContext(
        day=state.day,
        phase=state.phase.value,
        location=state.location_id.value,
        visible_islanders=[islander.name for islander in visible],
        location_flavor="" if location_content is None else location_content.body,
        archetype_flavor={
            islander.name: index.archetypes[islander.archetype].body
            for islander in visible
            if islander.archetype in index.archetypes
        },
    )


def mock_narration(state: GameState, result: MechanicalResult) -> str:
    """Return deterministic mock narration until the real Narrator is enabled."""
    if result.action.kind is ActionKind.TALK:
        target_id = result.action.target_id or "someone"
        outcome = "lands" if result.success else "falls flat"
        return f"Your chat with {target_id} {outcome} by the {state.location_id}."
    if result.action.kind is ActionKind.FLIRT:
        target_id = result.action.target_id or "someone"
        outcome = "sparks" if result.success else "gets awkward"
        return f"Your flirt with {target_id} {outcome} by the {state.location_id}."
    if result.action.kind is ActionKind.BOLD_FLIRT:
        target_id = result.action.target_id or "someone"
        outcome = "makes the villa notice" if result.success else "pushes too hard"
        return f"Your bold flirt with {target_id} {outcome}."
    if result.action.kind is ActionKind.LISTEN:
        target_id = result.action.target_id or "someone"
        return f"You give {target_id} the floor and let the moment breathe."
    if result.action.kind is ActionKind.LEAVE:
        return "You step away before the chat turns stale."
    if result.action.kind is ActionKind.ADVANCE_PHASE:
        return f"The villa moves into {state.phase.value}."
    if result.action.kind is ActionKind.MOVE:
        return f"You head over to {state.location_id.value}."
    return "The villa shifts around your choice."


def _load_dotenv_local(path: Path = Path(".env.local")) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())
