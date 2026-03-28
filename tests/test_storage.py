from __future__ import annotations

from app.storage import latest_run_label


def test_latest_run_label_ignores_chart_and_video_directories(tmp_path) -> None:
    processed = tmp_path / "processed"
    (processed / "chart").mkdir(parents=True)
    (processed / "video").mkdir(parents=True)
    target = processed / "2026-03-24"
    target.mkdir()

    assert latest_run_label(tmp_path) == "2026-03-24"
