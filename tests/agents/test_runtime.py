"""Tests for live-agent runtime settings and trace capture."""

from __future__ import annotations

from dataclasses import dataclass

from src.game.agents.runtime import (
    GAME_AGENT_MODEL,
    AgentTrace,
    begin_agent_attempt,
    begin_agent_trace_capture,
    end_agent_attempt,
    end_agent_trace_capture,
    extract_reasoning_summaries,
    reasoning_request_kwargs,
    record_agent_trace,
)


@dataclass
class SummaryText:
    text: str


@dataclass
class ReasoningItem:
    id: str
    type: str
    summary: list[SummaryText]


@dataclass
class FakeResponse:
    id: str
    output: list[ReasoningItem]


def test_reasoning_request_kwargs_enable_high_summary_capture() -> None:
    kwargs = reasoning_request_kwargs()

    assert kwargs["reasoning"] == {"effort": "high", "summary": "detailed"}
    assert kwargs["include"] == ["reasoning.encrypted_content"]


def test_extract_reasoning_summaries_reads_response_output_items() -> None:
    response = FakeResponse(
        id="resp_1",
        output=[
            ReasoningItem(
                id="rs_1",
                type="reasoning",
                summary=[SummaryText("Checked the target mood before writing dialogue.")],
            )
        ],
    )

    summaries = extract_reasoning_summaries(response)

    assert summaries[0].item_id == "rs_1"
    assert summaries[0].texts == ["Checked the target mood before writing dialogue."]


def test_record_agent_trace_captures_attempt_model_output_and_reasoning() -> None:
    token = begin_agent_trace_capture()
    attempt_token = begin_agent_attempt(2)
    try:
        response = FakeResponse(
            id="resp_2",
            output=[
                ReasoningItem(
                    id="rs_2",
                    type="reasoning",
                    summary=[SummaryText("Retried after a validation issue.")],
                )
            ],
        )
        record_agent_trace(
            agent_name="islander_voice",
            model=GAME_AGENT_MODEL,
            prompt_path="src/game/agents/prompts/islander_voice.md",
            response=response,
            output={"npc_tone": "warm"},
        )
    finally:
        end_agent_attempt(attempt_token)
    traces = end_agent_trace_capture(token)

    assert len(traces) == 1
    assert traces[0].attempt == 2
    assert traces[0].model == "gpt-5.4-mini"
    assert traces[0].reasoning_effort == "high"
    assert traces[0].output == {"npc_tone": "warm"}
    assert traces[0].reasoning_summaries[0].texts == ["Retried after a validation issue."]


def test_record_agent_trace_captures_unparsed_response_text() -> None:
    token = begin_agent_trace_capture()
    try:
        response = type(
            "UnparsedResponse",
            (),
            {
                "id": "resp_unparsed",
                "status": "incomplete",
                "incomplete_details": {"reason": "max_output_tokens"},
                "output_text": '{"memories": [',
                "output": [],
            },
        )()
        record_agent_trace(
            agent_name="conversation_curator",
            model=GAME_AGENT_MODEL,
            prompt_path="src/game/agents/prompts/conversation_curator.md",
            response=response,
            output=None,
        )
    finally:
        traces = end_agent_trace_capture(token)

    trace = AgentTrace.model_validate(traces[0].model_dump(mode="json"))
    assert trace.response_status == "incomplete"
    assert "max_output_tokens" in (trace.response_details or "")
    assert trace.output_type == "raw_response_text"
    assert trace.output == '{"memories": ['


def test_record_agent_trace_sanitizes_unparsed_response_output_items() -> None:
    token = begin_agent_trace_capture()
    try:
        response = type(
            "UnparsedResponse",
            (),
            {
                "id": "resp_output",
                "status": "incomplete",
                "incomplete_details": {"reason": "max_output_tokens"},
                "output_text": "",
                "output": [
                    {
                        "type": "reasoning",
                        "summary": [{"text": "Needed more time."}],
                        "encrypted_content": "secret",
                    }
                ],
            },
        )()
        record_agent_trace(
            agent_name="villa_orchestrator",
            model=GAME_AGENT_MODEL,
            prompt_path="src/game/agents/prompts/villa_orchestrator.md",
            response=response,
            output=None,
        )
    finally:
        traces = end_agent_trace_capture(token)

    trace = traces[0]
    assert trace.output_type == "raw_response_output"
    assert trace.output == [{"type": "reasoning", "status": "", "summary": ["Needed more time."], "text": []}]
