"""Tests for live-agent runtime settings and trace capture."""

from __future__ import annotations

from dataclasses import dataclass

from src.game.agents.runtime import (
    GAME_AGENT_MODEL,
    JUDGE_PROFILE,
    ORCHESTRATOR_PROFILE,
    VOICE_PROFILE,
    AgentTrace,
    begin_agent_attempt,
    begin_agent_trace_capture,
    end_agent_attempt,
    end_agent_trace_capture,
    extract_reasoning_summaries,
    mark_agent_trace_generation_error,
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


def test_reasoning_request_kwargs_use_low_default_and_allow_role_effort() -> None:
    kwargs = reasoning_request_kwargs()

    assert kwargs["reasoning"] == {"effort": "low", "summary": "detailed"}
    assert kwargs["include"] == ["reasoning.encrypted_content"]
    assert (
        reasoning_request_kwargs(effort=VOICE_PROFILE.reasoning_effort)["reasoning"]["effort"]
        == "medium"
    )
    assert JUDGE_PROFILE.reasoning_effort == "medium"
    assert ORCHESTRATOR_PROFILE.reasoning_effort == "medium"


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
            agent_name="heartbreaker_voice",
            model=GAME_AGENT_MODEL,
            prompt_path="src/game/agents/prompts/heartbreaker_voice.md",
            response=response,
            output={"npc_tone": "warm"},
        )
    finally:
        end_agent_attempt(attempt_token)
    traces = end_agent_trace_capture(token)

    assert len(traces) == 1
    assert traces[0].attempt == 2
    assert traces[0].model == "gpt-5.6-luna"
    assert traces[0].reasoning_effort == "low"
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


def test_generation_retry_is_distinct_from_validation_failure() -> None:
    token = begin_agent_trace_capture()
    try:
        mark_agent_trace_generation_error(
            "conversation_curator",
            1,
            TimeoutError("Request timed out."),
        )
    finally:
        traces = end_agent_trace_capture(token)

    assert traces[0].generation_error == "Request timed out."
    assert traces[0].validation_error is None


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
            agent_name="resort_orchestrator",
            model=GAME_AGENT_MODEL,
            prompt_path="src/game/agents/prompts/resort_orchestrator.md",
            response=response,
            output=None,
        )
    finally:
        traces = end_agent_trace_capture(token)

    trace = traces[0]
    assert trace.output_type == "raw_response_output"
    assert trace.output == [
        {"type": "reasoning", "status": "", "summary": ["Needed more time."], "text": []}
    ]


def test_record_agent_trace_captures_prompt_input_latency_and_usage() -> None:
    token = begin_agent_trace_capture()
    try:
        response = type(
            "UsageResponse",
            (),
            {
                "id": "resp_usage",
                "output": [],
                "usage": {
                    "input_tokens": 120,
                    "output_tokens": 30,
                    "total_tokens": 150,
                    "input_tokens_details": {"cached_tokens": 80},
                    "output_tokens_details": {"reasoning_tokens": 12},
                },
            },
        )()
        record_agent_trace(
            agent_name="contextual_options",
            model=GAME_AGENT_MODEL,
            prompt_path="src/game/agents/prompts/contextual_options.md",
            response=response,
            output={"options": []},
            prompt_text="instructions",
            input_payload={"target": "chloe"},
            started_at=0.0,
        )
    finally:
        traces = end_agent_trace_capture(token)

    trace = traces[0]
    assert trace.prompt_sha256 == "238fa28a94976c7da14563bc873c2729bd5cd325389085bb4c6dd0de28923590"
    assert trace.input == {"target": "chloe"}
    assert trace.latency_ms is not None
    assert trace.usage is not None
    assert trace.usage.total_tokens == 150
    assert trace.usage.cached_input_tokens == 80
    assert trace.usage.reasoning_tokens == 12
