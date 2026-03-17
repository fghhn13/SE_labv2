from __future__ import annotations

import argparse
from pathlib import Path

from .metrics import plot_all_metrics


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Plot training metrics from an episode CSV."
    )
    parser.add_argument(
        "csv_path",
        type=str,
        help="Path to CSV file produced by CsvEpisodeLogger.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help=(
            "Directory to save plots. "
            "If omitted, plots are shown interactively instead of being saved."
        ),
    )
    parser.add_argument(
        "--window",
        type=int,
        default=10,
        help="Rolling window size for smoothing metrics.",
    )

    args = parser.parse_args(argv)

    csv_path = Path(args.csv_path)
    if not csv_path.exists():
        raise SystemExit(f"CSV file not found: {csv_path}")

    plot_all_metrics(
        csv_path=csv_path,
        output_dir=args.output_dir,
        window=args.window,
    )


if __name__ == "__main__":
    main()

