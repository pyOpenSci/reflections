"""Build an issue-level CSV from local issue snapshots."""

import argparse
from pathlib import Path

from reflections import load_issue_snapshot, write_issue_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--snapshots",
        type=Path,
        default=Path("data/github/issues"),
        help="issue snapshot directory (default: data/github/issues)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/derived/issues.csv"),
        help="CSV path (default: data/derived/issues.csv)",
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
        raise SystemExit(f"No issue snapshots found in {args.snapshots}")

    snapshots = [load_issue_snapshot(path) for path in paths]
    output = write_issue_csv(snapshots, args.output, window_days=args.window_days)
    issue_count = sum(len(snapshot.issues) for snapshot in snapshots)
    print(f"Wrote {issue_count} issues from {len(snapshots)} snapshots to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
