from __future__ import annotations

from datetime import datetime
from threading import Lock, Thread

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.chart.service import (
    load_chart_runs,
    load_chart_signal_bundle,
    load_stock_chart,
    run_chart_pipeline,
)
from app.chat.schemas import ChatIndexRequest, ChatQueryRequest
from app.chat.service import answer_query, chat_status, index_for_chat
from app.config import settings
from app.market import search_stock_master, stock_context
from app.pipeline import run_pipeline
from app.storage import (
    chart_summary_for_symbol,
    explained_signals_path,
    latest_run_label,
    load_dashboard_bundle,
    processed_root,
    signals_path,
    video_media_path,
)
from app.video.rendering import render_saved_video
from app.video.service import build_daily_market_video_payload, build_video_render_state, save_daily_market_video_payload

app = FastAPI(title="Opportunity Radar MVP", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = settings.root_dir / "app" / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

CHART_RUN_LOCK = Lock()
CHART_RUN_STATUS: dict[str, object] = {
    "status": "idle",
    "started_at": None,
    "completed_at": None,
    "error": None,
    "last_run_label": None,
    "overview": {},
    "manifest": {},
    "requested_symbol_limit": None,
    "video_payload_run_label": None,
    "video_payload_error": None,
    "video_render": {},
}

VIDEO_RENDER_LOCK = Lock()
VIDEO_RENDER_STATUS: dict[str, object] = {
    "status": "idle",
    "started_at": None,
    "completed_at": None,
    "error": None,
    "requested_video_run_label": None,
    "pending_video_run_label": None,
    "last_video_run_label": None,
    "last_output_path": None,
    "audio_included": False,
    "audio_voice": None,
    "audio_error": None,
}


def _timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _chart_run_snapshot() -> dict[str, object]:
    with CHART_RUN_LOCK:
        return dict(CHART_RUN_STATUS)


def _update_chart_run_status(**updates: object) -> dict[str, object]:
    with CHART_RUN_LOCK:
        CHART_RUN_STATUS.update(updates)
        return dict(CHART_RUN_STATUS)


def _video_render_snapshot() -> dict[str, object]:
    with VIDEO_RENDER_LOCK:
        return dict(VIDEO_RENDER_STATUS)


def _update_video_render_status(**updates: object) -> dict[str, object]:
    with VIDEO_RENDER_LOCK:
        VIDEO_RENDER_STATUS.update(updates)
        return dict(VIDEO_RENDER_STATUS)


def _start_video_render_worker(video_run_label: str) -> None:
    worker = Thread(
        target=_run_video_render_in_background,
        args=(video_run_label,),
        daemon=True,
    )
    worker.start()


def _queue_video_render(video_run_label: str | None) -> dict[str, object]:
    normalized = str(video_run_label or "").strip()
    if not normalized:
        return {
            "status": "missing",
            "started": False,
            "message": "No saved video payload was available to render.",
        }
    if not settings.video_auto_render:
        return {
            "status": "disabled",
            "started": False,
            "requested_video_run_label": normalized,
            "message": "Automatic video rendering is disabled.",
        }

    with VIDEO_RENDER_LOCK:
        if VIDEO_RENDER_STATUS.get("status") == "running":
            VIDEO_RENDER_STATUS.update(
                pending_video_run_label=normalized,
                completed_at=None,
            )
            snapshot = dict(VIDEO_RENDER_STATUS)
            snapshot["started"] = False
            snapshot["message"] = "Video render already running. Queued the latest request."
            return snapshot

        VIDEO_RENDER_STATUS.update(
            status="running",
            started_at=_timestamp(),
            completed_at=None,
            error=None,
            requested_video_run_label=normalized,
            pending_video_run_label=None,
            audio_included=False,
            audio_voice=None,
            audio_error=None,
        )
        snapshot = dict(VIDEO_RENDER_STATUS)

    _start_video_render_worker(normalized)
    snapshot["started"] = True
    snapshot["message"] = "Video render started in the background."
    return snapshot


def _run_video_render_in_background(video_run_label: str) -> None:
    next_video_run_label: str | None = None
    try:
        result = render_saved_video(
            video_run_label,
            scale=settings.video_render_scale,
            workspace=settings.video_render_workspace,
        )
        with VIDEO_RENDER_LOCK:
            queued = str(VIDEO_RENDER_STATUS.get("pending_video_run_label") or "").strip()
            next_video_run_label = queued or None
            if next_video_run_label == video_run_label:
                next_video_run_label = None
            VIDEO_RENDER_STATUS.update(
                status="completed",
                completed_at=_timestamp(),
                error=None,
                requested_video_run_label=video_run_label,
                pending_video_run_label=None,
                last_video_run_label=video_run_label,
                last_output_path=result.get("output_path"),
                audio_included=bool(result.get("audio_included")),
                audio_voice=result.get("audio_voice"),
                audio_error=result.get("audio_error"),
            )
    except Exception as exc:  # noqa: BLE001
        with VIDEO_RENDER_LOCK:
            queued = str(VIDEO_RENDER_STATUS.get("pending_video_run_label") or "").strip()
            next_video_run_label = queued or None
            if next_video_run_label == video_run_label:
                next_video_run_label = None
            VIDEO_RENDER_STATUS.update(
                status="failed",
                completed_at=_timestamp(),
                error=str(exc),
                requested_video_run_label=video_run_label,
                pending_video_run_label=None,
                audio_included=False,
                audio_voice=None,
                audio_error=None,
            )

    if next_video_run_label:
        with VIDEO_RENDER_LOCK:
            VIDEO_RENDER_STATUS.update(
                status="running",
                started_at=_timestamp(),
                completed_at=None,
                error=None,
                requested_video_run_label=next_video_run_label,
                pending_video_run_label=None,
                audio_included=False,
                audio_voice=None,
            )
        _start_video_render_worker(next_video_run_label)


def _run_chart_pipeline_in_background(payload: "ChartRunRequest") -> None:
    try:
        document = run_chart_pipeline(
            include_explanations=payload.include_explanations,
            explanation_limit=payload.explanation_limit,
            symbol_limit=payload.symbol_limit,
            force_refresh=payload.force_refresh,
        )
        video_payload = None
        video_payload_error = None
        video_render = {}
        try:
            video_payload = save_daily_market_video_payload(chart_run_label=document.get("run_label"))
            video_render = _queue_video_render((video_payload or {}).get("video_run_label"))
        except Exception as exc:  # noqa: BLE001
            video_payload_error = str(exc)
        _update_chart_run_status(
            status="completed",
            completed_at=_timestamp(),
            error=None,
            last_run_label=document.get("run_label"),
            overview=document.get("overview", {}),
            manifest=document.get("manifest", {}),
            video_payload_run_label=(video_payload or {}).get("video_run_label"),
            video_payload_error=video_payload_error,
            video_render=video_render,
        )
    except Exception as exc:  # noqa: BLE001
        _update_chart_run_status(
            status="failed",
            completed_at=_timestamp(),
            error=str(exc),
            video_payload_run_label=None,
            video_payload_error=None,
            video_render={},
        )


def serve_page(filename: str) -> FileResponse:
    return FileResponse(STATIC_DIR / filename)


class RunRequest(BaseModel):
    days_back: int = 1
    orchestration_mode: str = settings.orchestration_mode
    include_attachments: bool = True
    attachment_signal_limit: int = 12
    attachments_per_signal: int = 2
    include_explanations: bool = True
    explanation_limit: int = settings.explanation_limit
    agent_signal_limit: int = settings.agent_signal_limit
    index_chat: bool = True


class ChartRunRequest(BaseModel):
    include_explanations: bool = True
    explanation_limit: int = settings.chart_explanation_limit
    symbol_limit: int | None = None
    force_refresh: bool = False


class VideoBuildRequest(BaseModel):
    run_label: str | None = None
    chart_run_label: str | None = None
    disclosure_limit: int = 4
    chart_limit: int = 4


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "orchestration_mode": settings.orchestration_mode}


@app.get("/api/runs")
def list_runs() -> list[dict[str, object]]:
    root = processed_root()
    if not root.exists():
        return []

    runs = []
    for path in sorted(root.iterdir(), key=lambda item: item.stat().st_mtime, reverse=True):
        if not path.is_dir():
            continue
        if path.name in {"chart", "video", "video_demo"}:
            continue
        runs.append(
            {
                "run_label": path.name,
                "has_signals": signals_path(path.name).exists(),
                "has_explanations": explained_signals_path(path.name).exists(),
            }
        )
    return runs


@app.get("/api/universe")
def universe(q: str = "", limit: int = 300) -> dict[str, object]:
    return search_stock_master(q, limit=limit)


@app.get("/api/signals/latest")
def latest_signals() -> dict:
    run_label = latest_run_label()
    if not run_label:
        raise HTTPException(status_code=404, detail="No processed runs found.")
    return load_dashboard_bundle(run_label)


@app.get("/api/signals/{run_label}")
def signals_for_run(run_label: str) -> dict:
    try:
        return load_dashboard_bundle(run_label)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/chart-runs")
def list_chart_signal_runs() -> list[dict[str, object]]:
    return load_chart_runs()


@app.get("/api/chart-run/status")
def chart_run_status() -> dict[str, object]:
    snapshot = _chart_run_snapshot()
    runs = load_chart_runs()
    snapshot["latest_available_run"] = runs[0]["run_label"] if runs else None
    snapshot["available_runs"] = len(runs)
    return snapshot


@app.get("/api/chart-signals/latest")
def latest_chart_signals() -> dict:
    try:
        return load_chart_signal_bundle()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/chart-signals/{run_label}")
def chart_signals_for_run(run_label: str) -> dict:
    try:
        return load_chart_signal_bundle(run_label)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/video/latest")
def latest_market_video_payload(
    run_label: str | None = None,
    chart_run_label: str | None = None,
    disclosure_limit: int = 4,
    chart_limit: int = 4,
) -> dict[str, object]:
    try:
        payload = build_daily_market_video_payload(
            run_label=run_label,
            chart_run_label=chart_run_label,
            disclosure_limit=disclosure_limit,
            chart_limit=chart_limit,
        )
        payload["render"] = build_video_render_state(payload.get("source_runs"))
        payload["render_job"] = _video_render_snapshot()
        return payload
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/video-build")
def build_market_video_payload(payload: VideoBuildRequest) -> dict[str, object]:
    try:
        result = save_daily_market_video_payload(
            run_label=payload.run_label,
            chart_run_label=payload.chart_run_label,
            disclosure_limit=payload.disclosure_limit,
            chart_limit=payload.chart_limit,
        )
        result["video_render"] = _queue_video_render(result.get("video_run_label"))
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/video/media/{video_run_label}")
def latest_market_video_media(video_run_label: str) -> FileResponse:
    path = video_media_path(video_run_label)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"No rendered video found for '{video_run_label}'.")
    return FileResponse(path, media_type="video/mp4", filename=path.name)


@app.get("/api/video/status")
def latest_market_video_status() -> dict[str, object]:
    return _video_render_snapshot()


@app.get("/api/stocks/{symbol}")
def stock_details(symbol: str, run_label: str | None = None) -> dict[str, object]:
    normalized = symbol.strip().upper()
    if not normalized:
        raise HTTPException(status_code=400, detail="Symbol is required.")

    context = stock_context(normalized)
    bundle_run = run_label or latest_run_label()
    bundle = load_dashboard_bundle(bundle_run) if bundle_run else None

    signal = None
    coverage = None
    if bundle:
        for item in bundle.get("signals", []):
            if str(item.get("symbol") or "").upper() == normalized:
                signal = item
                break
        coverage = bundle.get("coverage", {}).get("by_symbol", {}).get(normalized)

    return {
        "symbol": normalized,
        "run_label": bundle_run,
        "master": context.get("master"),
        "quote": context.get("quote"),
        "signal": signal,
        "coverage": coverage,
        "chart_summary": chart_summary_for_symbol(normalized),
    }


@app.get("/api/stocks/{symbol}/chart")
def stock_chart_details(
    symbol: str,
    run_label: str | None = None,
    force_refresh: bool = False,
) -> dict[str, object]:
    normalized = symbol.strip().upper()
    if not normalized:
        raise HTTPException(status_code=400, detail="Symbol is required.")

    try:
        return load_stock_chart(
            normalized,
            run_label=run_label,
            force_refresh=force_refresh,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/run")
def trigger_run(payload: RunRequest) -> dict[str, object]:
    result = run_pipeline(
        days_back=payload.days_back,
        orchestration_mode=payload.orchestration_mode,
        include_attachments=payload.include_attachments,
        attachment_signal_limit=payload.attachment_signal_limit,
        attachments_per_signal=payload.attachments_per_signal,
        include_explanations=payload.include_explanations,
        explanation_limit=payload.explanation_limit,
        agent_signal_limit=payload.agent_signal_limit,
    )
    response: dict[str, object] = {
        "run_label": result["run_label"],
        "orchestration_mode": payload.orchestration_mode,
        "signals_path": str(signals_path(result["run_label"])),
        "explained_signals_path": str(explained_signals_path(result["run_label"])),
    }
    try:
        video_payload = save_daily_market_video_payload(run_label=result["run_label"])
        response["video_payload"] = {
            "video_run_label": video_payload.get("video_run_label"),
            "payload_path": video_payload.get("payload_path"),
        }
        response["video_render"] = _queue_video_render(video_payload.get("video_run_label"))
    except Exception as exc:  # noqa: BLE001
        response["video_payload_error"] = str(exc)
    if payload.index_chat:
        try:
            response["chat_index"] = index_for_chat(result["run_label"])
        except Exception as exc:  # noqa: BLE001
            response["chat_index_error"] = str(exc)
    return response


@app.post("/api/chart-run")
def trigger_chart_pipeline(payload: ChartRunRequest) -> dict[str, object]:
    current = _chart_run_snapshot()
    if current.get("status") == "running":
        current["started"] = False
        current["message"] = "A chart scan is already running."
        return current

    snapshot = _update_chart_run_status(
        status="running",
        started_at=_timestamp(),
        completed_at=None,
        error=None,
        overview={},
        manifest={},
        requested_symbol_limit=payload.symbol_limit,
        video_payload_run_label=None,
        video_payload_error=None,
        video_render={},
    )
    worker = Thread(
        target=_run_chart_pipeline_in_background,
        args=(payload,),
        daemon=True,
    )
    worker.start()
    snapshot["started"] = True
    snapshot["message"] = "Chart scan started in the background."
    return snapshot


@app.get("/api/chat/status")
def chat_index_status(run_label: str | None = None) -> list[dict[str, object]]:
    status = chat_status()
    if run_label:
        return [item for item in status if str(item.get("run_label")) == run_label]
    return status


@app.post("/api/chat/reindex")
def chat_reindex(payload: ChatIndexRequest) -> dict[str, object]:
    return index_for_chat(payload.run_label)


@app.post("/api/chat/query")
def chat_query(payload: ChatQueryRequest) -> dict[str, object]:
    try:
        return answer_query(payload).model_dump()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/")
def index() -> FileResponse:
    return serve_page("index.html")


@app.get("/radar")
def radar_page() -> FileResponse:
    return serve_page("radar.html")


@app.get("/chart-radar")
def chart_radar_page() -> FileResponse:
    return serve_page("chart-radar.html")


@app.get("/watchlist")
def watchlist_page() -> FileResponse:
    return serve_page("watchlist.html")


@app.get("/brief")
def brief_page() -> FileResponse:
    return serve_page("brief.html")


@app.get("/chat")
def chat_page() -> FileResponse:
    return serve_page("chat.html")
