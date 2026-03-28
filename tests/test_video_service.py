from __future__ import annotations

from app.storage import (
    chart_signals_path,
    chart_stock_detail_path,
    save_json,
    signals_path,
    video_media_path,
    video_payload_path,
    video_render_manifest_path,
)
from app.video.service import build_daily_market_video_payload, build_video_render_state, save_daily_market_video_payload


def _disclosure_bundle(run_label: str = "2026-03-24") -> dict:
    return {
        "run_label": run_label,
        "manifest": {"to_date": run_label},
        "overview": {"total_signals": 2, "total_events": 41},
        "signals": [
            {
                "symbol": "RELIANCE",
                "company": "Reliance Industries Limited",
                "direction": "bullish",
                "score": 84,
                "confidence": 82,
                "primary_reason": "Promoter market purchase cluster",
                "reasons": ["Promoter buying stacked up across the latest filings."],
                "llm_explanation": {
                    "signal_label": "Promoter Buying Cluster",
                    "summary": "Promoter activity kept building in the latest disclosure run.",
                    "confidence": 82,
                },
            },
            {
                "symbol": "INFY",
                "company": "Infosys Limited",
                "direction": "bearish",
                "score": 66,
                "confidence": 70,
                "primary_reason": "Governance clarification risk",
                "reasons": ["The filing flow needs closer reading before sentiment improves."],
                "llm_explanation": {
                    "signal_label": "Clarification Overhang",
                    "summary": "The latest disclosure adds caution rather than conviction.",
                    "confidence": 70,
                },
            },
        ],
    }


def _chart_bundle() -> dict:
    return {
        "run_label": "2026-03-27T13-08-08+05-30",
        "generated_at": "2026-03-27T13:08:08+05:30",
        "overview": {"signals_published": 2},
        "signals": [
            {
                "symbol": "RELIANCE",
                "company": "Reliance Industries Limited",
                "direction": "bullish",
                "score": 91,
                "confidence": 85,
                "pattern_label": "Bullish Breakout",
                "timeframe": "5m",
                "support_levels": [{"price": 2825.5}],
                "resistance_levels": [{"price": 2862.4}],
                "backtest": {"success_rate": 57.1, "sample_size": 14},
                "llm_explanation": {
                    "signal_label": "Bullish Breakout",
                    "summary": "Reliance is pushing above resistance with volume.",
                    "confidence": 85,
                },
            },
            {
                "symbol": "TCS",
                "company": "Tata Consultancy Services Limited",
                "direction": "bearish",
                "score": 74,
                "confidence": 76,
                "pattern_label": "Resistance Rejection",
                "timeframe": "1d",
                "support_levels": [{"price": 3930.2}],
                "resistance_levels": [{"price": 4015.7}],
                "backtest": {"success_rate": 43.8, "sample_size": 16},
                "llm_explanation": {
                    "signal_label": "Resistance Rejection",
                    "summary": "TCS stalled near overhead supply and is fading.",
                    "confidence": 76,
                },
            },
        ],
    }


def _stock_detail(symbol: str, timeframe: str) -> dict:
    base = 100.0 if symbol == "TCS" else 200.0
    candles = [{"close": round(base + (index * 0.75), 2)} for index in range(32)]
    return {
        "symbol": symbol,
        "summary": {"timeframe": timeframe},
        "candles": {
            timeframe: candles,
            "1d": candles,
        },
    }


def test_build_daily_market_video_payload(tmp_path) -> None:
    save_json(signals_path("2026-03-24", tmp_path), _disclosure_bundle())
    save_json(chart_signals_path("2026-03-27T13-08-08+05-30", tmp_path), _chart_bundle())
    save_json(
        chart_stock_detail_path("2026-03-27T13-08-08+05-30", "RELIANCE", tmp_path),
        _stock_detail("RELIANCE", "5m"),
    )
    save_json(
        chart_stock_detail_path("2026-03-27T13-08-08+05-30", "TCS", tmp_path),
        _stock_detail("TCS", "1d"),
    )

    payload = build_daily_market_video_payload(
        run_label="2026-03-24",
        chart_run_label="2026-03-27T13-08-08+05-30",
        data_root=tmp_path,
    )

    assert payload["video_id"] == "daily-market-wrap"
    assert payload["summary"]["headline"]
    assert len(payload["scenes"]) == 5
    assert payload["width"] == 1920
    assert payload["height"] == 1080
    assert payload["duration_in_frames"] == 1260
    assert payload["duration_seconds"] == 42.0
    assert payload["scenes"][1]["type"] == "board"
    assert payload["scenes"][2]["items"][0]["sparkline"]
    assert payload["stats"]["cross_signal_names"] == 1
    assert payload["audio"]["enabled"] is True
    assert payload["audio"]["ai_generated"] is True
    assert payload["audio"]["voice"]
    assert payload["generation_matrix"]
    assert any(item["label"] == "Top chart score" for item in payload["generation_matrix"])


def test_save_daily_market_video_payload(tmp_path) -> None:
    save_json(signals_path("2026-03-24", tmp_path), _disclosure_bundle())
    save_json(chart_signals_path("2026-03-27T13-08-08+05-30", tmp_path), _chart_bundle())

    payload = save_daily_market_video_payload(
        run_label="2026-03-24",
        chart_run_label="2026-03-27T13-08-08+05-30",
        data_root=tmp_path,
    )

    assert payload["video_run_label"]
    assert video_payload_path(payload["video_run_label"], tmp_path).exists()
    assert payload["audio"]["asset_name"].endswith(".mp3")


def test_build_video_render_state_detects_synced_and_stale(tmp_path) -> None:
    save_json(signals_path("2026-03-24", tmp_path), _disclosure_bundle("2026-03-24"))
    save_json(chart_signals_path("2026-03-27T13-08-08+05-30", tmp_path), _chart_bundle())

    payload = save_daily_market_video_payload(
        run_label="2026-03-24",
        chart_run_label="2026-03-27T13-08-08+05-30",
        data_root=tmp_path,
    )
    video_media_path(payload["video_run_label"], tmp_path).write_bytes(b"mp4")
    save_json(
        video_render_manifest_path(payload["video_run_label"], tmp_path),
        {
            "video_run_label": payload["video_run_label"],
            "mode": "full",
            "duration_seconds": payload["duration_seconds"],
            "audio_included": True,
            "audio_voice": "coral",
            "audio_disclosure": "Narration uses an AI-generated voice.",
        },
    )

    synced = build_video_render_state(
        {
            "disclosure_run_label": "2026-03-24",
            "chart_run_label": "2026-03-27T13-08-08+05-30",
        },
        data_root=tmp_path,
    )
    assert synced["status"] == "synced"
    assert synced["media_url"] == f"/api/video/media/{payload['video_run_label']}"
    assert synced["audio_included"] is True
    assert synced["audio_voice"] == "coral"

    stale = build_video_render_state(
        {
            "disclosure_run_label": "2026-03-25",
            "chart_run_label": "2026-03-27T13-08-08+05-30",
        },
        data_root=tmp_path,
    )
    assert stale["status"] == "stale"
    assert stale["media_url"] == f"/api/video/media/{payload['video_run_label']}"


def test_build_video_render_state_ignores_media_without_full_manifest(tmp_path) -> None:
    save_json(signals_path("2026-03-24", tmp_path), _disclosure_bundle("2026-03-24"))
    save_json(chart_signals_path("2026-03-27T13-08-08+05-30", tmp_path), _chart_bundle())

    payload = save_daily_market_video_payload(
        run_label="2026-03-24",
        chart_run_label="2026-03-27T13-08-08+05-30",
        data_root=tmp_path,
    )
    video_media_path(payload["video_run_label"], tmp_path).write_bytes(b"preview")

    render_state = build_video_render_state(
        {
            "disclosure_run_label": "2026-03-24",
            "chart_run_label": "2026-03-27T13-08-08+05-30",
        },
        data_root=tmp_path,
    )

    assert render_state["status"] == "payload_ready"
    assert render_state["media_url"] is None
