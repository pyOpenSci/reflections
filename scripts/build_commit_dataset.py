"""Build a commit-level CSV from local commit snapshots."""

import argparse
from pathlib import Path

from reflections import load_commit_snapshot, write_commit_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--snapshots",
        type=Path,
        default=Path("data/github/commits"),
        help="commit snapshot directory (default: data/github/commits)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/derived/commits.csv"),
        help="CSV path (default: data/derived/commits.csv)",
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
        raise SystemExit(f"No commit snapshots found in {args.snapshots}")

    snapshots = [load_commit_snapshot(path) for path in paths]
    output = write_commit_csv(
        snapshots,
        args.output,
        window_days=args.window_days,
    )
    commit_count = sum(len(snapshot.commits) for snapshot in snapshots)
    print(
        f"Wrote {commit_count} commits from {len(snapshots)} snapshots to {output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
