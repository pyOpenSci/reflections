"""Build a PR-level CSV from local GitHub snapshots."""

import argparse
from pathlib import Path

from reflections.analysis import write_pull_request_csv
from reflections import load_snapshot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--snapshots",
        type=Path,
        default=Path("data/github"),
        help="snapshot directory (default: data/github)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/derived/pull_requests.csv"),
        help="CSV path (default: data/derived/pull_requests.csv)",
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
    paths = sorted(args.snapshots.glob("*.json"))
    if not paths:
        raise SystemExit(f"No snapshots found in {args.snapshots}")

    snapshots = [load_snapshot(path) for path in paths]
    output = write_pull_request_csv(
        snapshots,
        args.output,
        window_days=args.window_days,
    )
    pull_request_count = sum(len(snapshot.pull_requests) for snapshot in snapshots)
    print(
        f"Wrote {pull_request_count} pull requests from "
        f"{len(snapshots)} snapshots to {output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
