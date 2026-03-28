from __future__ import annotations

from tests.conftest import build_candles

from app.chart.service import analyze_symbol_chart


class FakeProvider:
    def __init__(self, daily, intraday=None):
        self.daily = daily
        self.intraday = intraday if intraday is not None else daily[-80:]

    def fetch_candles(self, symbol, interval, *, lookback_days, data_root=None, force_refresh=False):
        return self.daily if interval == "1d" else self.intraday


def test_analyze_symbol_chart_marks_insufficient_history() -> None:
    provider = FakeProvider(build_candles([100 + (index * 0.2) for index in range(40)]))

    result = analyze_symbol_chart("TEST", company="Test Industries", provider=provider)

    assert result["summary"] is None
    assert result["chart_status"]["reason"] == "insufficient_history"


def test_analyze_symbol_chart_marks_illiquid_symbol() -> None:
    daily = build_candles(
        [100 + ((index % 5) * 0.15) for index in range(140)],
        default_volume=100,
    )
    provider = FakeProvider(daily)

    result = analyze_symbol_chart("TEST", company="Test Industries", provider=provider)

    assert result["summary"] is None
    assert result["chart_status"]["reason"] == "illiquid"


def test_analyze_symbol_chart_produces_summary_signal() -> None:
    daily_closes = [100 + ((index % 4) * 0.1) for index in range(130)] + [100.4, 104.6]
    intraday_closes = [101 + ((index % 3) * 0.07) for index in range(80)] + [101.2, 103.9]
    daily = build_candles(daily_closes, default_volume=180_000, special_volumes={131: 520_000})
    intraday = build_candles(intraday_closes, default_volume=90_000, special_volumes={81: 280_000})
    provider = FakeProvider(daily, intraday)

    result = analyze_symbol_chart("TEST", company="Test Industries", provider=provider)

    assert result["chart_status"]["reason"] == "ok"
    assert result["summary"] is not None
    assert result["summary"]["pattern_family"] in {"breakout", "reversal", "divergence"}
    assert result["summary"]["llm_explanation"]["summary"]
