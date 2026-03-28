from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")


def resolve_data_dir() -> Path:
    raw_value = os.getenv("DATA_DIR")
    if not raw_value:
        return ROOT_DIR / "data"
    candidate = Path(raw_value).expanduser()
    if not candidate.is_absolute():
        candidate = ROOT_DIR / candidate
    return candidate


@dataclass(frozen=True)
class Settings:
    root_dir: Path
    data_dir: Path
    database_url: str | None
    openai_api_key: str | None
    openai_model: str
    agent_model: str
    embedding_model: str
    chat_model: str
    openai_base_url: str
    explanation_limit: int
    agent_signal_limit: int
    chat_retrieval_limit: int
    chat_history_messages: int
    orchestration_mode: str
    chart_data_provider: str
    chart_data_base_url: str
    chart_data_api_key: str | None
    chart_intraday_interval: str
    chart_intraday_lookback_days: int
    chart_daily_lookback_days: int
    chart_backtest_horizon_days: int
    chart_min_sample_size: int
    chart_liquidity_floor: float
    chart_explanation_limit: int
    chart_min_history_bars: int
    chart_score_threshold: int
    chart_scan_workers: int
    video_auto_render: bool
    video_render_scale: float
    video_render_workspace: str | None
    video_render_timeout_seconds: int
    video_tts_enabled: bool
    video_tts_model: str
    video_tts_voice: str
    video_tts_instructions: str
    video_tts_speed: float
    host: str
    port: int


def get_settings() -> Settings:
    return Settings(
        root_dir=ROOT_DIR,
        data_dir=resolve_data_dir(),
        database_url=os.getenv("DATABASE_URL"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        agent_model=os.getenv("AGENT_MODEL", os.getenv("OPENAI_MODEL", "gpt-4.1-mini")),
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        chat_model=os.getenv("CHAT_MODEL", os.getenv("OPENAI_MODEL", "gpt-4.1-mini")),
        openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        explanation_limit=int(os.getenv("SIGNAL_EXPLANATION_LIMIT", "12")),
        agent_signal_limit=int(os.getenv("AGENT_SIGNAL_LIMIT", "5")),
        chat_retrieval_limit=int(os.getenv("CHAT_RETRIEVAL_LIMIT", "8")),
        chat_history_messages=int(os.getenv("CHAT_HISTORY_MESSAGES", "6")),
        orchestration_mode=os.getenv("ORCHESTRATION_MODE", "multi_agent"),
        chart_data_provider=os.getenv("CHART_DATA_PROVIDER", "yahoo").strip().lower(),
        chart_data_base_url=os.getenv(
            "CHART_DATA_BASE_URL",
            "https://query1.finance.yahoo.com/v8/finance/chart",
        ).strip(),
        chart_data_api_key=os.getenv("CHART_DATA_API_KEY"),
        chart_intraday_interval=os.getenv("CHART_INTRADAY_INTERVAL", "5m").strip().lower(),
        chart_intraday_lookback_days=int(os.getenv("CHART_INTRADAY_LOOKBACK_DAYS", "10")),
        chart_daily_lookback_days=int(os.getenv("CHART_DAILY_LOOKBACK_DAYS", "730")),
        chart_backtest_horizon_days=int(os.getenv("CHART_BACKTEST_HORIZON_DAYS", "7")),
        chart_min_sample_size=int(os.getenv("CHART_MIN_SAMPLE_SIZE", "8")),
        chart_liquidity_floor=float(os.getenv("CHART_LIQUIDITY_FLOOR", "10000000")),
        chart_explanation_limit=int(os.getenv("CHART_EXPLANATION_LIMIT", "12")),
        chart_min_history_bars=int(os.getenv("CHART_MIN_HISTORY_BARS", "120")),
        chart_score_threshold=int(os.getenv("CHART_SCORE_THRESHOLD", "55")),
        chart_scan_workers=int(os.getenv("CHART_SCAN_WORKERS", "8")),
        video_auto_render=os.getenv("VIDEO_AUTO_RENDER", "true").strip().lower() in {"1", "true", "yes", "on"},
        video_render_scale=float(os.getenv("VIDEO_RENDER_SCALE", "1.0")),
        video_render_workspace=os.getenv("VIDEO_RENDER_WORKSPACE"),
        video_render_timeout_seconds=int(os.getenv("VIDEO_RENDER_TIMEOUT_SECONDS", "1800")),
        video_tts_enabled=os.getenv("VIDEO_TTS_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"},
        video_tts_model=os.getenv("VIDEO_TTS_MODEL", "gpt-4o-mini-tts").strip(),
        video_tts_voice=os.getenv("VIDEO_TTS_VOICE", "coral").strip(),
        video_tts_instructions=os.getenv(
            "VIDEO_TTS_INSTRUCTIONS",
            "Speak like a calm Indian markets anchor in a studio bulletin. Enunciate ticker symbols, numbers, percentages, and price levels clearly. Keep a steady pace, use short pauses, and avoid hype.",
        ).strip(),
        video_tts_speed=float(os.getenv("VIDEO_TTS_SPEED", "0.95")),
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
    )


settings = get_settings()
