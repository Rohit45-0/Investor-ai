from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.video.demo_rendering import render_product_demo_video
from app.video.demo_service import save_product_demo_payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and render the Remotion hackathon product demo.")
    parser.add_argument(
        "--output-root",
        default=str(settings.data_dir),
        help="Data directory that contains processed/ runs.",
    )
    parser.add_argument("--run-label", help="Optional disclosure run label override.")
    parser.add_argument("--chart-run-label", help="Optional chart run label override.")
    parser.add_argument(
        "--tts-voice",
        default="ash",
        help="TTS voice for the narration track. Defaults to 'ash' for a human-sounding male profile.",
    )
    parser.add_argument(
        "--tts-model",
        help="Optional TTS model override. Defaults to the configured video TTS model.",
    )
    parser.add_argument(
        "--tts-speed",
        type=float,
        default=0.92,
        help="Narration speed multiplier.",
    )
    parser.add_argument(
        "--tts-instructions",
        help="Optional narration-style instructions override.",
    )
    parser.add_argument(
        "--payload-only",
        action="store_true",
        help="Build the payload and skip video rendering.",
    )
    parser.add_argument(
        "--out",
        help="Optional output MP4 path. Defaults to the managed processed/video_demo run directory.",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Render only the first ~6 seconds for a quick verification pass.",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="Render scale multiplier for the full render. Use 1.0 for full 1080p output.",
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
    payload = save_product_demo_payload(
        run_label=args.run_label,
        chart_run_label=args.chart_run_label,
        data_root=output_root,
        tts_voice=args.tts_voice,
        tts_model=args.tts_model,
        tts_instructions=args.tts_instructions,
        tts_speed=args.tts_speed,
    )
    print(f"Payload file: {payload['payload_path']}")
    print(f"Demo run label: {payload['demo_run_label']}")

    if args.payload_only:
        return

    result = render_product_demo_video(
        payload["demo_run_label"],
        data_root=output_root,
        preview=args.preview,
        scale=args.scale,
        workspace=args.workspace,
        out=args.out,
        overwrite_audio=args.overwrite_audio,
    )
    print(f"Rendered demo video: {result['output_path']}")
    print(f"Render quality: {result['quality_label']}")
    if result.get("audio_included"):
        print(f"Audio: AI narration included with voice '{result.get('audio_voice')}'")
    elif result.get("audio_error"):
        print(f"Audio skipped: {result['audio_error']}")


if __name__ == "__main__":
    main()
