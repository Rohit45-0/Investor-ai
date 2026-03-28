from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from app.chat.service import chat_status
from app.config import settings
from app.storage import (
    demo_video_payload_path,
    latest_chart_run_label,
    latest_run_label,
    load_chart_bundle,
    load_dashboard_bundle,
    save_json,
)
from app.video.service import ai_audio_disclosure, build_daily_market_video_payload, build_video_render_state

IST = ZoneInfo("Asia/Kolkata")
DEMO_FPS = 30
DEMO_WIDTH = 1920
DEMO_HEIGHT = 1080
DEMO_TAB_LABELS = [
    {"key": "video_engine", "label": "Video Engine"},
    {"key": "opportunity_radar", "label": "Opportunity Radar"},
    {"key": "chart_intelligence", "label": "Chart Intelligence"},
    {"key": "market_chatgpt", "label": "Market ChatGPT"},
]
DEMO_SECTION_DURATIONS = {
    "intro": 450,
    "overview": 450,
    "opportunity": 750,
    "agentic": 720,
    "chart": 750,
    "chat": 720,
    "video": 750,
    "command": 540,
    "close": 270,
}


def now_ist() -> datetime:
    return datetime.now(IST)


def timestamped_demo_run_label(now: datetime | None = None) -> str:
    stamp = (now or now_ist()).astimezone(IST)
    offset = stamp.strftime("%z")
    offset_slug = f"{offset[:3]}-{offset[3:]}" if len(offset) == 5 else offset
    return stamp.strftime("%Y-%m-%dT%H-%M-%S") + offset_slug


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())


def _truncate(value: Any, limit: int = 160) -> str:
    text = _normalize_text(value)
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


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


def _headline(signal: dict[str, Any], fallback: str) -> str:
    explanation = signal.get("llm_explanation") or {}
    return (
        _normalize_text(explanation.get("signal_label"))
        or _normalize_text(signal.get("pattern_label"))
        or _normalize_text(signal.get("primary_reason"))
        or fallback
    )


def _summary(signal: dict[str, Any], fallback: str) -> str:
    explanation = signal.get("llm_explanation") or {}
    return _truncate(explanation.get("summary") or fallback, 180)


def _direction(signal: dict[str, Any]) -> str:
    value = _normalize_text(signal.get("direction")).lower()
    return value if value in {"bullish", "bearish", "neutral"} else "neutral"


def _company(signal: dict[str, Any]) -> str:
    return _normalize_text(signal.get("company")) or _normalize_text(signal.get("symbol")) or "Unknown company"


def _top_disclosure_cards(bundle: dict[str, Any], limit: int = 3) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for signal in (bundle.get("signals") or [])[:limit]:
        cards.append(
            {
                "symbol": _normalize_text(signal.get("symbol")),
                "company": _company(signal),
                "direction": _direction(signal),
                "headline": _headline(signal, "Disclosure signal"),
                "summary": _summary(signal, signal.get("primary_reason") or "Disclosure update"),
                "metric_label": "Score",
                "metric_value": _int(signal.get("score")),
            }
        )
    return cards


def _top_chart_cards(bundle: dict[str, Any], limit: int = 3) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for signal in (bundle.get("signals") or [])[:limit]:
        backtest = signal.get("backtest") or {}
        sample_size = _int(backtest.get("sample_size"))
        hit_rate = backtest.get("success_rate")
        metric_value = f"{_float(hit_rate):.1f}%" if hit_rate is not None else str(_int(signal.get("score")))
        cards.append(
            {
                "symbol": _normalize_text(signal.get("symbol")),
                "company": _company(signal),
                "direction": _direction(signal),
                "headline": _headline(signal, "Chart setup"),
                "summary": _summary(signal, signal.get("pattern_label") or "Pattern setup"),
                "metric_label": "7D hit rate" if hit_rate is not None else "Score",
                "metric_value": metric_value,
                "detail": _truncate(
                    f"{_normalize_text(signal.get('timeframe')) or '1d'} | {sample_size} samples"
                    if sample_size
                    else _normalize_text(signal.get("timeframe")) or "1d",
                    80,
                ),
            }
        )
    return cards


def _agentic_cards(signal: dict[str, Any]) -> list[dict[str, Any]]:
    outputs = signal.get("agent_outputs") or {}
    filing = outputs.get("filing_analyst") or {}
    bull = outputs.get("bull_analyst") or {}
    bear = outputs.get("bear_analyst") or {}
    referee = outputs.get("referee") or {}

    cards = [
        {
            "label": "Filing Analyst",
            "tone": "neutral",
            "headline": _truncate(filing.get("what_changed") or signal.get("primary_reason") or "Reads the filing evidence", 72),
            "detail": _truncate(" | ".join((filing.get("key_facts") or [])[:2]) or "Builds a structured evidence brief from filings and attachments.", 132),
        },
        {
            "label": "Bull Analyst",
            "tone": "bullish",
            "headline": _truncate(bull.get("thesis") or "Builds the strongest supported upside case.", 72),
            "detail": _truncate(" | ".join((bull.get("supporting_points") or [])[:2]) or "Argues the upside only from evidence that is already in the run.", 132),
        },
        {
            "label": "Bear Analyst",
            "tone": "bearish",
            "headline": _truncate(bear.get("thesis") or "Builds the strongest supported risk case.", 72),
            "detail": _truncate(" | ".join((bear.get("supporting_points") or [])[:2]) or "Stress-tests the bullish thesis with cautionary reading of the same evidence.", 132),
        },
        {
            "label": "Referee",
            "tone": _direction(signal),
            "headline": _truncate(referee.get("signal_label") or _headline(signal, "Final verdict"), 72),
            "detail": _truncate(referee.get("why_it_matters") or referee.get("summary") or "Produces the final investor-facing call and explanation.", 132),
        },
    ]
    return cards


def _agentic_steps(signal: dict[str, Any]) -> list[dict[str, Any]]:
    highlighted_symbol = _normalize_text(signal.get("symbol")) or "today's top stock"
    return [
        {
            "step": "Scout",
            "detail": "Collects the daily market universe from disclosures and related feeds.",
        },
        {
            "step": "Router",
            "detail": f"Shortlists the highest-signal names, including {highlighted_symbol}.",
        },
        {
            "step": "Debate Desk",
            "detail": "Filing Analyst, Bull Analyst, and Bear Analyst each build a separate structured view.",
        },
        {
            "step": "Referee",
            "detail": "Weights evidence over hype and publishes the final investor-facing verdict.",
        },
    ]


def _chat_metrics(run_label: str) -> dict[str, Any]:
    try:
        status_rows = chat_status()
    except Exception:  # noqa: BLE001
        return {"indexed_documents": 0, "indexed_chunks": 0, "ready": False}

    for row in status_rows:
        if str(row.get("run_label")) == run_label:
            return {
                "indexed_documents": _int(row.get("indexed_documents")),
                "indexed_chunks": _int(row.get("indexed_chunks")),
                "ready": True,
            }
    return {"indexed_documents": 0, "indexed_chunks": 0, "ready": False}


def _chat_demo(disclosure_signal: dict[str, Any] | None, chart_signal: dict[str, Any] | None, run_label: str) -> dict[str, Any]:
    primary = disclosure_signal or chart_signal or {}
    symbol = _normalize_text(primary.get("symbol")) or "LT"
    disclosure_summary = _summary(disclosure_signal or {}, "The disclosure lane surfaced a meaningful event in the latest run.")
    chart_summary = _summary(chart_signal or {}, "The chart lane surfaced a technically active setup in the latest run.")
    prompt = f"Why is {symbol} interesting today, and what should I watch next?"
    answer = _truncate(
        f"{symbol} stands out because {disclosure_summary} On top of that, the chart lane says {chart_summary} The next step is to verify the filing details, nearby levels, and whether follow-through confirms the thesis.",
        300,
    )
    metrics = _chat_metrics(run_label)
    return {
        "prompt": prompt,
        "answer": answer,
        "sources": [
            {"label": "Disclosure run", "value": run_label},
            {"label": "Primary symbol", "value": symbol},
            {"label": "Chart context", "value": _headline(chart_signal or {}, "Latest chart setup")},
        ],
        "stats": [
            {"label": "Indexed docs", "value": metrics["indexed_documents"]},
            {"label": "Retrieved chunks", "value": metrics["indexed_chunks"]},
            {"label": "Chat state", "value": "Ready" if metrics["ready"] else "Index needed"},
        ],
    }


def _video_metrics(run_label: str, chart_run_label: str, data_root: Path | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    source_runs = {
        "disclosure_run_label": run_label,
        "chart_run_label": chart_run_label,
    }
    latest_payload = build_daily_market_video_payload(run_label=run_label, chart_run_label=chart_run_label, data_root=data_root)
    render_state = build_video_render_state(source_runs, data_root=data_root)
    return latest_payload, render_state


def build_product_demo_payload(
    *,
    run_label: str | None = None,
    chart_run_label: str | None = None,
    data_root: Path | None = None,
    tts_voice: str = "ash",
    tts_model: str | None = None,
    tts_instructions: str | None = None,
    tts_speed: float = 0.92,
) -> dict[str, Any]:
    chosen_run = run_label or latest_run_label(data_root)
    chosen_chart_run = chart_run_label or latest_chart_run_label(data_root)
    if not chosen_run or not chosen_chart_run:
        raise FileNotFoundError("Both a disclosure run and a chart run are required to build the product demo payload.")

    disclosure_bundle = load_dashboard_bundle(chosen_run, data_root)
    chart_bundle = load_chart_bundle(chosen_chart_run, data_root)
    chosen_run = _normalize_text(disclosure_bundle.get("run_label")) or chosen_run
    chosen_chart_run = _normalize_text(chart_bundle.get("run_label")) or chosen_chart_run

    disclosure_cards = _top_disclosure_cards(disclosure_bundle)
    chart_cards = _top_chart_cards(chart_bundle)
    primary_signal = next((item for item in disclosure_bundle.get("signals", []) if item.get("agent_outputs")), None)
    if primary_signal is None:
        primary_signal = (disclosure_bundle.get("signals") or [None])[0]
    primary_chart_signal = (chart_bundle.get("signals") or [None])[0]
    chat_demo = _chat_demo(primary_signal, primary_chart_signal, chosen_run)
    latest_video_payload, latest_render = _video_metrics(chosen_run, chosen_chart_run, data_root)

    intro_stats = [
        {"label": "Products", "value": "4"},
        {"label": "Disclosure alerts", "value": _int((disclosure_bundle.get("overview") or {}).get("total_signals"))},
        {"label": "Chart alerts", "value": _int((chart_bundle.get("overview") or {}).get("signals_published"))},
        {"label": "Video", "value": latest_render.get("quality_label") or "Ready"},
    ]
    overview_cards = [
        {
            "label": "Opportunity Radar",
            "tone": "bullish",
            "headline": "Signal-finder for filings and regulatory shifts",
            "detail": "Continuously monitors disclosures, quarterly results, insider trades, management commentary shifts, and block or bulk deals.",
        },
        {
            "label": "Chart Intelligence",
            "tone": "neutral",
            "headline": "Breakouts, reversals, levels, and divergences",
            "detail": "Scans the full NSE universe and attaches stock-specific back-tested context to each published setup.",
        },
        {
            "label": "Market ChatGPT",
            "tone": "neutral",
            "headline": "Grounded chat over indexed runs",
            "detail": "Answers from retrieved sources, signal bundles, and indexed evidence instead of guessing from priors.",
        },
        {
            "label": "Video Engine",
            "tone": "bullish",
            "headline": "Zero-human-editing market walkthroughs",
            "detail": "Turns the latest data into a narrated 1080p product film and a daily market wrap.",
        },
    ]

    sections = [
        {
            "id": "intro",
            "type": "hero",
            "active_tab": "video_engine",
            "duration_frames": DEMO_SECTION_DURATIONS["intro"],
            "eyebrow": "Hackathon Demo",
            "title": "One intelligence layer across four market products.",
            "body": "This walkthrough shows how Opportunity Radar turns ET-style market data into alerts, chart setups, grounded chat, and auto-generated video.",
            "stats": intro_stats,
            "voiceover": "Opportunity Radar turns one market intelligence layer into four investor-facing products. In this walkthrough, we move from signal discovery to chart structure, then to grounded chat, and finally to auto-generated market video, all built from the same live system.",
        },
        {
            "id": "overview",
            "type": "overview",
            "active_tab": "video_engine",
            "duration_frames": DEMO_SECTION_DURATIONS["overview"],
            "eyebrow": "Product Surface",
            "title": "The app is organized around the exact hackathon brief.",
            "body": "Instead of a generic dashboard, each navigation tab is a product surface with its own job, user, and output format.",
            "cards": overview_cards,
            "voiceover": "Each tab has a distinct job, but all four read from the same market context. That lets an investor move from a fresh filing, to chart confirmation, to a cited explanation, and then to a visual briefing without losing continuity.",
        },
        {
            "id": "opportunity",
            "type": "showcase",
            "active_tab": "opportunity_radar",
            "duration_frames": DEMO_SECTION_DURATIONS["opportunity"],
            "eyebrow": "Opportunity Radar",
            "title": "Missed opportunities are surfaced as daily investor-facing alerts.",
            "body": "The disclosure lane watches filings, insider activity, bulk and block deals, quarterly results, commentary shifts, and regulatory changes, then filters them into a high-signal board.",
            "stats": [
                {"label": "Run", "value": chosen_run},
                {"label": "Fresh events", "value": _int((disclosure_bundle.get("overview") or {}).get("total_events"))},
                {"label": "Published alerts", "value": _int((disclosure_bundle.get("overview") or {}).get("total_signals"))},
                {"label": "AI briefs", "value": _int((disclosure_bundle.get("explanations") or {}).get("completed"))},
            ],
            "cards": disclosure_cards,
            "voiceover": "Opportunity Radar is the filing-led signal finder. It continuously watches disclosures, quarterly results, insider trades, bulk and block deals, commentary shifts, and regulatory changes. The goal is not to summarize noise, but to surface the few updates that deserve immediate research.",
        },
        {
            "id": "agentic",
            "type": "workflow",
            "active_tab": "opportunity_radar",
            "duration_frames": DEMO_SECTION_DURATIONS["agentic"],
            "eyebrow": "Agentic Layer",
            "title": f"Signals go through a multi-agent research desk before they are published.",
            "body": f"For the demo, { _normalize_text((primary_signal or {}).get('symbol')) or 'the top shortlisted name' } is passed through a filing analyst, a bull analyst, a bear analyst, and a referee.",
            "steps": _agentic_steps(primary_signal or {}),
            "cards": _agentic_cards(primary_signal or {}),
            "voiceover": "Once a name is shortlisted, the agentic layer takes over. A scout gathers the universe, a router prioritizes the strongest candidates, a filing analyst explains what changed, bull and bear analysts test the thesis from both sides, and a referee publishes the final investor-facing verdict.",
        },
        {
            "id": "chart",
            "type": "showcase",
            "active_tab": "chart_intelligence",
            "duration_frames": DEMO_SECTION_DURATIONS["chart"],
            "eyebrow": "Chart Pattern Intelligence",
            "title": "Real-time technical pattern detection stays in its own dedicated lane.",
            "body": "The chart engine scans the full NSE universe for breakouts, reversals, support and resistance reactions, and divergences, then attaches stock-specific back-tested success rates.",
            "stats": [
                {"label": "Chart run", "value": chosen_chart_run},
                {"label": "Universe", "value": _int((chart_bundle.get("manifest") or {}).get("universe_size"))},
                {"label": "Published", "value": _int((chart_bundle.get("overview") or {}).get("signals_published"))},
                {"label": "Backtest horizon", "value": f"{_int((chart_bundle.get('manifest') or {}).get('backtest_horizon_days'), settings.chart_backtest_horizon_days)}D"},
            ],
            "cards": chart_cards,
            "voiceover": "Chart Pattern Intelligence runs in parallel to the filing lane. It scans the NSE universe for breakouts, reversals, support and resistance reactions, and divergences. Every setup includes key levels plus stock-specific back-tested context, so the chart feed stays interpretable instead of becoming just another screener.",
        },
        {
            "id": "chat",
            "type": "chat",
            "active_tab": "market_chatgpt",
            "duration_frames": DEMO_SECTION_DURATIONS["chat"],
            "eyebrow": "Market ChatGPT",
            "title": "Grounded answers are generated from indexed runs and retrieved evidence.",
            "body": "This lane is designed to beat shallow market chat by staying source-cited and run-aware.",
            "prompt": chat_demo["prompt"],
            "answer": chat_demo["answer"],
            "sources": chat_demo["sources"],
            "stats": chat_demo["stats"],
            "voiceover": "Market ChatGPT is built for grounded analysis, not generic market chatter. It retrieves evidence from indexed runs before answering, so the response can explain why a stock matters, what changed in the latest run, and what an investor should verify next with sources attached.",
        },
        {
            "id": "video",
            "type": "showcase",
            "active_tab": "video_engine",
            "duration_frames": DEMO_SECTION_DURATIONS["video"],
            "eyebrow": "AI Market Video Engine",
            "title": "The same intelligence layer can publish itself as a narrated 1080p market film.",
            "body": "The video engine converts live radar counts, chart breadth, directional balance, and queue logic into a product-quality MP4 with no manual editing.",
            "stats": [
                {"label": "Render state", "value": _normalize_text(latest_render.get("status")) or "ready"},
                {"label": "Quality", "value": latest_render.get("quality_label") or "1080p"},
                {"label": "Duration", "value": f"{latest_video_payload.get('duration_seconds', 0)}s"},
                {"label": "Narration", "value": latest_render.get("audio_voice") or tts_voice},
            ],
            "cards": [
                {
                    "symbol": "Wrap",
                    "company": "Daily market film",
                    "direction": "bullish",
                    "headline": _normalize_text((latest_video_payload.get("summary") or {}).get("headline")) or "Daily market wrap",
                    "summary": _truncate((latest_video_payload.get("summary") or {}).get("subhead"), 180),
                    "metric_label": "Media URL",
                    "metric_value": latest_render.get("media_url") or "render pending",
                },
                {
                    "symbol": "Matrix",
                    "company": "Generation logic",
                    "direction": "neutral",
                    "headline": "The film is data-driven, not manually edited.",
                    "summary": "It is assembled from disclosure alerts, chart alerts, overlap names, directional balance, and a merged research queue.",
                    "metric_label": "Voice",
                    "metric_value": latest_render.get("audio_voice") or tts_voice,
                },
            ],
            "voiceover": "The Video Engine is a publishing layer on top of the research system. It turns live signal counts, chart breadth, directional balance, and the carry-forward queue into a watchable market briefing. The output is automatic, but the story still comes directly from the underlying data.",
        },
        {
            "id": "command",
            "type": "command",
            "active_tab": "video_engine",
            "duration_frames": DEMO_SECTION_DURATIONS["command"],
            "eyebrow": "Demo Ops",
            "title": "The whole demo can be refreshed with one command before presenting.",
            "body": "Instead of running separate prep steps, the app now ships with a single command that refreshes data, chart scans, and the market video.",
            "command": "python scripts/prepare_demo.py --serve",
            "checks": [
                "refresh Opportunity Radar",
                "refresh Chart Pattern Intelligence",
                "render the latest market video",
                "start the local demo server",
            ],
            "voiceover": "Because all four products share one pipeline, the platform can refresh quickly when new market data arrives. A single refresh updates filings, chart patterns, chat context, and the generated video, so the investor sees one consistent market picture instead of four disconnected tools.",
        },
        {
            "id": "close",
            "type": "close",
            "active_tab": "video_engine",
            "duration_frames": DEMO_SECTION_DURATIONS["close"],
            "eyebrow": "Submission Close",
            "title": "One data layer. Four product surfaces. Demo-ready today.",
            "body": "The architecture keeps deterministic market logic where precision matters and agentic reasoning where judgment matters.",
            "bullets": [
                "Opportunity Radar: signal-finder for filings",
                "Chart Pattern Intelligence: technical setups with backtests",
                "Market ChatGPT: grounded, cited answers",
                "AI Market Video Engine: narrated visual briefings",
            ],
            "voiceover": "The result is a market intelligence stack with four clear outputs: signals, chart setups, grounded answers, and video briefings. That combination is what makes Opportunity Radar useful for discovery, validation, and communication in one system.",
        },
    ]

    total_frames = sum(item["duration_frames"] for item in sections)
    payload = {
        "video_id": "hackathon-product-demo",
        "title": "Opportunity Radar Hackathon Product Demo",
        "generated_at": now_ist().isoformat(timespec="seconds"),
        "fps": DEMO_FPS,
        "width": DEMO_WIDTH,
        "height": DEMO_HEIGHT,
        "duration_in_frames": total_frames,
        "duration_seconds": round(total_frames / DEMO_FPS, 1),
        "brand": {
            "name": "Opportunity Radar",
            "tagline": "AI for the Indian Investor",
        },
        "tabs": DEMO_TAB_LABELS,
        "source_runs": {
            "disclosure_run_label": chosen_run,
            "chart_run_label": chosen_chart_run,
        },
        "audio": {
            "enabled": True,
            "available": False,
            "provider": "openai",
            "model": tts_model or settings.video_tts_model,
            "voice": tts_voice,
            "speed": tts_speed,
            "instructions": tts_instructions
            or "Narrate like a calm and credible Indian markets presenter. Stay product-focused, clear, and steady. Enunciate ticker symbols, numbers, and percentages carefully. Do not mention render quality, voice quality, or demo operations.",
            "ai_generated": True,
            "disclosure": ai_audio_disclosure(),
        },
        "sections": sections,
        "narration": [{"scene_id": item["id"], "text": item["voiceover"]} for item in sections],
        "tts_script": " ".join(_normalize_text(item.get("voiceover")) for item in sections if _normalize_text(item.get("voiceover"))),
    }
    return payload


def save_product_demo_payload(
    *,
    run_label: str | None = None,
    chart_run_label: str | None = None,
    data_root: Path | None = None,
    tts_voice: str = "ash",
    tts_model: str | None = None,
    tts_instructions: str | None = None,
    tts_speed: float = 0.92,
) -> dict[str, Any]:
    payload = build_product_demo_payload(
        run_label=run_label,
        chart_run_label=chart_run_label,
        data_root=data_root,
        tts_voice=tts_voice,
        tts_model=tts_model,
        tts_instructions=tts_instructions,
        tts_speed=tts_speed,
    )
    demo_run_label = timestamped_demo_run_label()
    payload["demo_run_label"] = demo_run_label
    path = demo_video_payload_path(demo_run_label, data_root)
    save_json(path, payload)
    payload["payload_path"] = str(path)
    return payload
