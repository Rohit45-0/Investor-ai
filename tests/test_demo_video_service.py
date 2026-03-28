from __future__ import annotations

from app.storage import (
    chart_signals_path,
    chart_stock_detail_path,
    demo_video_payload_path,
    save_json,
    signals_path,
)
from app.video.demo_service import build_product_demo_payload, save_product_demo_payload


def _disclosure_bundle(run_label: str = "2026-03-28") -> dict:
    return {
        "run_label": run_label,
        "manifest": {"to_date": run_label},
        "overview": {"total_signals": 2, "total_events": 34},
        "explanations": {"completed": 2},
        "signals": [
            {
                "symbol": "LT",
                "company": "Larsen & Toubro Limited",
                "direction": "bullish",
                "score": 26,
                "confidence": 75,
                "primary_reason": "New order announcement",
                "llm_explanation": {
                    "signal_label": "New orders boost growth outlook",
                    "summary": "Fresh orders could improve revenue visibility and business momentum.",
                    "confidence": 75,
                },
                "agent_outputs": {
                    "filing_analyst": {
                        "what_changed": "The company disclosed a fresh order win.",
                        "key_facts": ["Order-related filing", "Potential revenue catalyst"],
                    },
                    "bull_analyst": {
                        "thesis": "Order inflow improves growth visibility.",
                        "supporting_points": ["Momentum catalyst", "Positive sentiment"],
                    },
                    "bear_analyst": {
                        "thesis": "Execution quality still matters.",
                        "supporting_points": ["Order size unclear", "Delivery timing matters"],
                    },
                    "referee": {
                        "signal_label": "Order-driven opportunity",
                        "why_it_matters": "The filing is concrete enough to deserve immediate investor follow-up.",
                    },
                },
            },
            {
                "symbol": "ESTER",
                "company": "Ester Industries Limited",
                "direction": "bearish",
                "score": 28,
                "confidence": 76,
                "primary_reason": "Potential closure disclosure",
                "llm_explanation": {
                    "signal_label": "Potential closure disclosure",
                    "summary": "The filing adds operational caution and deserves defensive review.",
                    "confidence": 76,
                },
            },
        ],
    }


def _chart_bundle() -> dict:
    return {
        "run_label": "2026-03-28T14-02-33+05-30",
        "generated_at": "2026-03-28T14:02:33+05:30",
        "manifest": {
            "universe_size": 2122,
            "backtest_horizon_days": 7,
        },
        "overview": {"signals_published": 2},
        "signals": [
            {
                "symbol": "GRAPHITE",
                "company": "Graphite India Limited",
                "direction": "bullish",
                "score": 98,
                "confidence": 87,
                "pattern_label": "Bullish Breakout",
                "timeframe": "1d",
                "backtest": {"success_rate": 35.7, "sample_size": 14},
                "llm_explanation": {
                    "signal_label": "Bullish Breakout",
                    "summary": "Price cleared resistance with volume and remains technically active.",
                    "confidence": 87,
                },
            },
            {
                "symbol": "DDEVPLSTIK",
                "company": "Ddev Plastiks Industries Limited",
                "direction": "bearish",
                "score": 98,
                "confidence": 86,
                "pattern_label": "Bearish Breakdown",
                "timeframe": "1d",
                "backtest": {"success_rate": 0.0, "sample_size": 3},
                "llm_explanation": {
                    "signal_label": "Bearish Breakdown",
                    "summary": "The stock broke below support and leads the defensive side of the board.",
                    "confidence": 86,
                },
            },
        ],
    }


def _stock_detail(symbol: str) -> dict:
    base = 100.0 if symbol == "DDEVPLSTIK" else 200.0
    candles = [{"close": round(base + (index * 0.8), 2)} for index in range(32)]
    return {
        "symbol": symbol,
        "summary": {"timeframe": "1d"},
        "candles": {
            "1d": candles,
        },
    }


def test_build_product_demo_payload(tmp_path) -> None:
    save_json(signals_path("2026-03-28", tmp_path), _disclosure_bundle())
    save_json(chart_signals_path("2026-03-28T14-02-33+05-30", tmp_path), _chart_bundle())
    save_json(
        chart_stock_detail_path("2026-03-28T14-02-33+05-30", "GRAPHITE", tmp_path),
        _stock_detail("GRAPHITE"),
    )
    save_json(
        chart_stock_detail_path("2026-03-28T14-02-33+05-30", "DDEVPLSTIK", tmp_path),
        _stock_detail("DDEVPLSTIK"),
    )

    payload = build_product_demo_payload(
        run_label="2026-03-28",
        chart_run_label="2026-03-28T14-02-33+05-30",
        data_root=tmp_path,
    )

    assert payload["video_id"] == "hackathon-product-demo"
    assert payload["duration_in_frames"] == 5400
    assert payload["duration_seconds"] == 180.0
    assert len(payload["tabs"]) == 4
    assert len(payload["sections"]) == 9
    assert payload["audio"]["voice"] == "ash"
    assert any(section["type"] == "workflow" for section in payload["sections"])
    assert payload["sections"][2]["cards"]


def test_save_product_demo_payload(tmp_path) -> None:
    save_json(signals_path("2026-03-28", tmp_path), _disclosure_bundle())
    save_json(chart_signals_path("2026-03-28T14-02-33+05-30", tmp_path), _chart_bundle())
    save_json(
        chart_stock_detail_path("2026-03-28T14-02-33+05-30", "GRAPHITE", tmp_path),
        _stock_detail("GRAPHITE"),
    )
    save_json(
        chart_stock_detail_path("2026-03-28T14-02-33+05-30", "DDEVPLSTIK", tmp_path),
        _stock_detail("DDEVPLSTIK"),
    )

    payload = save_product_demo_payload(
        run_label="2026-03-28",
        chart_run_label="2026-03-28T14-02-33+05-30",
        data_root=tmp_path,
    )

    assert payload["demo_run_label"]
    assert demo_video_payload_path(payload["demo_run_label"], tmp_path).exists()
