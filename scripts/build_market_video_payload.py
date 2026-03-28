from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.video.service import save_daily_market_video_payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a saved payload for the Remotion market video engine.")
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = save_daily_market_video_payload(
        run_label=args.run_label,
        chart_run_label=args.chart_run_label,
        data_root=Path(args.output_root),
        disclosure_limit=args.disclosure_limit,
        chart_limit=args.chart_limit,
    )
    print(f"Video run label: {payload['video_run_label']}")
    print(f"Market date: {payload['market_date']}")
    print(f"Duration: {payload['duration_seconds']} seconds")
    print(f"Payload file: {payload['payload_path']}")


if __name__ == "__main__":
    main()
