"""Internal star dataset build command."""

import argparse
from pathlib import Path

from reflections.analysis.star_tables import write_star_csv
from reflections.datasources.github import load_star_snapshot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--snapshots",
        type=Path,
        default=Path("data/github/stars"),
        help="star snapshot directory (default: data/github/stars)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/derived/stars.csv"),
        help="CSV path (default: data/derived/stars.csv)",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=365,
        help="matched before/after window in days (default: 365)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = sorted(
        path
        for path in args.snapshots.glob("*.json")
        if not path.name.endswith(".partial.json")
    )
    if not paths:
        raise SystemExit(f"No star snapshots found in {args.snapshots}")
    snapshots = [load_star_snapshot(path) for path in paths]
    output = write_star_csv(snapshots, args.output, window_days=args.window_days)
    print(f"Wrote daily star history for {len(snapshots)} repositories to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
