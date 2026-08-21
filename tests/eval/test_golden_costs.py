from src.game.eval.golden_costs import summarize_call, summarize_calls


def test_luna_cost_uses_observed_usage_and_saved_price_snapshot() -> None:
    call = summarize_call(
        "gpt-5.6-luna",
        {
            "input_tokens": 100_000,
            "cached_input_tokens": 20_000,
            "cache_write_tokens": 10_000,
            "output_tokens": 5_000,
            "reasoning_tokens": 1_000,
            "total_tokens": 105_000,
        },
    )

    assert call.cost.kind == "exact"
    assert call.cost.input_usd == 0.014
    assert call.cost.cached_input_usd == 0.0004
    assert call.cost.cache_write_usd == 0.0025
    assert call.cost.output_usd == 0.006
    assert call.cost.total_usd == 0.0229
    assert call.cost.pricing_as_of == "2026-08-21"


def test_cost_rollup_keeps_game_and_judge_usage_additive() -> None:
    first = summarize_call(
        "gpt-5.6-luna",
        {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120},
    )
    second = summarize_call(
        "gpt-5.6-luna",
        {"input_tokens": 200, "output_tokens": 30, "total_tokens": 230},
    )

    total = summarize_calls([first, second])

    assert total.usage.input_tokens == 300
    assert total.usage.output_tokens == 50
    assert total.usage.total_tokens == 350
    assert total.cost.kind == "exact"
    assert total.cost.total_usd == first.cost.total_usd + second.cost.total_usd


def test_total_only_historical_usage_is_reported_as_a_range() -> None:
    call = summarize_call("gpt-5.6-luna", {"total_tokens": 440_334})

    assert call.cost.kind == "range"
    assert call.cost.minimum_usd == 0.0880668
    assert call.cost.maximum_usd == 0.5284008
