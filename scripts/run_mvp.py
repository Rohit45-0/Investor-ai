from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.pipeline import run_pipeline
from app.storage import explained_signals_path, signals_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the full Opportunity Radar MVP pipeline.")
    parser.add_argument("--days-back", type=int, default=1)
    parser.add_argument("--from-date")
    parser.add_argument("--to-date")
    parser.add_argument(
        "--mode",
        default=settings.orchestration_mode,
        choices=["multi_agent", "classic"],
        help="Pipeline orchestration mode.",
    )
    parser.add_argument(
        "--output-root",
        default=str(settings.data_dir),
        help="Data directory that contains raw/ and processed/.",
    )
    parser.add_argument(
        "--skip-explanations",
        action="store_true",
        help="Skip the OpenAI explanation stage.",
    )
    parser.add_argument(
        "--explanation-limit",
        type=int,
        default=settings.explanation_limit,
        help="Maximum number of signals to explain.",
    )
    parser.add_argument("--attachment-signal-limit", type=int, default=12)
    parser.add_argument("--attachments-per-signal", type=int, default=2)
    parser.add_argument("--agent-signal-limit", type=int, default=settings.agent_signal_limit)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_pipeline(
        days_back=args.days_back,
        from_date_text=args.from_date,
        to_date_text=args.to_date,
        output_root=Path(args.output_root),
        orchestration_mode=args.mode,
        include_explanations=not args.skip_explanations,
        explanation_limit=args.explanation_limit,
        attachment_signal_limit=args.attachment_signal_limit,
        attachments_per_signal=args.attachments_per_signal,
        agent_signal_limit=args.agent_signal_limit,
    )
    run_label = result["run_label"]
    print(f"Run label: {run_label}")
    print(f"Mode: {args.mode}")
    print(f"Signals file: {signals_path(run_label, Path(args.output_root))}")
    if args.skip_explanations:
        print("Explanations: skipped")
    else:
        print(f"Explained signals file: {explained_signals_path(run_label, Path(args.output_root))}")


if __name__ == "__main__":
    main()
