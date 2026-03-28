from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.chart.service import run_chart_pipeline
from app.config import settings
from app.pipeline import run_pipeline
from app.video.rendering import render_saved_video
from app.video.service import save_daily_market_video_payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare the full hackathon demo in one command: refresh signals, chart scan, and market video.",
    )
    parser.add_argument(
        "--output-root",
        default=str(settings.data_dir),
        help="Data directory that contains raw/, processed/, and cache/.",
    )
    parser.add_argument("--days-back", type=int, default=1, help="Disclosure collection lookback window.")
    parser.add_argument(
        "--mode",
        default=settings.orchestration_mode,
        choices=["multi_agent", "classic"],
        help="Opportunity Radar orchestration mode.",
    )
    parser.add_argument(
        "--agent-signal-limit",
        type=int,
        default=settings.agent_signal_limit,
        help="Maximum number of disclosure signals to send through the agent desk.",
    )
    parser.add_argument(
        "--chart-symbol-limit",
        type=int,
        help="Optional cap for chart scans during a faster rehearsal run.",
    )
    parser.add_argument(
        "--skip-signal-explanations",
        action="store_true",
        help="Skip the Opportunity Radar explanation stage.",
    )
    parser.add_argument(
        "--skip-chart-explanations",
        action="store_true",
        help="Skip the Chart Pattern Intelligence explanation stage.",
    )
    parser.add_argument(
        "--force-chart-refresh",
        action="store_true",
        help="Force the chart provider to refresh cached candles.",
    )
    parser.add_argument(
        "--video-scale",
        type=float,
        default=settings.video_render_scale,
        help="Override the final market-video render scale. Defaults to the configured full-quality setting.",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Start uvicorn after the data prep completes.",
    )
    parser.add_argument(
        "--host",
        default=settings.host,
        help="Host to use when starting uvicorn with --serve.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=settings.port,
        help="Port to use when starting uvicorn with --serve.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_root = Path(args.output_root)

    print("[1/4] Running Opportunity Radar...")
    pipeline_result = run_pipeline(
        days_back=args.days_back,
        output_root=output_root,
        orchestration_mode=args.mode,
        include_explanations=not args.skip_signal_explanations,
        agent_signal_limit=args.agent_signal_limit,
    )
    disclosure_run_label = pipeline_result["run_label"]
    print(f"  Disclosure run: {disclosure_run_label}")

    print("[2/4] Running Chart Pattern Intelligence...")
    chart_document = run_chart_pipeline(
        data_root=output_root,
        include_explanations=not args.skip_chart_explanations,
        symbol_limit=args.chart_symbol_limit,
        force_refresh=args.force_chart_refresh,
    )
    chart_run_label = chart_document["run_label"]
    print(f"  Chart run: {chart_run_label}")
    print(f"  Chart alerts: {chart_document['overview']['signals_published']}")

    print("[3/4] Building and rendering AI Market Video Engine...")
    video_payload = save_daily_market_video_payload(
        run_label=disclosure_run_label,
        chart_run_label=chart_run_label,
        data_root=output_root,
    )
    video_result = render_saved_video(
        video_payload["video_run_label"],
        data_root=output_root,
        scale=args.video_scale,
        overwrite_audio=True,
    )
    print(f"  Video payload: {video_payload['payload_path']}")
    print(f"  Video output: {video_result['output_path']}")
    if video_result.get("audio_included"):
        print(f"  Narration: enabled ({video_result.get('audio_voice')})")
    elif video_result.get("audio_error"):
        print(f"  Narration skipped: {video_result['audio_error']}")

    print("[4/4] Demo prep complete.")
    print(f"  Opportunity Radar run: {disclosure_run_label}")
    print(f"  Chart Intelligence run: {chart_run_label}")
    print(f"  Video run: {video_payload['video_run_label']}")
    print(f"  Open: http://{args.host}:{args.port}")

    if not args.serve:
        return

    print("Starting uvicorn...")
    subprocess.run(
        [
            "uvicorn",
            "app.main:app",
            "--reload",
            "--host",
            args.host,
            "--port",
            str(args.port),
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
