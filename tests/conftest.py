from __future__ import annotations

from datetime import date, timedelta

from app.chart.indicators import enrich_candles


def build_candles(
    closes: list[float],
    *,
    start: date = date(2025, 1, 1),
    default_volume: int = 100_000,
    special_volumes: dict[int, int] | None = None,
) -> list[dict[str, float | int | str]]:
    rows = []
    previous_close = closes[0]
    special_volumes = special_volumes or {}
    for index, close in enumerate(closes):
        open_price = previous_close if index else close * 0.995
        high_price = max(open_price, close) + 0.7
        low_price = min(open_price, close) - 0.7
        volume = special_volumes.get(index, default_volume)
        current_date = start + timedelta(days=index)
        rows.append(
            {
                "symbol": "TEST",
                "interval": "1d",
                "timestamp": f"{current_date.isoformat()}T15:30:00+05:30",
                "date": current_date.isoformat(),
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close, 2),
                "volume": volume,
                "traded_value": round(close * volume, 2),
            }
        )
        previous_close = close
    return rows


def build_enriched_candles(
    closes: list[float],
    *,
    start: date = date(2025, 1, 1),
    default_volume: int = 100_000,
    special_volumes: dict[int, int] | None = None,
) -> list[dict[str, float | int | str]]:
    return enrich_candles(
        build_candles(
            closes,
            start=start,
            default_volume=default_volume,
            special_volumes=special_volumes,
        )
    )
