from __future__ import annotations

from typing import Any

from .indicators import indicator_snapshot
from .levels import nearest_resistance, nearest_support


def _float(value: Any, fallback: float = 0.0) -> float:
    try:
        if value is None:
            return fallback
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _price_buffer(close_price: float, atr_value: float) -> float:
    return max(atr_value * 0.25, close_price * 0.003)


def _volume_confirmed(candle: dict[str, Any], multiple: float = 1.5) -> bool:
    median_volume = _float(candle.get("volume_median_20"))
    if median_volume <= 0:
        return False
    return _float(candle.get("volume")) >= median_volume * multiple


def _bullish_trend(candle: dict[str, Any]) -> bool:
    ema20 = _float(candle.get("ema20"))
    ema50 = _float(candle.get("ema50"))
    close_price = _float(candle.get("close"))
    return close_price > ema20 and ema20 >= ema50


def _bearish_trend(candle: dict[str, Any]) -> bool:
    ema20 = _float(candle.get("ema20"))
    ema50 = _float(candle.get("ema50"))
    close_price = _float(candle.get("close"))
    return close_price < ema20 and ema20 <= ema50


def _bullish_candle(candle: dict[str, Any]) -> bool:
    open_price = _float(candle.get("open"))
    high_price = _float(candle.get("high"))
    low_price = _float(candle.get("low"))
    close_price = _float(candle.get("close"))
    candle_range = max(high_price - low_price, close_price * 0.001)
    return close_price > open_price and close_price >= high_price - (candle_range * 0.35)


def _bearish_candle(candle: dict[str, Any]) -> bool:
    open_price = _float(candle.get("open"))
    high_price = _float(candle.get("high"))
    low_price = _float(candle.get("low"))
    close_price = _float(candle.get("close"))
    candle_range = max(high_price - low_price, close_price * 0.001)
    return close_price < open_price and close_price <= low_price + (candle_range * 0.35)


def _zone_hit(candle: dict[str, Any], zone: dict[str, Any], *, side: str, tolerance: float) -> bool:
    if side == "support":
        return _float(candle.get("low")) <= (_float(zone.get("upper")) + tolerance)
    return _float(candle.get("high")) >= (_float(zone.get("lower")) - tolerance)


def _movement_strength(candle: dict[str, Any]) -> float:
    high_price = _float(candle.get("high"))
    low_price = _float(candle.get("low"))
    close_price = _float(candle.get("close"))
    if close_price <= 0:
        return 0.0
    return (high_price - low_price) / close_price


def _score_pattern(
    *,
    family: str,
    direction: str,
    zone_strength: int,
    volume_confirmed: bool,
    trend_alignment: bool,
    reliability: float,
    movement_strength: float,
) -> tuple[int, int]:
    family_base = {
        "breakout": 56,
        "reversal": 50,
        "divergence": 52,
    }.get(family, 48)

    score = family_base
    score += min(18, int(zone_strength / 5))
    score += 12 if volume_confirmed else 0
    score += 8 if trend_alignment else 0
    score += min(10, int(reliability / 10))
    score += min(8, int(movement_strength * 100))
    if direction == "bearish":
        score += 1

    score = max(25, min(98, score))
    confidence = max(30, min(95, int((score * 0.7) + (reliability * 0.3))))
    return score, confidence


def _evidence(label: str, detail: str) -> dict[str, str]:
    return {"label": label, "detail": detail}


def _match(
    *,
    family: str,
    label: str,
    direction: str,
    timeframe: str,
    latest: dict[str, Any],
    support_levels: list[dict[str, Any]],
    resistance_levels: list[dict[str, Any]],
    evidence: list[dict[str, str]],
    reasons: list[str],
    zone_strength: int,
    volume_confirmed: bool,
    trend_alignment: bool,
    reliability: float,
) -> dict[str, Any]:
    score, confidence = _score_pattern(
        family=family,
        direction=direction,
        zone_strength=zone_strength,
        volume_confirmed=volume_confirmed,
        trend_alignment=trend_alignment,
        reliability=reliability,
        movement_strength=_movement_strength(latest),
    )
    return {
        "as_of": latest.get("timestamp"),
        "timeframe": timeframe,
        "pattern_family": family,
        "pattern_label": label,
        "direction": direction,
        "score": score,
        "confidence": confidence,
        "support_levels": support_levels,
        "resistance_levels": resistance_levels,
        "indicator_snapshot": indicator_snapshot(latest),
        "evidence": evidence,
        "reasons": reasons[:5],
        "volume_confirmed": volume_confirmed,
        "trend_alignment": trend_alignment,
        "zone_strength": zone_strength,
    }


def detect_patterns(
    candles: list[dict[str, Any]],
    *,
    timeframe: str,
    levels: dict[str, Any],
) -> list[dict[str, Any]]:
    if len(candles) < 60:
        return []

    latest = candles[-1]
    previous = candles[-2]
    current_close = _float(latest.get("close"))
    atr_value = max(_float(latest.get("atr14")), current_close * 0.01)
    buffer = _price_buffer(current_close, atr_value)
    support_levels = levels.get("support") or []
    resistance_levels = levels.get("resistance") or []
    support_zone = nearest_support(support_levels, current_close)
    resistance_zone = nearest_resistance(resistance_levels, current_close)
    volume_confirmed = _volume_confirmed(latest)
    bullish_trend = _bullish_trend(latest)
    bearish_trend = _bearish_trend(latest)
    momentum_up = _float(latest.get("rsi14")) >= max(42.0, _float(previous.get("rsi14")))
    momentum_down = _float(latest.get("rsi14")) <= min(58.0, _float(previous.get("rsi14"), 100.0))
    macd_hist_rising = _float(latest.get("macd_hist")) >= _float(previous.get("macd_hist"))
    macd_hist_falling = _float(latest.get("macd_hist")) <= _float(previous.get("macd_hist"))

    matches: list[dict[str, Any]] = []

    if resistance_zone:
        resistance_price = _float(resistance_zone.get("price"))
        if (
            _float(previous.get("close")) <= _float(resistance_zone.get("upper"))
            and current_close > _float(resistance_zone.get("upper")) + buffer
            and volume_confirmed
        ):
            matches.append(
                _match(
                    family="breakout",
                    label="Bullish Breakout",
                    direction="bullish",
                    timeframe=timeframe,
                    latest=latest,
                    support_levels=support_levels,
                    resistance_levels=resistance_levels,
                    evidence=[
                        _evidence(
                            "Trigger",
                            f"Closed above resistance {resistance_price:.2f} by more than {buffer:.2f}.",
                        ),
                        _evidence(
                            "Participation",
                            "Volume expanded above the 20-bar median.",
                        ),
                        _evidence(
                            "Context",
                            f"Resistance zone strength is {int(resistance_zone.get('strength') or 0)} / 100.",
                        ),
                    ],
                    reasons=[
                        "Price cleared a confirmed resistance zone with volume.",
                        "The move is sized beyond the ATR noise band.",
                        "A breakout can start a new swing leg if follow-through holds.",
                    ],
                    zone_strength=int(resistance_zone.get("strength") or 0),
                    volume_confirmed=True,
                    trend_alignment=bullish_trend,
                    reliability=62.0,
                )
            )

    if support_zone:
        support_price = _float(support_zone.get("price"))
        if (
            _float(previous.get("close")) >= _float(support_zone.get("lower"))
            and current_close < _float(support_zone.get("lower")) - buffer
            and volume_confirmed
        ):
            matches.append(
                _match(
                    family="breakout",
                    label="Bearish Breakdown",
                    direction="bearish",
                    timeframe=timeframe,
                    latest=latest,
                    support_levels=support_levels,
                    resistance_levels=resistance_levels,
                    evidence=[
                        _evidence(
                            "Trigger",
                            f"Closed below support {support_price:.2f} by more than {buffer:.2f}.",
                        ),
                        _evidence("Participation", "Volume expanded above the 20-bar median."),
                        _evidence(
                            "Context",
                            f"Support zone strength is {int(support_zone.get('strength') or 0)} / 100.",
                        ),
                    ],
                    reasons=[
                        "Price lost a confirmed support zone with volume.",
                        "The breakdown moved beyond the ATR noise band.",
                        "Broken support can become new overhead supply.",
                    ],
                    zone_strength=int(support_zone.get("strength") or 0),
                    volume_confirmed=True,
                    trend_alignment=bearish_trend,
                    reliability=61.0,
                )
            )

    if support_zone and _zone_hit(latest, support_zone, side="support", tolerance=buffer):
        bullish_reversal = _bullish_candle(latest) and (momentum_up or macd_hist_rising)
        if bullish_reversal:
            matches.append(
                _match(
                    family="reversal",
                    label="Bullish Reversal at Support",
                    direction="bullish",
                    timeframe=timeframe,
                    latest=latest,
                    support_levels=support_levels,
                    resistance_levels=resistance_levels,
                    evidence=[
                        _evidence("Support", f"Low tagged support near {_float(support_zone.get('price')):.2f}."),
                        _evidence("Candle", "Finished near the high of the bar after testing support."),
                        _evidence("Momentum", "RSI/MACD improved from the prior bar."),
                    ],
                    reasons=[
                        "Support held and buyers regained control into the close.",
                        "Momentum turned up at a recognized pivot zone.",
                        "Reversal setups work best when the next bars confirm above support.",
                    ],
                    zone_strength=int(support_zone.get("strength") or 0),
                    volume_confirmed=volume_confirmed,
                    trend_alignment=bullish_trend,
                    reliability=57.0,
                )
            )

        recent_support_touch = any(
            _zone_hit(candle, support_zone, side="support", tolerance=buffer)
            for candle in candles[-3:]
        )
        if recent_support_touch and current_close > _float(support_zone.get("upper")) and current_close > _float(previous.get("close")):
            matches.append(
                _match(
                    family="reversal",
                    label="Support Bounce",
                    direction="bullish",
                    timeframe=timeframe,
                    latest=latest,
                    support_levels=support_levels,
                    resistance_levels=resistance_levels,
                    evidence=[
                        _evidence("Support", f"Recent bars defended support near {_float(support_zone.get('price')):.2f}."),
                        _evidence("Recovery", "The latest close reclaimed the support zone."),
                        _evidence("Trend", "This is stronger when higher timeframes stay constructive."),
                    ],
                    reasons=[
                        "Repeated defense of support often attracts swing buyers.",
                        "The latest close suggests demand absorbed supply at the level.",
                        "The next hurdle is the nearest resistance zone above price.",
                    ],
                    zone_strength=int(support_zone.get("strength") or 0),
                    volume_confirmed=volume_confirmed,
                    trend_alignment=bullish_trend,
                    reliability=54.0,
                )
            )

    if resistance_zone and _zone_hit(latest, resistance_zone, side="resistance", tolerance=buffer):
        bearish_reversal = _bearish_candle(latest) and (momentum_down or macd_hist_falling)
        if bearish_reversal:
            matches.append(
                _match(
                    family="reversal",
                    label="Bearish Reversal at Resistance",
                    direction="bearish",
                    timeframe=timeframe,
                    latest=latest,
                    support_levels=support_levels,
                    resistance_levels=resistance_levels,
                    evidence=[
                        _evidence("Resistance", f"High tagged resistance near {_float(resistance_zone.get('price')):.2f}."),
                        _evidence("Candle", "Finished near the low of the bar after testing resistance."),
                        _evidence("Momentum", "RSI/MACD weakened from the prior bar."),
                    ],
                    reasons=[
                        "Resistance held and sellers took control into the close.",
                        "Momentum rolled over at a recognized supply zone.",
                        "Reversal setups are stronger when follow-through arrives quickly.",
                    ],
                    zone_strength=int(resistance_zone.get("strength") or 0),
                    volume_confirmed=volume_confirmed,
                    trend_alignment=bearish_trend,
                    reliability=57.0,
                )
            )

        recent_resistance_touch = any(
            _zone_hit(candle, resistance_zone, side="resistance", tolerance=buffer)
            for candle in candles[-3:]
        )
        if recent_resistance_touch and current_close < _float(resistance_zone.get("lower")) and current_close < _float(previous.get("close")):
            matches.append(
                _match(
                    family="reversal",
                    label="Resistance Rejection",
                    direction="bearish",
                    timeframe=timeframe,
                    latest=latest,
                    support_levels=support_levels,
                    resistance_levels=resistance_levels,
                    evidence=[
                        _evidence("Resistance", f"Recent bars failed near {_float(resistance_zone.get('price')):.2f}."),
                        _evidence("Rejection", "The latest close fell back under the zone."),
                        _evidence("Trend", "This setup improves when trend context is already weak."),
                    ],
                    reasons=[
                        "Repeated failure at resistance often signals distribution.",
                        "The latest close suggests sellers defended the level again.",
                        "A break of nearby support would strengthen the bearish case.",
                    ],
                    zone_strength=int(resistance_zone.get("strength") or 0),
                    volume_confirmed=volume_confirmed,
                    trend_alignment=bearish_trend,
                    reliability=54.0,
                )
            )

    pivot_lows = levels.get("pivots", {}).get("lows") or []
    if len(pivot_lows) >= 2:
        left = pivot_lows[-2]
        right = pivot_lows[-1]
        left_candle = candles[int(left["index"])]
        right_candle = candles[int(right["index"])]
        price_lower_low = _float(right["price"]) < _float(left["price"])
        rsi_higher_low = _float(right_candle.get("rsi14")) > _float(left_candle.get("rsi14")) + 2
        macd_higher_low = _float(right_candle.get("macd_hist")) > _float(left_candle.get("macd_hist"))
        if price_lower_low and (rsi_higher_low or macd_higher_low) and current_close > _float(previous.get("close")):
            matches.append(
                _match(
                    family="divergence",
                    label="Bullish Divergence",
                    direction="bullish",
                    timeframe=timeframe,
                    latest=latest,
                    support_levels=support_levels,
                    resistance_levels=resistance_levels,
                    evidence=[
                        _evidence("Price", "The latest pivot low undercut the prior pivot low."),
                        _evidence("Momentum", "RSI or MACD made a higher low during the same move."),
                        _evidence("Response", "The latest bar is starting to stabilize after the divergence."),
                    ],
                    reasons=[
                        "Momentum improved even while price printed a lower low.",
                        "Divergence often appears near exhaustion points.",
                        "Confirmation matters: the move still needs follow-through above nearby resistance.",
                    ],
                    zone_strength=int((support_zone or {}).get("strength") or 48),
                    volume_confirmed=volume_confirmed,
                    trend_alignment=bullish_trend,
                    reliability=55.0,
                )
            )

    pivot_highs = levels.get("pivots", {}).get("highs") or []
    if len(pivot_highs) >= 2:
        left = pivot_highs[-2]
        right = pivot_highs[-1]
        left_candle = candles[int(left["index"])]
        right_candle = candles[int(right["index"])]
        price_higher_high = _float(right["price"]) > _float(left["price"])
        rsi_lower_high = _float(right_candle.get("rsi14")) < _float(left_candle.get("rsi14")) - 2
        macd_lower_high = _float(right_candle.get("macd_hist")) < _float(left_candle.get("macd_hist"))
        if price_higher_high and (rsi_lower_high or macd_lower_high) and current_close < _float(previous.get("close")):
            matches.append(
                _match(
                    family="divergence",
                    label="Bearish Divergence",
                    direction="bearish",
                    timeframe=timeframe,
                    latest=latest,
                    support_levels=support_levels,
                    resistance_levels=resistance_levels,
                    evidence=[
                        _evidence("Price", "The latest pivot high exceeded the prior pivot high."),
                        _evidence("Momentum", "RSI or MACD made a lower high during the same move."),
                        _evidence("Response", "The latest bar is starting to fade after the divergence."),
                    ],
                    reasons=[
                        "Momentum weakened even while price printed a higher high.",
                        "Divergence often shows up near trend exhaustion.",
                        "Confirmation matters: the move still needs follow-through below nearby support.",
                    ],
                    zone_strength=int((resistance_zone or {}).get("strength") or 48),
                    volume_confirmed=volume_confirmed,
                    trend_alignment=bearish_trend,
                    reliability=55.0,
                )
            )

    matches.sort(key=lambda item: (-int(item["score"]), -int(item["confidence"]), item["pattern_label"]))
    return matches
