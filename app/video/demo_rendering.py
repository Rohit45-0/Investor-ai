from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
import os
import subprocess

import requests

from app.config import settings
from app.storage import (
    demo_video_audio_path,
    demo_video_media_path,
    demo_video_payload_path,
    demo_video_preview_media_path,
    demo_video_render_manifest_path,
    ensure_dir,
    load_json,
    save_json,
)
from app.video.rendering import _ensure_engine_dependencies, _npm_command, _preferred_workspace, _sync_engine_workspace
from app.video.service import ai_audio_disclosure


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())


def _truncate_tts_script(value: Any, limit: int = 3900) -> str:
    text = _normalize_text(value)
    if len(text) <= limit:
        return text
    trimmed = text[:limit].rsplit(" ", 1)[0].strip()
    return f"{trimmed}." if trimmed else ""


def _audio_asset_name(run_label: str) -> str:
    return f"runtime/demo-audio/{run_label}.mp3"


def load_saved_product_demo_payload(run_label: str, data_root: Path | None = None) -> dict[str, Any]:
    path = demo_video_payload_path(run_label, data_root)
    if not path.exists():
        raise FileNotFoundError(f"No saved product demo payload found for '{run_label}'.")
    payload = load_json(path)
    payload["demo_run_label"] = _normalize_text(payload.get("demo_run_label")) or run_label
    return payload


def synthesize_product_demo_audio(
    run_label: str,
    *,
    data_root: Path | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    payload = load_saved_product_demo_payload(run_label, data_root)
    metadata = dict(payload.get("audio") or {})
    destination = demo_video_audio_path(run_label, data_root)
    script = _truncate_tts_script(payload.get("tts_script"))

    if not settings.openai_api_key:
        metadata["available"] = False
        metadata["error"] = "OPENAI_API_KEY is missing, so narration was skipped."
    elif not script:
        metadata["available"] = False
        metadata["error"] = "Narration script was empty, so narration was skipped."
    elif destination.exists() and not overwrite:
        metadata["available"] = True
        metadata["error"] = None
    else:
        request_body: dict[str, Any] = {
            "model": metadata.get("model") or settings.video_tts_model,
            "voice": metadata.get("voice") or "ash",
            "input": script,
            "response_format": "mp3",
        }
        if _normalize_text(metadata.get("instructions")):
            request_body["instructions"] = metadata["instructions"]
        speed = float(metadata.get("speed") or 1.0)
        if abs(speed - 1.0) > 0.001:
            request_body["speed"] = speed

        response = requests.post(
            f"{settings.openai_base_url.rstrip('/')}/audio/speech",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json=request_body,
            stream=True,
            timeout=(30, 300),
        )
        try:
            response.raise_for_status()
            ensure_dir(destination.parent)
            with destination.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        handle.write(chunk)
            metadata["available"] = True
            metadata["error"] = None
        except Exception as exc:  # noqa: BLE001
            metadata["available"] = False
            metadata["error"] = str(exc)
        finally:
            response.close()

    metadata["script_characters"] = len(script)
    payload["audio"] = metadata
    save_json(demo_video_payload_path(run_label, data_root), payload)
    return metadata


def _stage_runtime_audio(run_label: str, workspace: Path, *, data_root: Path | None = None) -> str | None:
    source = demo_video_audio_path(run_label, data_root)
    if not source.exists():
        return None
    asset_name = _audio_asset_name(run_label)
    destination = workspace / "public" / Path(asset_name)
    ensure_dir(destination.parent)
    destination.write_bytes(source.read_bytes())
    return asset_name


def render_product_demo_video(
    run_label: str,
    *,
    data_root: Path | None = None,
    preview: bool = False,
    scale: float = 1.0,
    workspace: str | None = None,
    out: str | None = None,
    overwrite_audio: bool = False,
) -> dict[str, Any]:
    repo_root = settings.root_dir
    payload = load_saved_product_demo_payload(run_label, data_root)

    source_engine = repo_root / "video_engine"
    engine_dir = _preferred_workspace(repo_root, workspace or settings.video_render_workspace)
    if engine_dir != source_engine:
        _sync_engine_workspace(source_engine, engine_dir)
    else:
        ensure_dir(engine_dir / "public")
    _ensure_engine_dependencies(engine_dir)

    audio_metadata = dict(payload.get("audio") or {})
    if not preview:
        audio_metadata = synthesize_product_demo_audio(run_label, data_root=data_root, overwrite=overwrite_audio)
    asset_name = _stage_runtime_audio(run_label, engine_dir, data_root=data_root) if audio_metadata.get("available") else None

    render_payload = {
        **payload,
        "audio": {
            **audio_metadata,
            "available": bool(asset_name),
            "static_path": asset_name,
            "disclosure": ai_audio_disclosure(),
        },
    }
    save_json(demo_video_payload_path(run_label, data_root), render_payload)

    render_payload_path = engine_dir / "runtime" / "payloads" / f"{run_label}-demo.json"
    save_json(render_payload_path, render_payload)

    default_full_output = demo_video_media_path(run_label, data_root).resolve()
    default_preview_output = demo_video_preview_media_path(run_label, data_root).resolve()
    output_path = Path(out).resolve() if out else (default_preview_output if preview else default_full_output)

    effective_scale = 0.5 if preview else scale
    command = [
        _npm_command(),
        "run",
        "render",
        "--",
        "--composition",
        "ProductDemoWalkthrough",
        "--payload",
        str(render_payload_path),
        "--out",
        str(output_path),
    ]
    if preview:
        command.append("--preview")
    elif effective_scale != 1.0:
        command.extend(["--scale", str(effective_scale)])

    env = os.environ.copy()
    temp_dir = engine_dir.parent / "tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    env["TEMP"] = str(temp_dir)
    env["TMP"] = str(temp_dir)
    env["npm_config_cache"] = str(engine_dir.parent / "npm-cache")
    subprocess.run(
        command,
        cwd=engine_dir,
        check=True,
        env=env,
        timeout=settings.video_render_timeout_seconds,
    )

    output_width = max(1, int(round(float(render_payload.get("width") or 0) * effective_scale)))
    output_height = max(1, int(round(float(render_payload.get("height") or 0) * effective_scale)))
    quality_label = "1080p" if output_height >= 1080 else "720p" if output_height >= 720 else f"{output_height}p"
    manifest = {
        "demo_run_label": run_label,
        "mode": "preview" if preview else "full",
        "rendered_at": datetime.now().isoformat(timespec="seconds"),
        "duration_seconds": render_payload.get("duration_seconds"),
        "width": render_payload.get("width"),
        "height": render_payload.get("height"),
        "render_scale": effective_scale,
        "output_width": output_width,
        "output_height": output_height,
        "quality_label": quality_label,
        "output_path": str(output_path),
        "audio_included": bool(asset_name),
        "audio_voice": render_payload.get("audio", {}).get("voice"),
        "audio_disclosure": render_payload.get("audio", {}).get("disclosure"),
        "audio_error": render_payload.get("audio", {}).get("error"),
        "source_runs": render_payload.get("source_runs") or {},
    }
    if not preview and output_path == default_full_output:
        save_json(demo_video_render_manifest_path(run_label, data_root), manifest)
    return manifest
