from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.chart.service import run_chart_pipeline
from app.config import settings
from app.storage import chart_signals_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Chart Pattern Intelligence pipeline.")
    parser.add_argument(
        "--output-root",
        default=str(settings.data_dir),
        help="Data directory that contains cache/ and processed/chart/.",
    )
    parser.add_argument(
        "--skip-explanations",
        action="store_true",
        help="Skip the OpenAI explanation stage.",
    )
    parser.add_argument(
        "--explanation-limit",
        type=int,
        default=settings.chart_explanation_limit,
        help="Maximum number of chart alerts to explain with OpenAI.",
    )
    parser.add_argument(
        "--symbol-limit",
        type=int,
        help="Optional cap for development runs.",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Refresh chart caches instead of reusing fresh data.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    document = run_chart_pipeline(
        data_root=Path(args.output_root),
        include_explanations=not args.skip_explanations,
        explanation_limit=args.explanation_limit,
        symbol_limit=args.symbol_limit,
        force_refresh=args.force_refresh,
    )
    run_label = document["run_label"]
    print(f"Run label: {run_label}")
    print(f"Signals published: {document['overview']['signals_published']}")
    print(f"Breakouts: {document['overview']['breakout_signals']}")
    print(f"Reversals: {document['overview']['reversal_signals']}")
    print(f"Divergences: {document['overview']['divergence_signals']}")
    print(f"Chart signals file: {chart_signals_path(run_label, Path(args.output_root))}")


if __name__ == "__main__":
    main()
