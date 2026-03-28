from __future__ import annotations

from statistics import median
from typing import Any


def ema(values: list[float], period: int) -> list[float | None]:
    if period <= 0:
        raise ValueError("period must be positive")
    if not values:
        return []

    alpha = 2 / (period + 1)
    output: list[float | None] = [None] * len(values)
    running: float | None = None

    for index, value in enumerate(values):
        if running is None:
            running = float(value)
        else:
            running = (float(value) * alpha) + (running * (1 - alpha))
        output[index] = running
    return output


def rolling_median(values: list[float], period: int) -> list[float | None]:
    if period <= 0:
        raise ValueError("period must be positive")

    output: list[float | None] = []
    for index in range(len(values)):
        start = max(0, index - period + 1)
        window = values[start : index + 1]
        output.append(float(median(window)) if window else None)
    return output


def rsi(values: list[float], period: int = 14) -> list[float | None]:
    if period <= 0:
        raise ValueError("period must be positive")
    if not values:
        return []

    gains = [0.0]
    losses = [0.0]
    for index in range(1, len(values)):
        change = float(values[index]) - float(values[index - 1])
        gains.append(max(change, 0.0))
        losses.append(abs(min(change, 0.0)))

    output: list[float | None] = [None] * len(values)
    avg_gain = 0.0
    avg_loss = 0.0
    for index in range(1, len(values)):
        if index <= period:
            avg_gain += gains[index]
            avg_loss += losses[index]
            if index == period:
                avg_gain /= period
                avg_loss /= period
        else:
            avg_gain = ((avg_gain * (period - 1)) + gains[index]) / period
            avg_loss = ((avg_loss * (period - 1)) + losses[index]) / period

        if index < period:
            continue
        if avg_loss == 0:
            output[index] = 100.0
            continue
        rs = avg_gain / avg_loss
        output[index] = 100 - (100 / (1 + rs))
    return output


def true_range(
    highs: list[float],
    lows: list[float],
    closes: list[float],
) -> list[float]:
    output: list[float] = []
    for index, (high_value, low_value, close_value) in enumerate(zip(highs, lows, closes, strict=False)):
        if index == 0:
            output.append(float(high_value) - float(low_value))
            continue
        current_high = float(high_value)
        current_low = float(low_value)
        previous_close = float(closes[index - 1])
        output.append(
            max(
                current_high - current_low,
                abs(current_high - previous_close),
                abs(current_low - previous_close),
            )
        )
    return output


def atr(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int = 14,
) -> list[float | None]:
    if period <= 0:
        raise ValueError("period must be positive")
    if not highs:
        return []

    ranges = true_range(highs, lows, closes)
    output: list[float | None] = [None] * len(ranges)
    running = 0.0

    for index, value in enumerate(ranges):
        if index < period:
            running += value
            if index == period - 1:
                running /= period
                output[index] = running
            continue
        running = ((running * (period - 1)) + value) / period
        output[index] = running
    return output


def macd(
    values: list[float],
    *,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    fast = ema(values, fast_period)
    slow = ema(values, slow_period)
    line: list[float | None] = []
    for fast_value, slow_value in zip(fast, slow, strict=False):
        if fast_value is None or slow_value is None:
            line.append(None)
        else:
            line.append(fast_value - slow_value)

    line_filled = [value if value is not None else 0.0 for value in line]
    signal = ema(line_filled, signal_period)
    histogram: list[float | None] = []
    for line_value, signal_value in zip(line, signal, strict=False):
        if line_value is None or signal_value is None:
            histogram.append(None)
        else:
            histogram.append(line_value - signal_value)
    return line, signal, histogram


def indicator_snapshot(candle: dict[str, Any]) -> dict[str, float | None]:
    return {
        "ema20": candle.get("ema20"),
        "ema50": candle.get("ema50"),
        "rsi14": candle.get("rsi14"),
        "macd": candle.get("macd_line"),
        "macd_signal": candle.get("macd_signal"),
        "macd_hist": candle.get("macd_hist"),
        "atr14": candle.get("atr14"),
        "volume_median_20": candle.get("volume_median_20"),
        "traded_value_median_20": candle.get("traded_value_median_20"),
    }


def enrich_candles(candles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not candles:
        return []

    enriched = [dict(item) for item in candles]
    closes = [float(item["close"]) for item in enriched]
    highs = [float(item["high"]) for item in enriched]
    lows = [float(item["low"]) for item in enriched]
    volumes = [float(item.get("volume") or 0) for item in enriched]
    traded_values = [float(item.get("traded_value") or 0.0) for item in enriched]

    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50)
    rsi14 = rsi(closes, 14)
    atr14 = atr(highs, lows, closes, 14)
    macd_line, macd_signal, macd_hist = macd(closes)
    volume_median = rolling_median(volumes, 20)
    traded_value_median = rolling_median(traded_values, 20)

    for index, candle in enumerate(enriched):
        candle["ema20"] = ema20[index]
        candle["ema50"] = ema50[index]
        candle["rsi14"] = rsi14[index]
        candle["atr14"] = atr14[index]
        candle["macd_line"] = macd_line[index]
        candle["macd_signal"] = macd_signal[index]
        candle["macd_hist"] = macd_hist[index]
        candle["volume_median_20"] = volume_median[index]
        candle["traded_value_median_20"] = traded_value_median[index]
    return enriched
