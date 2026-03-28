from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any

import requests

from app.config import settings
from app.storage import (
    ensure_dir,
    load_json,
    save_json,
    video_audio_path,
    video_media_path,
    video_payload_path,
    video_preview_media_path,
    video_render_manifest_path,
)
from app.video.service import ai_audio_disclosure, base_audio_metadata, video_audio_asset_name

MIN_ENGINE_FREE_BYTES = 5 * 1024 * 1024 * 1024


def _npm_command() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def _quality_label(height: int) -> str:
    if height >= 1080:
        return "1080p"
    if height >= 720:
        return "720p"
    if height >= 540:
        return "540p"
    if height >= 360:
        return "360p"
    return f"{height}p"


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())


def _preferred_workspace(repo_root: Path, requested: str | None = None) -> Path:
    if requested:
        return Path(requested).expanduser().resolve()

    source_dir = repo_root / "video_engine"
    try:
        repo_free = shutil.disk_usage(source_dir.anchor or repo_root).free
    except FileNotFoundError:
        repo_free = MIN_ENGINE_FREE_BYTES

    d_drive = Path("D:/")
    if os.name == "nt" and repo_free < MIN_ENGINE_FREE_BYTES and d_drive.exists():
        return (d_drive / "AIInvestorVideoEngine" / "workspace").resolve()
    return source_dir


def _sync_engine_workspace(source_dir: Path, workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_dir / "package.json", workspace / "package.json")
    shutil.copy2(source_dir / "render.mjs", workspace / "render.mjs")

    source_src = source_dir / "src"
    target_src = workspace / "src"
    if target_src.exists():
        shutil.rmtree(target_src)
    shutil.copytree(source_src, target_src)

    source_public = source_dir / "public"
    target_public = workspace / "public"
    if target_public.exists():
        shutil.rmtree(target_public)
    if source_public.exists():
        shutil.copytree(source_public, target_public)
    else:
        target_public.mkdir(parents=True, exist_ok=True)


def _ensure_engine_dependencies(workspace: Path) -> None:
    node_modules = workspace / "node_modules"
    package_lock = workspace / "package-lock.json"
    package_json = workspace / "package.json"
    should_install = (not node_modules.exists()) or (
        package_lock.exists() and package_lock.stat().st_mtime < package_json.stat().st_mtime
    )
    if not node_modules.exists() and not package_lock.exists():
        should_install = True
    if not should_install:
        return

    env = os.environ.copy()
    cache_dir = workspace.parent / "npm-cache"
    temp_dir = workspace.parent / "tmp"
    cache_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    env["npm_config_cache"] = str(cache_dir)
    env["TEMP"] = str(temp_dir)
    env["TMP"] = str(temp_dir)
    subprocess.run([_npm_command(), "install"], cwd=workspace, check=True, env=env, timeout=settings.video_render_timeout_seconds)


def load_saved_video_payload(video_run_label: str, data_root: Path | None = None) -> dict[str, Any]:
    path = video_payload_path(video_run_label, data_root)
    if not path.exists():
        raise FileNotFoundError(f"No saved video payload found for '{video_run_label}'.")

    payload = load_json(path)
    payload["video_run_label"] = _normalize_text(payload.get("video_run_label")) or video_run_label
    payload["audio"] = {**base_audio_metadata(payload["video_run_label"]), **(payload.get("audio") or {})}
    return payload


def _truncate_tts_script(value: Any, limit: int = 3900) -> str:
    text = _normalize_text(value)
    if len(text) <= limit:
        return text
    trimmed = text[:limit].rsplit(" ", 1)[0].strip()
    return f"{trimmed}." if trimmed else ""


def synthesize_narration_audio(
    video_run_label: str,
    *,
    data_root: Path | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    payload = load_saved_video_payload(video_run_label, data_root)
    metadata = {**base_audio_metadata(video_run_label), **(payload.get("audio") or {})}
    script = _truncate_tts_script(payload.get("tts_script"))
    destination = video_audio_path(video_run_label, data_root)

    if not settings.video_tts_enabled:
        metadata["available"] = False
        metadata["error"] = None
    elif not settings.openai_api_key:
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
            "model": settings.video_tts_model,
            "voice": settings.video_tts_voice,
            "input": script,
            "response_format": "mp3",
        }
        if settings.video_tts_model == "gpt-4o-mini-tts" and settings.video_tts_instructions:
            request_body["instructions"] = settings.video_tts_instructions
        if abs(settings.video_tts_speed - 1.0) > 0.001:
            request_body["speed"] = settings.video_tts_speed

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
    save_json(video_payload_path(video_run_label, data_root), payload)
    return metadata


def _stage_runtime_audio(
    video_run_label: str,
    workspace: Path,
    *,
    data_root: Path | None = None,
) -> str | None:
    source = video_audio_path(video_run_label, data_root)
    if not source.exists():
        return None

    asset_name = video_audio_asset_name(video_run_label)
    destination = workspace / "public" / Path(asset_name)
    ensure_dir(destination.parent)
    shutil.copy2(source, destination)
    return asset_name


def render_saved_video(
    video_run_label: str,
    *,
    data_root: Path | None = None,
    preview: bool = False,
    scale: float | None = None,
    workspace: str | None = None,
    out: str | None = None,
    overwrite_audio: bool = False,
) -> dict[str, Any]:
    repo_root = settings.root_dir
    payload = load_saved_video_payload(video_run_label, data_root)
    payload_path = video_payload_path(video_run_label, data_root).resolve()

    source_engine = repo_root / "video_engine"
    engine_dir = _preferred_workspace(repo_root, workspace or settings.video_render_workspace)
    if engine_dir != source_engine:
        _sync_engine_workspace(source_engine, engine_dir)
    else:
        ensure_dir(engine_dir / "public")
    _ensure_engine_dependencies(engine_dir)

    audio_metadata = {**base_audio_metadata(video_run_label), **(payload.get("audio") or {})}
    if settings.video_tts_enabled and not preview:
        audio_metadata = synthesize_narration_audio(video_run_label, data_root=data_root, overwrite=overwrite_audio)
    asset_name = _stage_runtime_audio(video_run_label, engine_dir, data_root=data_root) if audio_metadata.get("available") else None

    render_payload = {
        **payload,
        "audio": {
            **audio_metadata,
            "available": bool(asset_name),
            "static_path": asset_name,
            "disclosure": ai_audio_disclosure(),
        },
    }
    save_json(video_payload_path(video_run_label, data_root), render_payload)

    render_payload_path = engine_dir / "runtime" / "payloads" / f"{video_run_label}.json"
    save_json(render_payload_path, render_payload)

    default_full_output = video_media_path(video_run_label, data_root).resolve()
    default_preview_output = video_preview_media_path(video_run_label, data_root).resolve()
    output_path = Path(out).resolve() if out else (default_preview_output if preview else default_full_output)

    effective_scale = 0.5 if preview else (settings.video_render_scale if scale is None else scale)
    command = [
        _npm_command(),
        "run",
        "render",
        "--",
        "--payload",
        str(render_payload_path),
        "--out",
        str(output_path),
    ]
    if preview:
        command.append("--preview")
    else:
        if effective_scale != 1.0:
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
    manifest = {
        "video_run_label": video_run_label,
        "mode": "preview" if preview else "full",
        "rendered_at": datetime.now().isoformat(timespec="seconds"),
        "duration_seconds": render_payload.get("duration_seconds"),
        "width": render_payload.get("width"),
        "height": render_payload.get("height"),
        "render_scale": effective_scale,
        "output_width": output_width,
        "output_height": output_height,
        "quality_label": _quality_label(output_height),
        "source_runs": render_payload.get("source_runs") or {},
        "output_path": str(output_path),
        "audio_included": bool(asset_name),
        "audio_voice": render_payload.get("audio", {}).get("voice"),
        "audio_disclosure": render_payload.get("audio", {}).get("disclosure"),
        "audio_error": render_payload.get("audio", {}).get("error"),
    }
    if not preview and output_path == default_full_output:
        save_json(video_render_manifest_path(video_run_label, data_root), manifest)

    return manifest
