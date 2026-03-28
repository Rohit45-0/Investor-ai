from __future__ import annotations

from fastapi.testclient import TestClient

import app.main as main_module


client = TestClient(main_module.app)


def test_latest_video_payload_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        main_module,
        "build_daily_market_video_payload",
        lambda **kwargs: {
            "video_id": "daily-market-wrap",
            "summary": {"headline": "Mixed tape"},
            "scenes": [],
            "source_runs": {},
        },
    )
    monkeypatch.setattr(
        main_module,
        "build_video_render_state",
        lambda source_runs: {"status": "missing", "label": "No rendered market video is available yet."},
    )
    monkeypatch.setattr(
        main_module,
        "_video_render_snapshot",
        lambda: {"status": "idle", "requested_video_run_label": None},
    )

    response = client.get("/api/video/latest")

    assert response.status_code == 200
    assert response.json()["video_id"] == "daily-market-wrap"
    assert response.json()["render"]["status"] == "missing"
    assert response.json()["render_job"]["status"] == "idle"


def test_build_video_payload_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        main_module,
        "save_daily_market_video_payload",
        lambda **kwargs: {
            "video_run_label": "2026-03-27T14-00-00+05-30",
            "payload_path": "data/processed/video/2026-03-27T14-00-00+05-30/daily_market_wrap.json",
        },
    )
    monkeypatch.setattr(
        main_module,
        "_queue_video_render",
        lambda run_label: {"status": "running", "requested_video_run_label": run_label},
    )

    response = client.post("/api/video-build", json={})

    assert response.status_code == 200
    assert response.json()["video_run_label"] == "2026-03-27T14-00-00+05-30"
    assert response.json()["video_render"]["status"] == "running"


def test_video_media_endpoint(monkeypatch, tmp_path) -> None:
    media_path = tmp_path / "daily_market_wrap.mp4"
    media_path.write_bytes(b"mp4")

    monkeypatch.setattr(main_module, "video_media_path", lambda run_label: media_path)

    response = client.get("/api/video/media/2026-03-27T14-00-00+05-30")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("video/mp4")


def test_video_status_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        main_module,
        "_video_render_snapshot",
        lambda: {
            "status": "running",
            "requested_video_run_label": "2026-03-27T14-00-00+05-30",
            "audio_included": False,
        },
    )

    response = client.get("/api/video/status")

    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_trigger_run_queues_video_render(monkeypatch) -> None:
    monkeypatch.setattr(
        main_module,
        "run_pipeline",
        lambda **kwargs: {"run_label": "2026-03-28"},
    )
    monkeypatch.setattr(
        main_module,
        "save_daily_market_video_payload",
        lambda **kwargs: {
            "video_run_label": "2026-03-28T10-00-00+05-30",
            "payload_path": "data/processed/video/2026-03-28T10-00-00+05-30/daily_market_wrap.json",
        },
    )
    monkeypatch.setattr(
        main_module,
        "_queue_video_render",
        lambda run_label: {"status": "running", "requested_video_run_label": run_label},
    )
    monkeypatch.setattr(
        main_module,
        "index_for_chat",
        lambda run_label: {"run_label": run_label, "indexed": True},
    )

    response = client.post("/api/run", json={"index_chat": False})

    assert response.status_code == 200
    assert response.json()["run_label"] == "2026-03-28"
    assert response.json()["video_payload"]["video_run_label"] == "2026-03-28T10-00-00+05-30"
    assert response.json()["video_render"]["status"] == "running"
