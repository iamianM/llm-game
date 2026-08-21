"""Observed token usage and price-snapshotted eval cost estimates."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Literal

from pydantic import BaseModel, ConfigDict


class UsageSummary(BaseModel):
    """Observed Responses API usage summed across model calls."""

    model_config = ConfigDict(extra="forbid")

    input_tokens: int = 0
    cached_input_tokens: int = 0
    cache_write_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0


class CostSummary(BaseModel):
    """Estimated USD cost using the price snapshot stored with the run."""

    model_config = ConfigDict(extra="forbid")

    currency: Literal["USD"] = "USD"
    kind: Literal["exact", "range", "unavailable"]
    total_usd: float | None = None
    minimum_usd: float | None = None
    maximum_usd: float | None = None
    input_usd: float | None = None
    cached_input_usd: float | None = None
    cache_write_usd: float | None = None
    output_usd: float | None = None
    input_rate_per_million: float | None = None
    cached_input_rate_per_million: float | None = None
    cache_write_rate_per_million: float | None = None
    output_rate_per_million: float | None = None
    pricing_source: str
    pricing_as_of: str


class CallCost(BaseModel):
    """One call's observed usage and estimated cost."""

    model_config = ConfigDict(extra="forbid")

    usage: UsageSummary
    cost: CostSummary


class RunAccounting(BaseModel):
    """Game-agent, judge, and total accounting stored with one eval run."""

    model_config = ConfigDict(extra="forbid")

    game_agents: CallCost
    judges: CallCost
    total: CallCost


_LUNA = {
    "input": 0.20,
    "cached_input": 0.02,
    "cache_write": 0.25,
    "output": 1.20,
}
_SOURCE = "https://developers.openai.com/api/docs/models/gpt-5.6-luna"
_AS_OF = "2026-08-21"


def summarize_call(model: str | None, raw: Mapping[str, object]) -> CallCost:
    """Normalize one trace and attach the matching price snapshot."""
    usage = UsageSummary(
        input_tokens=_token(raw, "input_tokens"),
        cached_input_tokens=_token(raw, "cached_input_tokens"),
        cache_write_tokens=_token(raw, "cache_write_tokens"),
        output_tokens=_token(raw, "output_tokens"),
        reasoning_tokens=_token(raw, "reasoning_tokens"),
        total_tokens=_token(raw, "total_tokens"),
    )
    if _model_key(model) != "gpt-5.6-luna":
        return CallCost(
            usage=usage,
            cost=CostSummary(
                kind="unavailable",
                pricing_source=_SOURCE,
                pricing_as_of=_AS_OF,
            ),
        )
    has_split = isinstance(raw.get("input_tokens"), int) and isinstance(
        raw.get("output_tokens"), int
    )
    if not has_split:
        return CallCost(
            usage=usage,
            cost=_range_cost(usage.total_tokens),
        )
    cached = min(usage.cached_input_tokens, usage.input_tokens)
    writes = min(usage.cache_write_tokens, max(usage.input_tokens - cached, 0))
    uncached = max(usage.input_tokens - cached - writes, 0)
    multiplier_in, multiplier_out = _long_context_multipliers(usage.input_tokens)
    input_usd = _million_cost(uncached, _LUNA["input"] * multiplier_in)
    cached_usd = _million_cost(cached, _LUNA["cached_input"] * multiplier_in)
    write_usd = _million_cost(writes, _LUNA["cache_write"] * multiplier_in)
    output_usd = _million_cost(usage.output_tokens, _LUNA["output"] * multiplier_out)
    return CallCost(
        usage=usage,
        cost=CostSummary(
            kind="exact",
            total_usd=_rounded(input_usd + cached_usd + write_usd + output_usd),
            input_usd=_rounded(input_usd),
            cached_input_usd=_rounded(cached_usd),
            cache_write_usd=_rounded(write_usd),
            output_usd=_rounded(output_usd),
            pricing_source=_SOURCE,
            pricing_as_of=_AS_OF,
            **_rate_fields(),
        ),
    )


def summarize_calls(calls: Iterable[CallCost]) -> CallCost:
    """Sum call-level usage and costs without hiding incomplete pricing."""
    entries = list(calls)
    usage = UsageSummary(
        input_tokens=sum(entry.usage.input_tokens for entry in entries),
        cached_input_tokens=sum(entry.usage.cached_input_tokens for entry in entries),
        cache_write_tokens=sum(entry.usage.cache_write_tokens for entry in entries),
        output_tokens=sum(entry.usage.output_tokens for entry in entries),
        reasoning_tokens=sum(entry.usage.reasoning_tokens for entry in entries),
        total_tokens=sum(entry.usage.total_tokens for entry in entries),
    )
    if not entries:
        return CallCost(
            usage=usage,
            cost=CostSummary(kind="unavailable", pricing_source=_SOURCE, pricing_as_of=_AS_OF),
        )
    if all(entry.cost.kind == "exact" for entry in entries):
        return CallCost(
            usage=usage,
            cost=CostSummary(
                kind="exact",
                total_usd=_sum(entries, "total_usd"),
                input_usd=_sum(entries, "input_usd"),
                cached_input_usd=_sum(entries, "cached_input_usd"),
                cache_write_usd=_sum(entries, "cache_write_usd"),
                output_usd=_sum(entries, "output_usd"),
                pricing_source=_SOURCE,
                pricing_as_of=_AS_OF,
                **_rate_fields(),
            ),
        )
    if all(entry.cost.kind in {"exact", "range"} for entry in entries):
        minimum = sum(
            entry.cost.total_usd
            if entry.cost.kind == "exact"
            else entry.cost.minimum_usd or 0
            for entry in entries
        )
        maximum = sum(
            entry.cost.total_usd
            if entry.cost.kind == "exact"
            else entry.cost.maximum_usd or 0
            for entry in entries
        )
        return CallCost(
            usage=usage,
            cost=CostSummary(
                kind="range",
                minimum_usd=_rounded(minimum),
                maximum_usd=_rounded(maximum),
                pricing_source=_SOURCE,
                pricing_as_of=_AS_OF,
                **_rate_fields(),
            ),
        )
    return CallCost(
        usage=usage,
        cost=CostSummary(kind="unavailable", pricing_source=_SOURCE, pricing_as_of=_AS_OF),
    )


def _range_cost(total_tokens: int) -> CostSummary:
    return CostSummary(
        kind="range",
        minimum_usd=_rounded(_million_cost(total_tokens, _LUNA["input"])),
        maximum_usd=_rounded(_million_cost(total_tokens, _LUNA["output"])),
        pricing_source=_SOURCE,
        pricing_as_of=_AS_OF,
        **_rate_fields(),
    )


def _long_context_multipliers(input_tokens: int) -> tuple[float, float]:
    return (2.0, 1.5) if input_tokens > 272_000 else (1.0, 1.0)


def _rate_fields() -> dict[str, float]:
    return {
        "input_rate_per_million": _LUNA["input"],
        "cached_input_rate_per_million": _LUNA["cached_input"],
        "cache_write_rate_per_million": _LUNA["cache_write"],
        "output_rate_per_million": _LUNA["output"],
    }


def _token(raw: Mapping[str, object], key: str) -> int:
    value = raw.get(key)
    return max(value, 0) if isinstance(value, int) and not isinstance(value, bool) else 0


def _model_key(model: str | None) -> str:
    return (model or "").split("/")[-1].strip().lower()


def _million_cost(tokens: int, rate: float) -> float:
    return tokens / 1_000_000 * rate


def _rounded(value: float) -> float:
    return round(value, 9)


def _sum(entries: list[CallCost], key: str) -> float:
    return _rounded(sum(float(getattr(entry.cost, key) or 0) for entry in entries))
