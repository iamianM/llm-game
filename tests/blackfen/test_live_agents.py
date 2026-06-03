from types import SimpleNamespace

import pytest

from src.blackfen.agents.intent import IntentParseOutput, OpenAIIntentParser
from src.blackfen.agents.narrator import NarrationOutput, OpenAINarrator, _validate_narration
from src.blackfen.engine import resolve_intent
from src.blackfen.models import Intent, IntentKind
from src.blackfen.new_game import new_game
from src.blackfen.rng import SeededRng


class FakeResponses:
    def __init__(self, output: object) -> None:
        self.output = output
        self.kwargs: dict[str, object] | None = None

    def parse(self, **kwargs: object) -> object:
        self.kwargs = kwargs
        return SimpleNamespace(output_parsed=self.output, id="resp_fake", status="completed", output=[])


def test_openai_intent_parser_uses_structured_response() -> None:
    fake = FakeResponses(IntentParseOutput(kind=IntentKind.TRAVEL, raw_text="go north road", target_id="north_road"))
    parser = OpenAIIntentParser()
    parser.__dict__["_client"] = SimpleNamespace(responses=fake)

    intent = parser.parse(new_game(42), "go north road")

    assert intent.kind is IntentKind.TRAVEL
    assert intent.target_id == "north_road"
    assert fake.kwargs is not None
    assert fake.kwargs["text_format"] is IntentParseOutput


def test_openai_narrator_uses_structured_response() -> None:
    state = new_game(42)
    result = resolve_intent(state, Intent(kind=IntentKind.INSPECT, raw_text="look around"), SeededRng(42))
    fake = FakeResponses(NarrationOutput(narration="You study the muddy square while rain ticks against the inn sign."))
    narrator = OpenAINarrator()
    narrator.__dict__["_client"] = SimpleNamespace(responses=fake)

    narration = narrator.narrate(state, result)

    assert "rain" in narration
    assert fake.kwargs is not None
    assert fake.kwargs["text_format"] is NarrationOutput


def test_blackfen_narrator_rejects_engine_tokens() -> None:
    with pytest.raises(ValueError, match="engine token"):
        _validate_narration("The target_id glows beside the run_status marker.")
