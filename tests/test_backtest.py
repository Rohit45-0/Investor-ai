from __future__ import annotations

from tests.conftest import build_enriched_candles

from app.chart.backtest import backtest_pattern, build_family_baselines


def test_backtest_pattern_returns_stock_specific_stats() -> None:
    closes = []
    special_volumes = {}
    for cycle in range(8):
        base = 100 + (cycle * 4)
        closes.extend([base + 0.1, base + 0.2, base + 0.15, base + 0.25, base + 0.2, base + 0.15, base + 0.3, base + 0.25])
        breakout_index = len(closes)
        closes.extend([base + 3.8, base + 5.2, base + 5.6, base + 5.8])
        special_volumes[breakout_index] = 420_000

    candles = build_enriched_candles(closes, special_volumes=special_volumes)
    result = backtest_pattern(
        candles,
        "Bullish Breakout",
        horizon_days=7,
        min_sample_size=2,
    )

    assert result["sample_size"] >= 2
    assert result["wins"] >= 1
    assert result["success_rate"] is not None
    assert result["reliability"] == "ok"


def test_family_baselines_aggregate_samples() -> None:
    baselines = build_family_baselines(
        [
            {
                "pattern_family": "breakout",
                "sample_size": 4,
                "wins": 3,
                "horizon_days": 7,
                "avg_forward_return": 2.4,
            },
            {
                "pattern_family": "breakout",
                "sample_size": 6,
                "wins": 4,
                "horizon_days": 7,
                "avg_forward_return": 1.8,
            },
        ]
    )

    assert baselines["breakout"]["sample_size"] == 10
    assert baselines["breakout"]["wins"] == 7
    assert baselines["breakout"]["success_rate"] == 70.0
