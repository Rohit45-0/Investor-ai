from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from app.config import settings


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_json(path: Path, payload: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def processed_root(data_root: Path | None = None) -> Path:
    base = data_root or settings.data_dir
    return base / "processed"


def processed_chart_root(data_root: Path | None = None) -> Path:
    return processed_root(data_root) / "chart"


def processed_video_root(data_root: Path | None = None) -> Path:
    return processed_root(data_root) / "video"


def processed_demo_video_root(data_root: Path | None = None) -> Path:
    return processed_root(data_root) / "video_demo"


def reference_root(data_root: Path | None = None) -> Path:
    base = data_root or settings.data_dir
    return base / "reference"


def cache_root(data_root: Path | None = None) -> Path:
    base = data_root or settings.data_dir
    return base / "cache"


def raw_root(data_root: Path | None = None) -> Path:
    base = data_root or settings.data_dir
    return base / "raw"


def latest_run_label(data_root: Path | None = None) -> str | None:
    root = processed_root(data_root)
    if not root.exists():
        return None

    ignored = {"chart", "video", "video_demo"}
    candidates = [path for path in root.iterdir() if path.is_dir() and path.name not in ignored]
    if not candidates:
        return None

    latest = max(candidates, key=lambda path: path.stat().st_mtime)
    return latest.name


def latest_chart_run_label(data_root: Path | None = None) -> str | None:
    root = processed_chart_root(data_root)
    if not root.exists():
        return None

    candidates = [path for path in root.iterdir() if path.is_dir()]
    if not candidates:
        return None

    latest = max(candidates, key=lambda path: path.stat().st_mtime)
    return latest.name


def latest_video_run_label(data_root: Path | None = None) -> str | None:
    root = processed_video_root(data_root)
    if not root.exists():
        return None

    candidates = [path for path in root.iterdir() if path.is_dir()]
    if not candidates:
        return None

    latest = max(candidates, key=lambda path: path.stat().st_mtime)
    return latest.name


def latest_demo_video_run_label(data_root: Path | None = None) -> str | None:
    root = processed_demo_video_root(data_root)
    if not root.exists():
        return None

    candidates = [path for path in root.iterdir() if path.is_dir()]
    if not candidates:
        return None

    latest = max(candidates, key=lambda path: path.stat().st_mtime)
    return latest.name


def events_path(run_label: str, data_root: Path | None = None) -> Path:
    return processed_root(data_root) / run_label / "events.json"


def manifest_path(run_label: str, data_root: Path | None = None) -> Path:
    return processed_root(data_root) / run_label / "manifest.json"


def signals_path(run_label: str, data_root: Path | None = None) -> Path:
    return processed_root(data_root) / run_label / "signals.json"


def enriched_signals_path(run_label: str, data_root: Path | None = None) -> Path:
    return processed_root(data_root) / run_label / "signals_enriched.json"


def explained_signals_path(run_label: str, data_root: Path | None = None) -> Path:
    return processed_root(data_root) / run_label / "signals_explained.json"


def chart_run_dir(run_label: str, data_root: Path | None = None) -> Path:
    return processed_chart_root(data_root) / run_label


def video_run_dir(run_label: str, data_root: Path | None = None) -> Path:
    return processed_video_root(data_root) / run_label


def demo_video_run_dir(run_label: str, data_root: Path | None = None) -> Path:
    return processed_demo_video_root(data_root) / run_label


def chart_signals_path(run_label: str, data_root: Path | None = None) -> Path:
    return chart_run_dir(run_label, data_root) / "signals.json"


def video_payload_path(run_label: str, data_root: Path | None = None) -> Path:
    return video_run_dir(run_label, data_root) / "daily_market_wrap.json"


def video_media_path(run_label: str, data_root: Path | None = None) -> Path:
    return video_run_dir(run_label, data_root) / "daily_market_wrap.mp4"


def video_audio_path(run_label: str, data_root: Path | None = None) -> Path:
    return video_run_dir(run_label, data_root) / "daily_market_wrap_voiceover.mp3"


def video_preview_media_path(run_label: str, data_root: Path | None = None) -> Path:
    return video_run_dir(run_label, data_root) / "daily_market_wrap_preview.mp4"


def video_render_manifest_path(run_label: str, data_root: Path | None = None) -> Path:
    return video_run_dir(run_label, data_root) / "daily_market_wrap.render.json"


def demo_video_payload_path(run_label: str, data_root: Path | None = None) -> Path:
    return demo_video_run_dir(run_label, data_root) / "product_demo.json"


def demo_video_media_path(run_label: str, data_root: Path | None = None) -> Path:
    return demo_video_run_dir(run_label, data_root) / "product_demo.mp4"


def demo_video_audio_path(run_label: str, data_root: Path | None = None) -> Path:
    return demo_video_run_dir(run_label, data_root) / "product_demo_voiceover.mp3"


def demo_video_preview_media_path(run_label: str, data_root: Path | None = None) -> Path:
    return demo_video_run_dir(run_label, data_root) / "product_demo_preview.mp4"


def demo_video_render_manifest_path(run_label: str, data_root: Path | None = None) -> Path:
    return demo_video_run_dir(run_label, data_root) / "product_demo.render.json"


def chart_stock_detail_path(
    run_label: str,
    symbol: str,
    data_root: Path | None = None,
) -> Path:
    safe_symbol = "".join(ch for ch in str(symbol or "").upper() if ch.isalnum() or ch in {"-", "_"})
    return chart_run_dir(run_label, data_root) / "stocks" / f"{safe_symbol}.json"


def stock_master_path(data_root: Path | None = None) -> Path:
    return reference_root(data_root) / "nse_equity_master.json"


def stock_quote_cache_path(symbol: str, data_root: Path | None = None) -> Path:
    safe_symbol = "".join(ch for ch in str(symbol or "").upper() if ch.isalnum() or ch in {"-", "_"})
    return cache_root(data_root) / "quotes" / f"{safe_symbol}.json"


def chart_candle_cache_path(
    symbol: str,
    interval: str,
    data_root: Path | None = None,
) -> Path:
    safe_symbol = "".join(ch for ch in str(symbol or "").upper() if ch.isalnum() or ch in {"-", "_"})
    safe_interval = "".join(ch for ch in str(interval or "").lower() if ch.isalnum())
    return cache_root(data_root) / "chart" / "candles" / safe_interval / f"{safe_symbol}.json"


def load_signal_bundle(
    run_label: str | None = None,
    data_root: Path | None = None,
    prefer_explained: bool = True,
) -> dict[str, Any]:
    chosen_run = run_label or latest_run_label(data_root)
    if not chosen_run:
        raise FileNotFoundError("No processed runs found.")

    explained = explained_signals_path(chosen_run, data_root)
    enriched = enriched_signals_path(chosen_run, data_root)
    scored = signals_path(chosen_run, data_root)

    if prefer_explained and explained.exists():
        return load_json(explained)
    if enriched.exists():
        return load_json(enriched)
    if scored.exists():
        return load_json(scored)

    raise FileNotFoundError(f"No scored signals found for run '{chosen_run}'.")


def build_symbol_coverage(
    run_label: str,
    data_root: Path | None = None,
) -> dict[str, Any]:
    path = events_path(run_label, data_root)
    if not path.exists():
        return {"raw_event_count": 0, "total_symbols": 0, "symbols": [], "by_symbol": {}}

    events = load_json(path)
    by_symbol: dict[str, dict[str, Any]] = {}

    for event in events:
        symbol = str(event.get("symbol") or "").strip().upper()
        if not symbol:
            continue

        event_date = event.get("event_date")
        record = by_symbol.setdefault(
            symbol,
            {
                "symbol": symbol,
                "company": event.get("company") or symbol,
                "event_count": 0,
                "attachment_count": 0,
                "latest_event_date": event_date,
                "latest_headline": event.get("headline"),
                "latest_event_type": event.get("event_type"),
                "event_types": set(),
            },
        )

        record["event_count"] += 1
        if event.get("attachment_url"):
            record["attachment_count"] += 1
        if event.get("company") and record["company"] == symbol:
            record["company"] = event["company"]
        if event.get("event_type"):
            record["event_types"].add(event["event_type"])

        latest_known = str(record.get("latest_event_date") or "")
        current_date = str(event_date or "")
        if current_date >= latest_known:
            record["latest_event_date"] = event_date
            record["latest_headline"] = event.get("headline")
            record["latest_event_type"] = event.get("event_type")

    symbols = []
    for record in by_symbol.values():
        normalized = {
            **record,
            "event_types": sorted(record["event_types"]),
        }
        symbols.append(normalized)

    symbols.sort(key=lambda item: (-item["event_count"], item["symbol"]))
    return {
        "raw_event_count": len(events),
        "total_symbols": len(symbols),
        "symbols": symbols,
        "by_symbol": {item["symbol"]: item for item in symbols},
    }


def load_dashboard_bundle(
    run_label: str | None = None,
    data_root: Path | None = None,
    prefer_explained: bool = True,
) -> dict[str, Any]:
    bundle = load_signal_bundle(run_label, data_root, prefer_explained=prefer_explained)
    chosen_run = bundle.get("run_label") or run_label or latest_run_label(data_root)
    if not chosen_run:
        return bundle

    coverage = build_symbol_coverage(chosen_run, data_root)
    signal_symbols = {
        str(item.get("symbol") or "").strip().upper()
        for item in bundle.get("signals", [])
        if item.get("symbol")
    }

    for item in coverage["symbols"]:
        item["has_ranked_signal"] = item["symbol"] in signal_symbols

    coverage["by_symbol"] = {item["symbol"]: item for item in coverage["symbols"]}
    coverage["shortlisted_symbols"] = len(signal_symbols)
    bundle["coverage"] = coverage
    return bundle


def load_chart_bundle(
    run_label: str | None = None,
    data_root: Path | None = None,
) -> dict[str, Any]:
    chosen_run = run_label or latest_chart_run_label(data_root)
    if not chosen_run:
        raise FileNotFoundError("No chart runs found.")

    path = chart_signals_path(chosen_run, data_root)
    if not path.exists():
        raise FileNotFoundError(f"No chart signals found for run '{chosen_run}'.")
    return load_json(path)


def chart_summary_for_symbol(
    symbol: str,
    run_label: str | None = None,
    data_root: Path | None = None,
) -> dict[str, Any] | None:
    normalized = str(symbol or "").strip().upper()
    if not normalized:
        return None

    try:
        bundle = load_chart_bundle(run_label, data_root)
    except FileNotFoundError:
        return None

    for item in bundle.get("signals", []):
        if str(item.get("symbol") or "").upper() == normalized:
            return {
                "run_label": bundle.get("run_label"),
                "as_of": item.get("as_of"),
                "timeframe": item.get("timeframe"),
                "pattern_family": item.get("pattern_family"),
                "pattern_label": item.get("pattern_label"),
                "direction": item.get("direction"),
                "score": item.get("score"),
                "confidence": item.get("confidence"),
                "success_rate": (item.get("backtest") or {}).get("success_rate"),
                "sample_size": (item.get("backtest") or {}).get("sample_size"),
                "summary": (item.get("llm_explanation") or {}).get("summary"),
            }
    return None


def timestamped_chart_run_label(now: datetime | None = None) -> str:
    stamp = (now or datetime.now(ZoneInfo("Asia/Kolkata"))).astimezone(ZoneInfo("Asia/Kolkata"))
    offset = stamp.strftime("%z")
    offset_slug = f"{offset[:3]}-{offset[3:]}" if len(offset) == 5 else offset
    return stamp.strftime("%Y-%m-%dT%H-%M-%S") + offset_slug
