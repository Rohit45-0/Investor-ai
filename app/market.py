from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests

from app.config import settings
from app.storage import ensure_dir, load_json, save_json, stock_master_path, stock_quote_cache_path

BASE_URL = "https://www.nseindia.com"
MASTER_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": f"{BASE_URL}/",
}
QUOTE_CACHE_TTL = timedelta(minutes=15)


class NSEReferenceClient:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def fetch_stock_master_csv(self) -> str:
        response = self.session.get(MASTER_URL, timeout=30)
        response.raise_for_status()
        return response.text

    def fetch_quote_equity(self, symbol: str) -> dict[str, Any]:
        normalized = str(symbol or "").strip().upper()
        if not normalized:
            raise ValueError("Symbol is required.")

        response = self.session.get(
            f"{BASE_URL}/api/quote-equity",
            params={"symbol": normalized},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()


def parse_stock_master(csv_text: str) -> dict[str, Any]:
    rows = []
    reader = csv.DictReader(io.StringIO(csv_text))

    for raw in reader:
        symbol = str(raw.get("SYMBOL") or "").strip().upper()
        if not symbol:
            continue
        row = {
            "symbol": symbol,
            "company": str(raw.get("NAME OF COMPANY") or symbol).strip(),
            "series": str(raw.get(" SERIES") or raw.get("SERIES") or "").strip(),
            "listing_date": str(raw.get(" DATE OF LISTING") or raw.get("DATE OF LISTING") or "").strip(),
            "paid_up_value": str(raw.get("PAID UP VALUE") or raw.get(" PAID UP VALUE") or "").strip(),
            "market_lot": str(raw.get(" MARKET LOT") or raw.get("MARKET LOT") or "").strip(),
            "isin": str(raw.get("ISIN NUMBER") or raw.get(" ISIN NUMBER") or "").strip(),
            "face_value": str(raw.get(" FACE VALUE") or raw.get("FACE VALUE") or "").strip(),
        }
        rows.append(row)

    rows.sort(key=lambda item: item["symbol"])
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_url": MASTER_URL,
        "total_symbols": len(rows),
        "symbols": rows,
    }


def load_stock_master(
    *,
    data_root: Path | None = None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    path = stock_master_path(data_root)
    if path.exists() and not force_refresh:
        data = load_json(path)
    else:
        client = NSEReferenceClient()
        data = parse_stock_master(client.fetch_stock_master_csv())
        save_json(path, data)

    symbols = data.get("symbols", [])
    data["by_symbol"] = {item["symbol"]: item for item in symbols}
    return data


def search_stock_master(
    query: str | None = None,
    *,
    limit: int = 100,
    data_root: Path | None = None,
) -> dict[str, Any]:
    master = load_stock_master(data_root=data_root)
    items = master.get("symbols", [])
    needle = str(query or "").strip().upper()

    if needle:
        filtered = [
            item
            for item in items
            if needle in item["symbol"] or needle in item["company"].upper()
        ]
    else:
        filtered = items

    limited = filtered[: max(1, min(limit, 5000))]
    return {
        "query": query or "",
        "total_symbols": master.get("total_symbols", len(items)),
        "returned": len(limited),
        "items": limited,
    }


def normalize_quote_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    info = payload.get("info") or {}
    metadata = payload.get("metadata") or {}
    security = payload.get("securityInfo") or {}
    price = payload.get("priceInfo") or {}
    industry = payload.get("industryInfo") or {}
    intra_day = price.get("intraDayHighLow") or {}
    week = price.get("weekHighLow") or {}

    return {
        "symbol": info.get("symbol") or metadata.get("symbol"),
        "company": info.get("companyName") or metadata.get("symbol"),
        "industry": info.get("industry") or metadata.get("industry") or industry.get("basicIndustry"),
        "sector": industry.get("sector"),
        "basic_industry": industry.get("basicIndustry"),
        "series": metadata.get("series"),
        "listing_date": metadata.get("listingDate") or info.get("listingDate"),
        "isin": info.get("isin") or metadata.get("isin"),
        "market_status": security.get("tradingStatus") or metadata.get("status"),
        "last_price": price.get("lastPrice"),
        "change": price.get("change"),
        "percent_change": price.get("pChange"),
        "previous_close": price.get("previousClose"),
        "open": price.get("open"),
        "high": intra_day.get("max"),
        "low": intra_day.get("min"),
        "week_52_high": week.get("max"),
        "week_52_low": week.get("min"),
        "last_update_time": metadata.get("lastUpdateTime"),
        "source_url": f"{BASE_URL}/get-quotes/equity?symbol={info.get('symbol') or metadata.get('symbol')}",
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
    }


def _quote_cache_is_fresh(path: Path) -> bool:
    if not path.exists():
        return False
    modified = datetime.fromtimestamp(path.stat().st_mtime)
    return datetime.now() - modified <= QUOTE_CACHE_TTL


def load_quote_snapshot(
    symbol: str,
    *,
    data_root: Path | None = None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    normalized = str(symbol or "").strip().upper()
    if not normalized:
        raise ValueError("Symbol is required.")

    path = stock_quote_cache_path(normalized, data_root)
    if path.exists() and not force_refresh and _quote_cache_is_fresh(path):
        return load_json(path)

    client = NSEReferenceClient()
    payload = client.fetch_quote_equity(normalized)
    normalized_quote = normalize_quote_snapshot(payload)
    ensure_dir(path.parent)
    save_json(path, normalized_quote)
    return normalized_quote


def stock_context(
    symbol: str,
    *,
    data_root: Path | None = None,
    force_quote_refresh: bool = False,
) -> dict[str, Any]:
    normalized = str(symbol or "").strip().upper()
    if not normalized:
        raise ValueError("Symbol is required.")

    master = load_stock_master(data_root=data_root)
    master_row = master.get("by_symbol", {}).get(normalized)

    try:
        quote = load_quote_snapshot(normalized, data_root=data_root, force_refresh=force_quote_refresh)
    except requests.RequestException:
        quote = None

    return {
        "symbol": normalized,
        "master": master_row,
        "quote": quote,
    }
