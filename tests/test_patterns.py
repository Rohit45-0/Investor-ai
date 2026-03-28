from __future__ import annotations

from tests.conftest import build_enriched_candles

from app.chart.patterns import detect_patterns


def test_detects_bullish_breakout() -> None:
    closes = [100 + ((index % 4) * 0.15) for index in range(68)] + [100.4, 104.8]
    candles = build_enriched_candles(closes, special_volumes={69: 320_000})
    levels = {
        "support": [{"price": 98.9, "lower": 98.6, "upper": 99.2, "strength": 66}],
        "resistance": [{"price": 101.0, "lower": 100.8, "upper": 101.1, "strength": 84}],
        "pivots": {"highs": [], "lows": []},
    }

    patterns = detect_patterns(candles, timeframe="5m", levels=levels)

    assert any(item["pattern_label"] == "Bullish Breakout" for item in patterns)


def test_detects_support_bounce() -> None:
    closes = [101 + ((index % 3) * 0.08) for index in range(67)] + [100.2, 100.4, 101.6]
    candles = build_enriched_candles(closes)
    candles[-3]["low"] = 99.9
    candles[-2]["low"] = 100.0
    levels = {
        "support": [{"price": 100.2, "lower": 99.9, "upper": 100.5, "strength": 78}],
        "resistance": [{"price": 102.6, "lower": 102.3, "upper": 102.8, "strength": 55}],
        "pivots": {"highs": [], "lows": []},
    }

    patterns = detect_patterns(candles, timeframe="1d", levels=levels)

    assert any(item["pattern_label"] == "Support Bounce" for item in patterns)


def test_detects_bullish_divergence() -> None:
    closes = [106 - (index * 0.1) for index in range(70)]
    candles = build_enriched_candles(closes)
    candles[58]["low"] = 95.0
    candles[63]["low"] = 93.8
    candles[58]["rsi14"] = 28.0
    candles[63]["rsi14"] = 35.0
    candles[58]["macd_hist"] = -1.8
    candles[63]["macd_hist"] = -0.9
    candles[-2]["close"] = 96.1
    candles[-1]["close"] = 97.2
    levels = {
        "support": [{"price": 94.2, "lower": 93.7, "upper": 94.7, "strength": 71}],
        "resistance": [{"price": 99.9, "lower": 99.5, "upper": 100.2, "strength": 52}],
        "pivots": {
            "highs": [],
            "lows": [
                {"index": 58, "price": 95.0},
                {"index": 63, "price": 93.8},
            ],
        },
    }

    patterns = detect_patterns(candles, timeframe="1d", levels=levels)

    assert any(item["pattern_label"] == "Bullish Divergence" for item in patterns)


def test_returns_no_signal_for_quiet_series() -> None:
    closes = [100 + ((index % 2) * 0.02) for index in range(75)]
    candles = build_enriched_candles(closes)
    levels = {
        "support": [{"price": 92.0, "lower": 91.5, "upper": 92.5, "strength": 40}],
        "resistance": [{"price": 108.0, "lower": 107.5, "upper": 108.5, "strength": 40}],
        "pivots": {"highs": [], "lows": []},
    }

    patterns = detect_patterns(candles, timeframe="1d", levels=levels)

    assert patterns == []
