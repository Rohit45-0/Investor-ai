from __future__ import annotations

from typing import Any


def find_pivots(
    candles: list[dict[str, Any]],
    *,
    left: int = 3,
    right: int = 3,
) -> dict[str, list[dict[str, Any]]]:
    highs: list[dict[str, Any]] = []
    lows: list[dict[str, Any]] = []
    total = len(candles)

    if total < left + right + 1:
        return {"highs": highs, "lows": lows}

    for index in range(left, total - right):
        current = candles[index]
        left_window = candles[index - left : index]
        right_window = candles[index + 1 : index + right + 1]

        if not left_window or not right_window:
            continue

        current_high = float(current["high"])
        current_low = float(current["low"])
        high_neighbors = [float(item["high"]) for item in left_window + right_window]
        low_neighbors = [float(item["low"]) for item in left_window + right_window]

        if current_high >= max(high_neighbors) and current_high > float(left_window[-1]["high"]):
            highs.append(
                {
                    "index": index,
                    "price": current_high,
                    "timestamp": current.get("timestamp"),
                    "date": current.get("date"),
                    "volume": current.get("volume", 0),
                }
            )

        if current_low <= min(low_neighbors) and current_low < float(left_window[-1]["low"]):
            lows.append(
                {
                    "index": index,
                    "price": current_low,
                    "timestamp": current.get("timestamp"),
                    "date": current.get("date"),
                    "volume": current.get("volume", 0),
                }
            )
    return {"highs": highs, "lows": lows}


def _cluster_threshold(price: float, atr_value: float | None) -> float:
    atr_component = (atr_value or (price * 0.015)) * 0.5
    return max(atr_component, price * 0.004)


def _strength_score(cluster: list[dict[str, Any]], candle_count: int) -> int:
    hits = len(cluster)
    last_index = max(int(item["index"]) for item in cluster)
    recency = max(0, 24 - (candle_count - 1 - last_index))
    volume_bonus = 0
    if cluster:
        avg_volume = sum(float(item.get("volume") or 0) for item in cluster) / hits
        if avg_volume > 0:
            volume_bonus = min(18, int(avg_volume ** 0.25))
    return min(100, (hits * 22) + recency + volume_bonus)


def cluster_zones(
    pivots: list[dict[str, Any]],
    *,
    atr_value: float | None,
    candle_count: int,
) -> list[dict[str, Any]]:
    if not pivots:
        return []

    sorted_pivots = sorted(pivots, key=lambda item: float(item["price"]))
    clusters: list[list[dict[str, Any]]] = []

    for pivot in sorted_pivots:
        price = float(pivot["price"])
        assigned = False
        for cluster in clusters:
            center = sum(float(item["price"]) for item in cluster) / len(cluster)
            threshold = _cluster_threshold(center, atr_value)
            if abs(price - center) <= threshold:
                cluster.append(pivot)
                assigned = True
                break
        if not assigned:
            clusters.append([pivot])

    zones = []
    for cluster in clusters:
        prices = [float(item["price"]) for item in cluster]
        center = sum(prices) / len(prices)
        width = _cluster_threshold(center, atr_value) / 2
        zones.append(
            {
                "price": round(center, 2),
                "lower": round(center - width, 2),
                "upper": round(center + width, 2),
                "hits": len(cluster),
                "first_date": cluster[0].get("date"),
                "last_date": cluster[-1].get("date"),
                "last_index": max(int(item["index"]) for item in cluster),
                "strength": _strength_score(cluster, candle_count),
            }
        )
    zones.sort(key=lambda item: (-int(item["strength"]), abs(float(item["price"]))))
    return zones


def nearest_support(zones: list[dict[str, Any]], price: float) -> dict[str, Any] | None:
    below = [item for item in zones if float(item["price"]) <= price]
    if below:
        return max(below, key=lambda item: float(item["price"]))
    if zones:
        return min(zones, key=lambda item: abs(float(item["price"]) - price))
    return None


def nearest_resistance(zones: list[dict[str, Any]], price: float) -> dict[str, Any] | None:
    above = [item for item in zones if float(item["price"]) >= price]
    if above:
        return min(above, key=lambda item: float(item["price"]))
    if zones:
        return min(zones, key=lambda item: abs(float(item["price"]) - price))
    return None


def build_support_resistance(candles: list[dict[str, Any]]) -> dict[str, Any]:
    if not candles:
        return {"support": [], "resistance": [], "pivots": {"highs": [], "lows": []}}

    latest_atr = candles[-1].get("atr14")
    pivots = find_pivots(candles)
    support = cluster_zones(pivots["lows"], atr_value=latest_atr, candle_count=len(candles))
    resistance = cluster_zones(pivots["highs"], atr_value=latest_atr, candle_count=len(candles))
    current_price = float(candles[-1]["close"])

    support = sorted(
        support[:6],
        key=lambda item: (abs(float(item["price"]) - current_price), -int(item["strength"])),
    )[:3]
    resistance = sorted(
        resistance[:6],
        key=lambda item: (abs(float(item["price"]) - current_price), -int(item["strength"])),
    )[:3]

    return {
        "support": support,
        "resistance": resistance,
        "pivots": pivots,
    }
