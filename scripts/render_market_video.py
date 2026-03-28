from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.video.rendering import render_saved_video
from app.video.service import save_daily_market_video_payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and render the Remotion daily market wrap.")
    parser.add_argument(
        "--output-root",
        default=str(settings.data_dir),
        help="Data directory that contains processed/ runs.",
    )
    parser.add_argument("--run-label", help="Optional disclosure run label override.")
    parser.add_argument("--chart-run-label", help="Optional chart run label override.")
    parser.add_argument(
        "--disclosure-limit",
        type=int,
        default=4,
        help="Maximum number of disclosure cards to include.",
    )
    parser.add_argument(
        "--chart-limit",
        type=int,
        default=4,
        help="Maximum number of chart cards to include.",
    )
    parser.add_argument(
        "--payload-only",
        action="store_true",
        help="Build the payload and skip video rendering.",
    )
    parser.add_argument(
        "--out",
        help="Optional output MP4 path. Defaults to the managed processed/video run directory.",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Render the first ~6 seconds at reduced scale for a faster verification pass.",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=settings.video_render_scale,
        help="Optional render scale multiplier for the full render.",
    )
    parser.add_argument(
        "--workspace",
        help="Optional render workspace. Useful if the repo drive is low on space.",
    )
    parser.add_argument(
        "--overwrite-audio",
        action="store_true",
        help="Force narration MP3 regeneration before rendering.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_root = Path(args.output_root)
    payload = save_daily_market_video_payload(
        run_label=args.run_label,
        chart_run_label=args.chart_run_label,
        data_root=output_root,
        disclosure_limit=args.disclosure_limit,
        chart_limit=args.chart_limit,
    )
    print(f"Payload file: {payload['payload_path']}")

    if args.payload_only:
        return

    result = render_saved_video(
        payload["video_run_label"],
        data_root=output_root,
        preview=args.preview,
        scale=args.scale,
        workspace=args.workspace,
        out=args.out,
        overwrite_audio=args.overwrite_audio,
    )
    print(f"Rendered video: {result['output_path']}")
    if result.get("audio_included"):
        print(f"Audio: AI narration included with voice '{result.get('audio_voice')}'")
    elif result.get("audio_error"):
        print(f"Audio skipped: {result['audio_error']}")


if __name__ == "__main__":
    main()
