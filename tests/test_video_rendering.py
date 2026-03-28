from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import app.video.rendering as rendering_module
from app.storage import load_json, save_json, video_audio_path, video_payload_path, video_render_manifest_path


def _payload(run_label: str = "2026-03-27T14-00-00+05-30") -> dict:
    return {
        "video_run_label": run_label,
        "video_id": "daily-market-wrap",
        "generated_at": "2026-03-27T14:00:00+05:30",
        "source_runs": {
            "disclosure_run_label": "2026-03-27",
            "chart_run_label": "2026-03-27T13-08-08+05-30",
        },
        "duration_seconds": 42.0,
        "width": 1920,
        "height": 1080,
        "tts_script": "The tape is mixed. Charts are active. Carry forward the strongest names.",
        "audio": {
            "enabled": True,
            "available": False,
            "provider": "openai",
            "model": "gpt-4o-mini-tts",
            "voice": "coral",
            "ai_generated": True,
            "disclosure": "Narration uses an AI-generated voice.",
        },
        "scenes": [],
    }


class _FakeSpeechResponse:
    def __init__(self, status_code: int = 200, body: bytes = b"mp3-bytes") -> None:
        self.status_code = status_code
        self._body = body

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size: int = 8192):
        yield self._body

    def close(self) -> None:
        return None


def test_synthesize_narration_audio_skips_without_api_key(tmp_path, monkeypatch) -> None:
    run_label = "2026-03-27T14-00-00+05-30"
    save_json(video_payload_path(run_label, tmp_path), _payload(run_label))
    monkeypatch.setattr(
        rendering_module,
        "settings",
        replace(rendering_module.settings, video_tts_enabled=True, openai_api_key=None),
    )

    metadata = rendering_module.synthesize_narration_audio(run_label, data_root=tmp_path)

    assert metadata["available"] is False
    assert "OPENAI_API_KEY" in metadata["error"]


def test_synthesize_narration_audio_writes_mp3(tmp_path, monkeypatch) -> None:
    run_label = "2026-03-27T14-00-00+05-30"
    save_json(video_payload_path(run_label, tmp_path), _payload(run_label))
    monkeypatch.setattr(
        rendering_module,
        "settings",
        replace(
            rendering_module.settings,
            video_tts_enabled=True,
            openai_api_key="sk-test",
            openai_base_url="https://api.openai.com/v1",
            video_tts_model="gpt-4o-mini-tts",
            video_tts_voice="coral",
            video_tts_instructions="Calm markets anchor voice.",
            video_tts_speed=1.0,
        ),
    )

    calls: list[dict] = []

    def fake_post(url: str, **kwargs):
        calls.append({"url": url, **kwargs})
        return _FakeSpeechResponse()

    monkeypatch.setattr(rendering_module.requests, "post", fake_post)

    metadata = rendering_module.synthesize_narration_audio(run_label, data_root=tmp_path)
    saved_payload = load_json(video_payload_path(run_label, tmp_path))

    assert calls
    assert calls[0]["url"].endswith("/audio/speech")
    assert metadata["available"] is True
    assert metadata["voice"] == "coral"
    assert video_audio_path(run_label, tmp_path).read_bytes() == b"mp3-bytes"
    assert saved_payload["audio"]["available"] is True
    assert saved_payload["audio"]["script_characters"] > 0


def test_render_saved_video_records_audio_manifest(tmp_path, monkeypatch) -> None:
    run_label = "2026-03-27T14-00-00+05-30"
    payload = _payload(run_label)
    payload["audio"]["available"] = True
    save_json(video_payload_path(run_label, tmp_path), payload)
    video_audio_path(run_label, tmp_path).parent.mkdir(parents=True, exist_ok=True)
    video_audio_path(run_label, tmp_path).write_bytes(b"mp3")

    monkeypatch.setattr(
        rendering_module,
        "settings",
        replace(rendering_module.settings, video_tts_enabled=False, video_render_timeout_seconds=30),
    )
    monkeypatch.setattr(rendering_module, "_ensure_engine_dependencies", lambda workspace: None)

    def fake_run(command, **kwargs):
        output_path = command[command.index("--out") + 1]
        Path(output_path).write_bytes(b"mp4")
        return None

    monkeypatch.setattr(rendering_module.subprocess, "run", fake_run)

    result = rendering_module.render_saved_video(
        run_label,
        data_root=tmp_path,
        workspace=str(tmp_path / "workspace"),
    )

    manifest = load_json(video_render_manifest_path(run_label, tmp_path))
    assert result["audio_included"] is True
    assert result["audio_voice"] == "coral"
    assert manifest["audio_included"] is True
    assert manifest["quality_label"] == "1080p"
