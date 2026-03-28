from __future__ import annotations

from app.chart.indicators import atr, ema, macd, rsi


def test_indicator_lengths_and_basic_values() -> None:
    closes = [100 + (index * 0.8) for index in range(40)]
    highs = [value + 1.0 for value in closes]
    lows = [value - 1.0 for value in closes]

    ema_values = ema(closes, 10)
    rsi_values = rsi(closes, 14)
    atr_values = atr(highs, lows, closes, 14)
    macd_line, macd_signal, macd_hist = macd(closes)

    assert len(ema_values) == len(closes)
    assert len(rsi_values) == len(closes)
    assert len(atr_values) == len(closes)
    assert len(macd_line) == len(closes)
    assert len(macd_signal) == len(closes)
    assert len(macd_hist) == len(closes)
    assert ema_values[-1] is not None
    assert rsi_values[-1] is not None and rsi_values[-1] > 50
    assert atr_values[-1] is not None and atr_values[-1] > 0
    assert macd_line[-1] is not None
