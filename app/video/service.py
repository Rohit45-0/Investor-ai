from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from app.config import settings
from app.storage import (
    chart_stock_detail_path,
    latest_chart_run_label,
    latest_run_label,
    load_chart_bundle,
    load_dashboard_bundle,
    load_json,
    processed_video_root,
    save_json,
    video_media_path,
    video_payload_path,
    video_render_manifest_path,
)

IST = ZoneInfo("Asia/Kolkata")
VIDEO_FPS = 30
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
SCENE_DURATIONS = {
    "hero": 180,
    "filings": 300,
    "charts": 360,
    "queue": 240,
    "close": 180,
}


def ai_audio_disclosure() -> str:
    return "Narration uses an AI-generated voice."


def video_audio_asset_name(video_run_label: str) -> str:
    return f"runtime/audio/{video_run_label}.mp3"


def base_audio_metadata(video_run_label: str | None = None) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "enabled": bool(settings.video_tts_enabled),
        "available": False,
        "provider": "openai" if settings.video_tts_enabled else None,
        "model": settings.video_tts_model if settings.video_tts_enabled else None,
        "voice": settings.video_tts_voice if settings.video_tts_enabled else None,
        "ai_generated": True,
        "disclosure": ai_audio_disclosure(),
    }
    if video_run_label:
        metadata["asset_name"] = video_audio_asset_name(video_run_label)
    return metadata


def now_ist() -> datetime:
    return datetime.now(IST)


def timestamped_video_run_label(now: datetime | None = None) -> str:
    stamp = (now or now_ist()).astimezone(IST)
    offset = stamp.strftime("%z")
    offset_slug = f"{offset[:3]}-{offset[3:]}" if len(offset) == 5 else offset
    return stamp.strftime("%Y-%m-%dT%H-%M-%S") + offset_slug


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())


def _truncate(value: Any, limit: int = 140) -> str:
    text = _normalize_text(value)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _first_level(levels: list[dict[str, Any]] | None) -> float | None:
    if not levels:
        return None
    for item in levels:
        if item and item.get("price") is not None:
            return _float(item.get("price"))
    return None


def _format_level(value: float | None) -> str:
    return f"{value:.2f}" if value is not None else "n/a"


def _explanation_for(signal: dict[str, Any]) -> dict[str, Any]:
    explanation = signal.get("llm_explanation")
    return explanation if isinstance(explanation, dict) else {}


def _signal_label(signal: dict[str, Any]) -> str:
    explanation = _explanation_for(signal)
    return (
        _normalize_text(explanation.get("signal_label"))
        or _normalize_text(signal.get("pattern_label"))
        or _normalize_text(signal.get("primary_reason"))
        or "Market signal"
    )


def _signal_summary(signal: dict[str, Any], fallback: str) -> str:
    explanation = _explanation_for(signal)
    return _truncate(explanation.get("summary") or fallback, 150)


def _signal_company(signal: dict[str, Any]) -> str:
    return _normalize_text(signal.get("company")) or _normalize_text(signal.get("symbol")) or "Unknown company"


def _sparkline(symbol: str, chart_run_label: str | None, data_root: Path | None = None) -> list[float]:
    if not chart_run_label:
        return []

    path = chart_stock_detail_path(symbol=symbol, run_label=chart_run_label, data_root=data_root)
    if not path.exists():
        return []

    try:
        detail = load_json(path)
    except Exception:  # noqa: BLE001
        return []

    summary = detail.get("summary") or {}
    candles_map = detail.get("candles") or {}
    preferred = str(summary.get("timeframe") or "").strip()
    candles = candles_map.get(preferred) or candles_map.get("1d") or []
    closes = [_float(item.get("close")) for item in candles[-30:] if item.get("close") is not None]
    if len(closes) < 2:
        return []

    low = min(closes)
    high = max(closes)
    span = max(high - low, 0.0001)
    return [round((price - low) / span, 4) for price in closes]


def _build_disclosure_card(signal: dict[str, Any]) -> dict[str, Any]:
    reasons = [_normalize_text(item) for item in signal.get("reasons", []) if _normalize_text(item)]
    explanation = _explanation_for(signal)
    return {
        "symbol": _normalize_text(signal.get("symbol")),
        "company": _signal_company(signal),
        "direction": _normalize_text(signal.get("direction")) or "neutral",
        "headline": _signal_label(signal),
        "summary": _signal_summary(signal, reasons[0] if reasons else "Disclosure-driven setup."),
        "score": _int(signal.get("score")),
        "confidence": _int(explanation.get("confidence"), _int(signal.get("confidence"))),
        "metric_label": "Signal score",
        "metric_value": _int(signal.get("score")),
        "detail": _truncate(reasons[0] if reasons else signal.get("primary_reason"), 96),
        "source": "disclosure",
    }


def _build_chart_card(
    signal: dict[str, Any],
    *,
    chart_run_label: str | None,
    data_root: Path | None = None,
) -> dict[str, Any]:
    explanation = _explanation_for(signal)
    backtest = signal.get("backtest") or {}
    support = _first_level(signal.get("support_levels"))
    resistance = _first_level(signal.get("resistance_levels"))
    level_text = (
        f"Support {_format_level(support)} / Resistance {_format_level(resistance)}"
        if support is not None or resistance is not None
        else "Levels still forming"
    )
    success_rate = backtest.get("success_rate")
    sample_size = _int(backtest.get("sample_size"))
    return {
        "symbol": _normalize_text(signal.get("symbol")),
        "company": _signal_company(signal),
        "direction": _normalize_text(signal.get("direction")) or "neutral",
        "headline": _signal_label(signal),
        "summary": _signal_summary(signal, signal.get("pattern_label") or "Chart setup"),
        "score": _int(signal.get("score")),
        "confidence": _int(explanation.get("confidence"), _int(signal.get("confidence"))),
        "metric_label": "7D hit rate" if success_rate is not None else "Signal score",
        "metric_value": f"{_float(success_rate):.1f}%" if success_rate is not None else _int(signal.get("score")),
        "detail": _truncate(
            f"{signal.get('timeframe')} | {level_text} | {sample_size} samples"
            if sample_size
            else f"{signal.get('timeframe')} | {level_text}",
            96,
        ),
        "timeframe": _normalize_text(signal.get("timeframe")) or "1d",
        "success_rate": _float(success_rate) if success_rate is not None else None,
        "sample_size": sample_size,
        "sparkline": _sparkline(_normalize_text(signal.get("symbol")), chart_run_label, data_root),
        "source": "chart",
    }


def _merged_queue_items(
    disclosure_cards: list[dict[str, Any]],
    chart_cards: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}

    for card in disclosure_cards:
        symbol = card["symbol"]
        bucket = merged.setdefault(
            symbol,
            {
                "symbol": symbol,
                "company": card["company"],
                "headline": card["headline"],
                "sources": [],
                "direction": card["direction"],
                "conviction": 0.0,
                "note_parts": [],
            },
        )
        bucket["sources"].append("filing radar")
        bucket["conviction"] += _float(card.get("score"))
        bucket["note_parts"].append(card["headline"])

    for card in chart_cards:
        symbol = card["symbol"]
        bucket = merged.setdefault(
            symbol,
            {
                "symbol": symbol,
                "company": card["company"],
                "headline": card["headline"],
                "sources": [],
                "direction": card["direction"],
                "conviction": 0.0,
                "note_parts": [],
            },
        )
        bucket["sources"].append("chart radar")
        bucket["conviction"] += _float(card.get("score"))
        bucket["note_parts"].append(card["headline"])
        if bucket["direction"] != card["direction"]:
            bucket["direction"] = "mixed"

    items = []
    for record in merged.values():
        sources = sorted(set(record["sources"]))
        if sources == ["chart radar", "filing radar"]:
            thesis = "Both filing activity and chart structure are active."
        elif sources == ["chart radar"]:
            thesis = "Price structure is leading the research queue."
        else:
            thesis = "Disclosure activity is leading the research queue."
        items.append(
            {
                "symbol": record["symbol"],
                "company": record["company"],
                "direction": record["direction"],
                "headline": record["headline"],
                "sources": sources,
                "conviction": round(record["conviction"], 1),
                "thesis": thesis,
                "detail": _truncate(" + ".join(record["note_parts"]), 108),
            }
        )

    return sorted(items, key=lambda item: (-_float(item["conviction"]), item["symbol"]))[:4]


def _count_direction(items: list[dict[str, Any]], direction: str) -> int:
    return len([item for item in items if _normalize_text(item.get("direction")) == direction])


def _market_tone(
    disclosure_cards: list[dict[str, Any]],
    chart_cards: list[dict[str, Any]],
) -> tuple[str, str, str]:
    bullish = _count_direction(disclosure_cards, "bullish") + _count_direction(chart_cards, "bullish")
    bearish = _count_direction(disclosure_cards, "bearish") + _count_direction(chart_cards, "bearish")
    spread = bullish - bearish

    if spread >= 3:
        return (
            "risk_on",
            "Momentum is leaning bullish across radar and charts.",
            "Bullish setups are outnumbering risks, but the tape still needs follow-through after the trigger levels.",
        )
    if spread <= -3:
        return (
            "defensive",
            "Risk setups are stacking up faster than fresh longs.",
            "Bearish chart structures are starting to outweigh the strongest disclosure-led opportunities.",
        )
    return (
        "mixed",
        "The tape is mixed: selective filings, active charts, and no single market regime yet.",
        "Use today as a research queue, not a broad-market verdict, because conviction is still stock specific.",
    )


def _build_voiceover(
    hero_headline: str,
    disclosure_cards: list[dict[str, Any]],
    chart_cards: list[dict[str, Any]],
    queue_items: list[dict[str, Any]],
) -> dict[str, str]:
    disclosure_symbols = ", ".join(item["symbol"] for item in disclosure_cards[:3]) or "no clear filing leaders"
    chart_symbols = ", ".join(item["symbol"] for item in chart_cards[:3]) or "no clear chart leaders"
    queue_symbols = ", ".join(item["symbol"] for item in queue_items[:3]) or "no overlapping names yet"
    return {
        "hero": hero_headline,
        "filings": f"On the filing radar, the strongest research triggers are {disclosure_symbols}.",
        "charts": f"On the chart radar, price structure is most active in {chart_symbols}.",
        "queue": f"Names worth carrying into the next research queue are {queue_symbols}.",
        "close": "This wrap was assembled automatically from the latest Opportunity Radar and Chart Radar runs.",
    }


def _market_date(disclosure_bundle: dict[str, Any], chart_bundle: dict[str, Any]) -> str:
    disclosure_date = _normalize_text((disclosure_bundle.get("manifest") or {}).get("to_date"))
    if disclosure_date:
        return disclosure_date
    chart_time = _normalize_text(chart_bundle.get("generated_at"))
    return chart_time[:10] if len(chart_time) >= 10 else now_ist().date().isoformat()


def _top_score(items: list[dict[str, Any]]) -> int:
    if not items:
        return 0
    return max(_int(item.get("score")) for item in items)


def _balance_label(bullish: int, bearish: int) -> str:
    if not bullish and not bearish:
        return "No tilt"
    return f"{bullish} bull / {bearish} bear"


def _build_generation_matrix(
    *,
    disclosure_bundle: dict[str, Any],
    chart_bundle: dict[str, Any],
    disclosure_signals: list[dict[str, Any]],
    chart_signals: list[dict[str, Any]],
    disclosure_cards: list[dict[str, Any]],
    chart_cards: list[dict[str, Any]],
    queue_items: list[dict[str, Any]],
    overlap_count: int,
) -> list[dict[str, Any]]:
    bullish = _count_direction(disclosure_cards, "bullish") + _count_direction(chart_cards, "bullish")
    bearish = _count_direction(disclosure_cards, "bearish") + _count_direction(chart_cards, "bearish")
    chart_families = len(
        {
            _normalize_text(item.get("pattern_family"))
            for item in chart_signals
            if _normalize_text(item.get("pattern_family"))
        }
    )
    return [
        {
            "label": "Filing alerts",
            "value": _int((disclosure_bundle.get("overview") or {}).get("total_signals"), len(disclosure_signals)),
            "note": "Ranked disclosure-led signals available to the wrap from filings, insider trades, and bulk deals.",
            "source": "disclosure radar",
        },
        {
            "label": "Fresh disclosures",
            "value": _int((disclosure_bundle.get("overview") or {}).get("total_events")),
            "note": "Raw exchange events considered before the disclosure scorer narrows the board.",
            "source": "exchange feed",
        },
        {
            "label": "Chart alerts",
            "value": _int((chart_bundle.get("overview") or {}).get("signals_published"), len(chart_signals)),
            "note": "Published chart setups from breakout, reversal, support or resistance, and divergence scans.",
            "source": "chart radar",
        },
        {
            "label": "Pattern families",
            "value": chart_families,
            "note": "How many distinct chart pattern families are active in the current chart run.",
            "source": "chart radar",
        },
        {
            "label": "Bull vs bear",
            "value": _balance_label(bullish, bearish),
            "note": "The headline tone comes from the directional spread across the filing and chart cards pulled into the wrap.",
            "source": "mixed",
        },
        {
            "label": "Cross-radar overlap",
            "value": overlap_count,
            "note": "Names appearing across both disclosure and chart lanes rise higher in the research queue.",
            "source": "merged queue",
        },
        {
            "label": "Top filing score",
            "value": _top_score(disclosure_signals),
            "note": "Highest rule-based disclosure score in the latest disclosure run.",
            "source": "disclosure radar",
        },
        {
            "label": "Top chart score",
            "value": _top_score(chart_signals),
            "note": "Highest chart setup score in the latest chart run after confirmation and backtest context.",
            "source": "chart radar",
        },
        {
            "label": "Research queue",
            "value": len(queue_items),
            "note": "Merged carry-forward list after combining both lanes into a single research queue.",
            "source": "video engine",
        },
    ]


def _saved_video_payloads(data_root: Path | None = None) -> list[dict[str, Any]]:
    root = processed_video_root(data_root)
    if not root.exists():
        return []

    payloads: list[dict[str, Any]] = []
    directories = sorted(
        [path for path in root.iterdir() if path.is_dir()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for path in directories:
        payload_path = video_payload_path(path.name, data_root)
        if not payload_path.exists():
            continue
        try:
            payload = load_json(payload_path)
        except Exception:  # noqa: BLE001
            continue
        payload["video_run_label"] = _normalize_text(payload.get("video_run_label")) or path.name
        payload["payload_path"] = str(payload_path)
        payloads.append(payload)
    return payloads


def _matching_source_runs(saved_runs: dict[str, Any], target_runs: dict[str, Any]) -> bool:
    saved_disclosure = _normalize_text(saved_runs.get("disclosure_run_label"))
    saved_chart = _normalize_text(saved_runs.get("chart_run_label"))
    target_disclosure = _normalize_text(target_runs.get("disclosure_run_label"))
    target_chart = _normalize_text(target_runs.get("chart_run_label"))
    return saved_disclosure == target_disclosure and saved_chart == target_chart


def _load_full_render_manifest(
    video_run_label: str | None,
    data_root: Path | None = None,
) -> dict[str, Any] | None:
    normalized = _normalize_text(video_run_label)
    if not normalized:
        return None

    manifest_path = video_render_manifest_path(normalized, data_root)
    media_path = video_media_path(normalized, data_root)
    if not manifest_path.exists() or not media_path.exists():
        return None

    try:
        manifest = load_json(manifest_path)
    except Exception:  # noqa: BLE001
        return None

    if _normalize_text(manifest.get("mode")) != "full":
        return None

    manifest["video_run_label"] = normalized
    manifest["output_path"] = str(media_path)
    return manifest


def _render_state(
    *,
    status: str,
    payload: dict[str, Any] | None = None,
    render_manifest: dict[str, Any] | None = None,
    target_source_runs: dict[str, Any] | None = None,
    pending_payload: dict[str, Any] | None = None,
    data_root: Path | None = None,
) -> dict[str, Any]:
    status_labels = {
        "synced": "Rendered video is synced to the latest runs.",
        "payload_ready": "Latest storyboard is ready; render the MP4 to refresh the homepage film.",
        "stale": "A rendered video exists, but it is older than the latest disclosure and chart inputs.",
        "missing": "No rendered market video is available yet.",
    }
    video_run_label = _normalize_text((payload or {}).get("video_run_label"))
    media_url = f"/api/video/media/{video_run_label}" if render_manifest else None
    return {
        "status": status,
        "label": status_labels[status],
        "is_synced": status == "synced",
        "video_run_label": video_run_label or None,
        "generated_at": (payload or {}).get("generated_at"),
        "rendered_at": (render_manifest or {}).get("rendered_at"),
        "payload_path": (payload or {}).get("payload_path"),
        "media_available": bool(media_url),
        "media_url": media_url,
        "render_mode": (render_manifest or {}).get("mode"),
        "render_duration_seconds": (render_manifest or {}).get("duration_seconds"),
        "render_scale": (render_manifest or {}).get("render_scale"),
        "output_width": (render_manifest or {}).get("output_width"),
        "output_height": (render_manifest or {}).get("output_height"),
        "quality_label": (render_manifest or {}).get("quality_label"),
        "audio_included": bool((render_manifest or {}).get("audio_included")),
        "audio_voice": (render_manifest or {}).get("audio_voice"),
        "audio_disclosure": (render_manifest or {}).get("audio_disclosure"),
        "audio_error": (render_manifest or {}).get("audio_error"),
        "source_runs": (payload or {}).get("source_runs") or {},
        "target_source_runs": target_source_runs or {},
        "pending_video_run_label": _normalize_text((pending_payload or {}).get("video_run_label")) or None,
        "pending_generated_at": (pending_payload or {}).get("generated_at"),
    }


def build_video_render_state(
    source_runs: dict[str, Any] | None,
    *,
    data_root: Path | None = None,
) -> dict[str, Any]:
    target_runs = source_runs or {}
    saved_payloads = _saved_video_payloads(data_root)
    if not saved_payloads:
        return _render_state(status="missing", target_source_runs=target_runs, data_root=data_root)

    matched_payloads = [item for item in saved_payloads if _matching_source_runs(item.get("source_runs") or {}, target_runs)]
    matched_rendered = None
    matched_render_manifest = None
    for item in matched_payloads:
        manifest = _load_full_render_manifest(item.get("video_run_label"), data_root)
        if manifest:
            matched_rendered = item
            matched_render_manifest = manifest
            break
    if matched_rendered:
        return _render_state(
            status="synced",
            payload=matched_rendered,
            render_manifest=matched_render_manifest,
            target_source_runs=target_runs,
            data_root=data_root,
        )

    latest_rendered = None
    latest_render_manifest = None
    for item in saved_payloads:
        manifest = _load_full_render_manifest(item.get("video_run_label"), data_root)
        if manifest:
            latest_rendered = item
            latest_render_manifest = manifest
            break
    pending_payload = matched_payloads[0] if matched_payloads else None
    if latest_rendered:
        return _render_state(
            status="stale",
            payload=latest_rendered,
            render_manifest=latest_render_manifest,
            pending_payload=pending_payload,
            target_source_runs=target_runs,
            data_root=data_root,
        )
    if pending_payload:
        return _render_state(
            status="payload_ready",
            payload=pending_payload,
            target_source_runs=target_runs,
            data_root=data_root,
        )
    return _render_state(status="missing", target_source_runs=target_runs, data_root=data_root)


def build_daily_market_video_payload(
    *,
    run_label: str | None = None,
    chart_run_label: str | None = None,
    data_root: Path | None = None,
    disclosure_limit: int = 4,
    chart_limit: int = 4,
) -> dict[str, Any]:
    chosen_run = run_label or latest_run_label(data_root)
    chosen_chart_run = chart_run_label or latest_chart_run_label(data_root)
    if not chosen_run and not chosen_chart_run:
        raise FileNotFoundError("No disclosure or chart runs are available to build a market video payload.")

    disclosure_bundle: dict[str, Any] = {}
    chart_bundle: dict[str, Any] = {}
    if chosen_run:
        disclosure_bundle = load_dashboard_bundle(chosen_run, data_root)
        chosen_run = disclosure_bundle.get("run_label") or chosen_run
    if chosen_chart_run:
        chart_bundle = load_chart_bundle(chosen_chart_run, data_root)
        chosen_chart_run = chart_bundle.get("run_label") or chosen_chart_run

    disclosure_signals = list(disclosure_bundle.get("signals", []))
    chart_signals = list(chart_bundle.get("signals", []))

    disclosure_cards = [_build_disclosure_card(item) for item in disclosure_signals[: max(1, disclosure_limit)]]
    chart_cards = [
        _build_chart_card(item, chart_run_label=chosen_chart_run, data_root=data_root)
        for item in chart_signals[: max(1, chart_limit)]
    ]
    queue_items = _merged_queue_items(disclosure_cards, chart_cards)

    tone, hero_headline, hero_subhead = _market_tone(disclosure_cards, chart_cards)
    market_date = _market_date(disclosure_bundle, chart_bundle)
    total_frames = sum(SCENE_DURATIONS.values())
    voiceover = _build_voiceover(hero_headline, disclosure_cards, chart_cards, queue_items)
    overlap_count = len(
        {
            item["symbol"]
            for item in disclosure_cards
            if item["symbol"] in {card["symbol"] for card in chart_cards}
        }
    )
    generation_matrix = _build_generation_matrix(
        disclosure_bundle=disclosure_bundle,
        chart_bundle=chart_bundle,
        disclosure_signals=disclosure_signals,
        chart_signals=chart_signals,
        disclosure_cards=disclosure_cards,
        chart_cards=chart_cards,
        queue_items=queue_items,
        overlap_count=overlap_count,
    )

    scenes = [
        {
            "id": "hero",
            "type": "hero",
            "duration_frames": SCENE_DURATIONS["hero"],
            "eyebrow": "Opportunity Radar",
            "headline": hero_headline,
            "subhead": hero_subhead,
            "voiceover": voiceover["hero"],
            "stats": [
                {
                    "label": "Filing alerts",
                    "value": _int((disclosure_bundle.get("overview") or {}).get("total_signals"), len(disclosure_signals)),
                },
                {
                    "label": "Chart alerts",
                    "value": _int((chart_bundle.get("overview") or {}).get("signals_published"), len(chart_signals)),
                },
                {
                    "label": "Fresh disclosures",
                    "value": _int((disclosure_bundle.get("overview") or {}).get("total_events")),
                },
                {
                    "label": "Cross-signal names",
                    "value": overlap_count,
                },
            ],
        },
        {
            "id": "filings",
            "type": "board",
            "duration_frames": SCENE_DURATIONS["filings"],
            "eyebrow": "Filing Radar",
            "title": "Disclosure-led ideas in focus",
            "subtitle": "These are the strongest rule-based signals from exchange filings, insider trades, and bulk deals.",
            "voiceover": voiceover["filings"],
            "items": disclosure_cards,
        },
        {
            "id": "charts",
            "type": "board",
            "duration_frames": SCENE_DURATIONS["charts"],
            "eyebrow": "Chart Radar",
            "title": "Price structure is active here",
            "subtitle": "Breakouts, reversals, and divergences with stock-specific 7-day hit-rate context.",
            "voiceover": voiceover["charts"],
            "items": chart_cards,
        },
        {
            "id": "queue",
            "type": "queue",
            "duration_frames": SCENE_DURATIONS["queue"],
            "eyebrow": "Research Queue",
            "title": "Names to carry forward",
            "subtitle": "The strongest compound names are where filings and chart structure line up, or where one lens is especially loud.",
            "voiceover": voiceover["queue"],
            "items": queue_items,
        },
        {
            "id": "close",
            "type": "close",
            "duration_frames": SCENE_DURATIONS["close"],
            "eyebrow": "Auto-generated",
            "title": "Zero human editing, one research-ready wrap",
            "subtitle": "This is the first slice of the video engine. Next layers can add sector rotations, race charts, FII/DII flows, and IPO trackers.",
            "voiceover": voiceover["close"],
            "badges": [
                "Daily market wrap",
                "Disclosure radar",
                "Chart radar",
                "AI narration" if settings.video_tts_enabled else "Silent render",
                "Remotion-ready",
            ],
        },
    ]

    payload = {
        "video_id": "daily-market-wrap",
        "title": "Opportunity Radar Daily Market Wrap",
        "generated_at": now_ist().isoformat(timespec="seconds"),
        "market_date": market_date,
        "fps": VIDEO_FPS,
        "width": VIDEO_WIDTH,
        "height": VIDEO_HEIGHT,
        "duration_in_frames": total_frames,
        "duration_seconds": round(total_frames / VIDEO_FPS, 1),
        "brand": {
            "name": "Opportunity Radar",
            "tagline": "AI for the Indian Investor",
        },
        "source_runs": {
            "disclosure_run_label": chosen_run,
            "chart_run_label": chosen_chart_run,
        },
        "summary": {
            "tone": tone,
            "headline": hero_headline,
            "subhead": hero_subhead,
        },
        "stats": {
            "filing_alerts": len(disclosure_signals),
            "chart_alerts": len(chart_signals),
            "fresh_disclosures": _int((disclosure_bundle.get("overview") or {}).get("total_events")),
            "cross_signal_names": overlap_count,
        },
        "generation_matrix": generation_matrix,
        "generation_methodology": [
            "The hero tone is driven by the bullish-versus-bearish spread across the strongest disclosure and chart cards.",
            "The filing board selects the highest-ranking disclosure signals from the latest disclosure run.",
            "The chart board selects the highest-ranking chart setups with support, resistance, and stock-specific 7-day hit-rate context.",
            "The research queue merges both lanes so overlap names rise while strong single-lens outliers still stay visible.",
            "If narration is enabled, the TTS script is converted into an AI-generated voice track and embedded into the final MP4 render.",
        ],
        "audio": base_audio_metadata(),
        "scenes": scenes,
        "narration": [{"scene_id": item["id"], "text": item["voiceover"]} for item in scenes],
        "tts_script": " ".join(item["voiceover"] for item in scenes if _normalize_text(item.get("voiceover"))),
    }
    return payload


def save_daily_market_video_payload(
    *,
    run_label: str | None = None,
    chart_run_label: str | None = None,
    data_root: Path | None = None,
    disclosure_limit: int = 4,
    chart_limit: int = 4,
) -> dict[str, Any]:
    payload = build_daily_market_video_payload(
        run_label=run_label,
        chart_run_label=chart_run_label,
        data_root=data_root,
        disclosure_limit=disclosure_limit,
        chart_limit=chart_limit,
    )
    video_run_label = timestamped_video_run_label()
    payload["video_run_label"] = video_run_label
    payload["audio"] = base_audio_metadata(video_run_label)
    path = video_payload_path(video_run_label, data_root)
    save_json(path, payload)
    payload["payload_path"] = str(path)
    return payload
