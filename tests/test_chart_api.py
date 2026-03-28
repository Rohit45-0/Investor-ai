from __future__ import annotations

from fastapi.testclient import TestClient

import app.main as main_module


client = TestClient(main_module.app)


def test_chart_runs_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        main_module,
        "load_chart_runs",
        lambda: [{"run_label": "2026-03-27T10-30-00+05-30", "has_signals": True, "signal_count": 12}],
    )

    response = client.get("/api/chart-runs")

    assert response.status_code == 200
    assert response.json()[0]["signal_count"] == 12


def test_stock_endpoint_includes_chart_summary(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "stock_context", lambda symbol: {"master": {"company": "Reliance Industries"}, "quote": {"last_price": 2900}})
    monkeypatch.setattr(main_module, "latest_run_label", lambda: None)
    monkeypatch.setattr(main_module, "load_dashboard_bundle", lambda run_label: None)
    monkeypatch.setattr(
        main_module,
        "chart_summary_for_symbol",
        lambda symbol: {
            "run_label": "2026-03-27T10-30-00+05-30",
            "pattern_label": "Bullish Breakout",
            "timeframe": "5m",
            "direction": "bullish",
            "score": 78,
            "confidence": 81,
        },
    )

    response = client.get("/api/stocks/RELIANCE")

    assert response.status_code == 200
    assert response.json()["chart_summary"]["pattern_label"] == "Bullish Breakout"


def test_stock_chart_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        main_module,
        "load_stock_chart",
        lambda symbol, run_label=None, force_refresh=False: {
            "symbol": symbol,
            "run_label": run_label or "2026-03-27T10-30-00+05-30",
            "summary": {"pattern_label": "Support Bounce"},
            "candles": {"1d": []},
        },
    )

    response = client.get("/api/stocks/INFY/chart")

    assert response.status_code == 200
    assert response.json()["summary"]["pattern_label"] == "Support Bounce"


def test_chart_run_endpoint(monkeypatch) -> None:
    main_module._update_chart_run_status(
        status="idle",
        started_at=None,
        completed_at=None,
        error=None,
        last_run_label=None,
        overview={},
        manifest={},
        requested_symbol_limit=None,
    )
    monkeypatch.setattr(
        main_module,
        "run_chart_pipeline",
        lambda **kwargs: {
            "run_label": "2026-03-27T10-30-00+05-30",
            "overview": {"signals_published": 8},
            "manifest": {"provider": "yahoo"},
        },
    )

    response = client.post("/api/chart-run", json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"running", "completed"}
    assert "started_at" in payload


def test_chart_run_status_endpoint(monkeypatch) -> None:
    main_module._update_chart_run_status(
        status="completed",
        started_at="2026-03-27T10:00:00",
        completed_at="2026-03-27T10:02:00",
        error=None,
        last_run_label="2026-03-27T10-30-00+05-30",
        overview={},
        manifest={},
        requested_symbol_limit=None,
    )
    monkeypatch.setattr(
        main_module,
        "load_chart_runs",
        lambda: [{"run_label": "2026-03-27T10-30-00+05-30", "has_signals": True, "signal_count": 8}],
    )

    response = client.get("/api/chart-run/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["latest_available_run"] == "2026-03-27T10-30-00+05-30"
