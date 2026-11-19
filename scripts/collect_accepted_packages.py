"""Collect or refresh local snapshots for accepted pyOpenSci packages."""

import argparse
from pathlib import Path
import sys

from reflections import (
    collect_repository_snapshot,
    get_accepted_submissions,
    save_snapshot,
)
from reflections.datasources.github import create_github


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/github"),
        help="snapshot directory (default: data/github)",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="replace snapshots that already exist",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="collect only the first N submissions (useful for a trial run)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit is not None and args.limit <= 0:
        raise SystemExit("--limit must be positive")

    github = create_github()
    submissions = get_accepted_submissions(github=github, on_unsupported="warn")
    if args.limit is not None:
        submissions = submissions[: args.limit]

    failures = 0
    for index, submission in enumerate(submissions, start=1):
        path = args.output / _snapshot_filename(submission.repository)
        prefix = f"[{index}/{len(submissions)}] {submission.repository}"
        if path.exists() and not args.refresh:
            print(f"{prefix}: using {path}")
            continue

        print(f"{prefix}: collecting", flush=True)
        try:
            snapshot = collect_repository_snapshot(
                submission.repository,
                accepted_at=submission.accepted_at,
                github=github,
            )
            save_snapshot(snapshot, path)
        except Exception as error:  # Continue so a long batch remains resumable.
            failures += 1
            print(f"{prefix}: failed: {error}", file=sys.stderr)

    if failures:
        print(f"Collection completed with {failures} failure(s).", file=sys.stderr)
        return 1
    return 0


def _snapshot_filename(repository: str) -> str:
    return f"{repository.replace('/', '--').casefold()}.json"


if __name__ == "__main__":
    raise SystemExit(main())
