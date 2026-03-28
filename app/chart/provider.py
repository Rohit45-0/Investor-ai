from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests

from app.config import settings
from app.storage import chart_candle_cache_path, load_json, save_json

IST = ZoneInfo("Asia/Kolkata")
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-IN,en;q=0.9",
}
CACHE_TTLS = {
    "1d": timedelta(hours=12),
    "5m": timedelta(minutes=4),
}


def provider_symbol(symbol: str) -> str:
    normalized = str(symbol or "").strip().upper()
    if not normalized:
        raise ValueError("Symbol is required.")
    if "." in normalized:
        return normalized
    return f"{normalized}.NS"


def _cache_is_fresh(path: Path, interval: str) -> bool:
    if not path.exists():
        return False
    modified = datetime.fromtimestamp(path.stat().st_mtime)
    ttl = CACHE_TTLS.get(interval, timedelta(minutes=5))
    return datetime.now() - modified <= ttl


def _normalize_candles(
    payload: dict[str, Any],
    symbol: str,
    interval: str,
) -> list[dict[str, Any]]:
    chart = payload.get("chart") or {}
    error = chart.get("error")
    if error:
        raise RuntimeError(str(error.get("description") or "Chart provider returned an error."))

    result = (chart.get("result") or [{}])[0]
    timestamps = result.get("timestamp") or []
    quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
    opens = quote.get("open") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    closes = quote.get("close") or []
    volumes = quote.get("volume") or []
    timezone_name = ((result.get("meta") or {}).get("exchangeTimezoneName") or "Asia/Kolkata").strip()
    zone = ZoneInfo(timezone_name) if timezone_name else IST

    candles: list[dict[str, Any]] = []
    for index, ts in enumerate(timestamps):
        if index >= len(opens) or index >= len(highs) or index >= len(lows) or index >= len(closes):
            continue
        open_price = opens[index]
        high_price = highs[index]
        low_price = lows[index]
        close_price = closes[index]
        if open_price is None or high_price is None or low_price is None or close_price is None:
            continue

        local_dt = datetime.fromtimestamp(int(ts), tz=zone).astimezone(IST)
        volume = 0
        if index < len(volumes) and volumes[index] is not None:
            try:
                volume = int(volumes[index])
            except (TypeError, ValueError):
                volume = 0

        close_float = float(close_price)
        candles.append(
            {
                "symbol": symbol,
                "interval": interval,
                "timestamp": local_dt.isoformat(),
                "date": local_dt.date().isoformat(),
                "open": float(open_price),
                "high": float(high_price),
                "low": float(low_price),
                "close": close_float,
                "volume": volume,
                "traded_value": round(close_float * volume, 2),
            }
        )
    return candles


class MarketDataProvider:
    def fetch_candles(
        self,
        symbol: str,
        interval: str,
        *,
        lookback_days: int,
        data_root: Path | None = None,
        force_refresh: bool = False,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError


class YahooFinanceChartProvider(MarketDataProvider):
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def fetch_candles(
        self,
        symbol: str,
        interval: str,
        *,
        lookback_days: int,
        data_root: Path | None = None,
        force_refresh: bool = False,
    ) -> list[dict[str, Any]]:
        normalized = str(symbol or "").strip().upper()
        if not normalized:
            raise ValueError("Symbol is required.")

        safe_interval = str(interval or "1d").strip().lower()
        cache_path = chart_candle_cache_path(normalized, safe_interval, data_root)
        if cache_path.exists() and not force_refresh and _cache_is_fresh(cache_path, safe_interval):
            cached = load_json(cache_path)
            return cached.get("candles", [])

        range_days = max(5, int(lookback_days))
        if safe_interval.endswith("m"):
            range_days = min(range_days, 59)

        try:
            response = self.session.get(
                f"{settings.chart_data_base_url.rstrip('/')}/{provider_symbol(normalized)}",
                params={
                    "interval": safe_interval,
                    "range": f"{range_days}d",
                    "includePrePost": "false",
                    "events": "div,splits",
                },
                timeout=45,
            )
            response.raise_for_status()
            payload = response.json()
            candles = _normalize_candles(payload, normalized, safe_interval)
            save_json(
                cache_path,
                {
                    "provider": "yahoo",
                    "symbol": normalized,
                    "provider_symbol": provider_symbol(normalized),
                    "interval": safe_interval,
                    "lookback_days": range_days,
                    "fetched_at": datetime.now(IST).isoformat(timespec="seconds"),
                    "candles": candles,
                },
            )
            return candles
        except Exception:
            if cache_path.exists():
                cached = load_json(cache_path)
                return cached.get("candles", [])
            raise


def get_market_data_provider() -> MarketDataProvider:
    if settings.chart_data_provider == "yahoo":
        return YahooFinanceChartProvider()
    raise RuntimeError(f"Unsupported chart data provider '{settings.chart_data_provider}'.")
