from __future__ import annotations

from statistics import median
from typing import Any


def _float(value: Any, fallback: float = 0.0) -> float:
    try:
        if value is None:
            return fallback
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _bullish_candle(candle: dict[str, Any]) -> bool:
    open_price = _float(candle.get("open"))
    close_price = _float(candle.get("close"))
    high_price = _float(candle.get("high"))
    low_price = _float(candle.get("low"))
    candle_range = max(high_price - low_price, close_price * 0.001)
    return close_price > open_price and close_price >= high_price - (candle_range * 0.35)


def _bearish_candle(candle: dict[str, Any]) -> bool:
    open_price = _float(candle.get("open"))
    close_price = _float(candle.get("close"))
    high_price = _float(candle.get("high"))
    low_price = _float(candle.get("low"))
    candle_range = max(high_price - low_price, close_price * 0.001)
    return close_price < open_price and close_price <= low_price + (candle_range * 0.35)


def _pivot_lows(candles: list[dict[str, Any]], end_index: int, lookback: int = 25) -> list[int]:
    start = max(2, end_index - lookback)
    pivots: list[int] = []
    for index in range(start, end_index):
        current_low = _float(candles[index].get("low"))
        if current_low <= _float(candles[index - 1].get("low")) and current_low <= _float(candles[index + 1].get("low")):
            pivots.append(index)
    return pivots


def _pivot_highs(candles: list[dict[str, Any]], end_index: int, lookback: int = 25) -> list[int]:
    start = max(2, end_index - lookback)
    pivots: list[int] = []
    for index in range(start, end_index):
        current_high = _float(candles[index].get("high"))
        if current_high >= _float(candles[index - 1].get("high")) and current_high >= _float(candles[index + 1].get("high")):
            pivots.append(index)
    return pivots


def _detect_label(candles: list[dict[str, Any]], index: int, pattern_label: str) -> bool:
    if index < 40:
        return False

    current = candles[index]
    previous = candles[index - 1]
    close_price = _float(current.get("close"))
    atr_value = max(_float(current.get("atr14")), close_price * 0.01)
    buffer = max(atr_value * 0.25, close_price * 0.003)
    volume_median = _float(current.get("volume_median_20"))
    volume_confirmed = volume_median > 0 and _float(current.get("volume")) >= volume_median * 1.5
    trailing = candles[max(0, index - 40) : index]
    trailing_high = max((_float(item.get("high")) for item in trailing), default=0.0)
    trailing_low = min((_float(item.get("low")) for item in trailing), default=0.0)
    recent_three = candles[max(0, index - 2) : index + 1]

    if pattern_label == "Bullish Breakout":
        return close_price > trailing_high + buffer and volume_confirmed

    if pattern_label == "Bearish Breakdown":
        return close_price < trailing_low - buffer and volume_confirmed

    if pattern_label == "Bullish Reversal at Support":
        return (
            _float(current.get("low")) <= trailing_low + buffer
            and _bullish_candle(current)
            and _float(current.get("rsi14")) >= _float(previous.get("rsi14"))
        )

    if pattern_label == "Bearish Reversal at Resistance":
        return (
            _float(current.get("high")) >= trailing_high - buffer
            and _bearish_candle(current)
            and _float(current.get("rsi14")) <= _float(previous.get("rsi14"))
        )

    if pattern_label == "Support Bounce":
        support_touched = any(_float(item.get("low")) <= trailing_low + buffer for item in recent_three)
        return support_touched and close_price > _float(previous.get("close"))

    if pattern_label == "Resistance Rejection":
        resistance_touched = any(_float(item.get("high")) >= trailing_high - buffer for item in recent_three)
        return resistance_touched and close_price < _float(previous.get("close"))

    if pattern_label == "Bullish Divergence":
        pivots = _pivot_lows(candles, index)
        if len(pivots) < 2:
            return False
        left = candles[pivots[-2]]
        right = candles[pivots[-1]]
        return (
            _float(right.get("low")) < _float(left.get("low"))
            and (
                _float(right.get("rsi14")) > _float(left.get("rsi14")) + 2
                or _float(right.get("macd_hist")) > _float(left.get("macd_hist"))
            )
            and close_price > _float(previous.get("close"))
        )

    if pattern_label == "Bearish Divergence":
        pivots = _pivot_highs(candles, index)
        if len(pivots) < 2:
            return False
        left = candles[pivots[-2]]
        right = candles[pivots[-1]]
        return (
            _float(right.get("high")) > _float(left.get("high"))
            and (
                _float(right.get("rsi14")) < _float(left.get("rsi14")) - 2
                or _float(right.get("macd_hist")) < _float(left.get("macd_hist"))
            )
            and close_price < _float(previous.get("close"))
        )

    return False


def _future_outcome(
    candles: list[dict[str, Any]],
    index: int,
    *,
    direction: str,
    horizon_days: int,
) -> tuple[bool, float]:
    entry = candles[index]
    entry_close = _float(entry.get("close"))
    atr_value = max(_float(entry.get("atr14")), entry_close * 0.01)
    target = entry_close + atr_value if direction == "bullish" else entry_close - atr_value
    stop = entry_close - atr_value if direction == "bullish" else entry_close + atr_value

    future = candles[index + 1 : index + horizon_days + 1]
    for candle in future:
        high_price = _float(candle.get("high"))
        low_price = _float(candle.get("low"))
        if direction == "bullish":
            if high_price >= target and low_price <= stop:
                return False, (_float(candle.get("close")) - entry_close) / entry_close
            if high_price >= target:
                return True, (target - entry_close) / entry_close
            if low_price <= stop:
                return False, (stop - entry_close) / entry_close
        else:
            if low_price <= target and high_price >= stop:
                return False, (entry_close - _float(candle.get("close"))) / entry_close
            if low_price <= target:
                return True, (entry_close - target) / entry_close
            if high_price >= stop:
                return False, (entry_close - stop) / entry_close

    final_close = _float(future[-1].get("close")) if future else entry_close
    if direction == "bullish":
        forward_return = (final_close - entry_close) / entry_close if entry_close else 0.0
    else:
        forward_return = (entry_close - final_close) / entry_close if entry_close else 0.0
    return forward_return > 0, forward_return


def pattern_family_for_label(pattern_label: str) -> str:
    mapping = {
        "Bullish Breakout": "breakout",
        "Bearish Breakdown": "breakout",
        "Bullish Reversal at Support": "reversal",
        "Bearish Reversal at Resistance": "reversal",
        "Support Bounce": "reversal",
        "Resistance Rejection": "reversal",
        "Bullish Divergence": "divergence",
        "Bearish Divergence": "divergence",
    }
    return mapping.get(pattern_label, "pattern")


def direction_for_label(pattern_label: str) -> str:
    return "bearish" if pattern_label in {"Bearish Breakdown", "Bearish Reversal at Resistance", "Resistance Rejection", "Bearish Divergence"} else "bullish"


def backtest_pattern(
    candles: list[dict[str, Any]],
    pattern_label: str,
    *,
    horizon_days: int,
    min_sample_size: int,
) -> dict[str, Any]:
    if len(candles) < 80:
        return {
            "pattern_label": pattern_label,
            "pattern_family": pattern_family_for_label(pattern_label),
            "sample_size": 0,
            "wins": 0,
            "losses": 0,
            "success_rate": None,
            "avg_forward_return": None,
            "median_forward_return": None,
            "horizon_days": horizon_days,
            "reliability": "insufficient_history",
        }

    direction = direction_for_label(pattern_label)
    forward_returns: list[float] = []
    wins = 0
    losses = 0
    sample_size = 0

    for index in range(40, len(candles) - horizon_days - 1):
        if not _detect_label(candles, index, pattern_label):
            continue
        sample_size += 1
        success, forward_return = _future_outcome(
            candles,
            index,
            direction=direction,
            horizon_days=horizon_days,
        )
        forward_returns.append(forward_return)
        if success:
            wins += 1
        else:
            losses += 1

    success_rate = round((wins / sample_size) * 100, 1) if sample_size else None
    reliability = "ok" if sample_size >= min_sample_size else "low_sample"
    return {
        "pattern_label": pattern_label,
        "pattern_family": pattern_family_for_label(pattern_label),
        "sample_size": sample_size,
        "wins": wins,
        "losses": losses,
        "success_rate": success_rate,
        "avg_forward_return": round((sum(forward_returns) / sample_size) * 100, 2) if sample_size else None,
        "median_forward_return": round(median(forward_returns) * 100, 2) if sample_size else None,
        "horizon_days": horizon_days,
        "reliability": reliability,
        "target_rule": "+1 ATR before -1 ATR" if direction == "bullish" else "-1 ATR before +1 ATR",
    }


def build_family_baselines(backtests: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for backtest in backtests:
        family = str(backtest.get("pattern_family") or "pattern")
        grouped.setdefault(family, []).append(backtest)

    baselines: dict[str, dict[str, Any]] = {}
    for family, items in grouped.items():
        sample_size = sum(int(item.get("sample_size") or 0) for item in items)
        wins = sum(int(item.get("wins") or 0) for item in items)
        if sample_size <= 0:
            continue
        returns = [float(item.get("avg_forward_return") or 0.0) for item in items if item.get("avg_forward_return") is not None]
        baselines[family] = {
            "pattern_family": family,
            "sample_size": sample_size,
            "wins": wins,
            "losses": sample_size - wins,
            "success_rate": round((wins / sample_size) * 100, 1),
            "avg_forward_return": round(sum(returns) / len(returns), 2) if returns else None,
            "horizon_days": max(int(item.get("horizon_days") or 0) for item in items),
            "reliability": "baseline",
        }
    return baselines
