"""Collect or refresh local snapshots for accepted pyOpenSci packages."""

import argparse
from datetime import UTC, datetime
from pathlib import Path
import sys

from github import RateLimitExceededException

from reflections._cli import ProgressBar, github_token
from reflections import (
    collect_repository_snapshot,
    get_accepted_submissions,
    load_snapshot,
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
    parser.add_argument(
        "--check-auth",
        action="store_true",
        help="verify authentication and print the current quota without collecting",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=365,
        help="collect PRs this many days before/after acceptance (default: 365)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit is not None and args.limit <= 0:
        raise SystemExit("--limit must be positive")
    if args.window_days <= 0:
        raise SystemExit("--window-days must be positive")

    github = create_github(token=github_token())
    remaining, limit = github.rate_limiting
    if limit <= 60:
        raise SystemExit(
            "Authenticated GitHub access is required for batch collection. "
            "Set GITHUB_TOKEN in the environment or in .env."
        )
    print(f"GitHub API quota: {remaining:,}/{limit:,} requests remaining")
    if args.check_auth:
        return 0

    submissions = get_accepted_submissions(github=github, on_unsupported="warn")
    if args.limit is not None:
        submissions = submissions[: args.limit]

    failures = 0
    for index, submission in enumerate(submissions, start=1):
        path = args.output / _snapshot_filename(submission.repository)
        partial_path = path.with_suffix(".partial.json")
        prefix = f"[{index}/{len(submissions)}] {submission.repository}"
        if path.exists() and not args.refresh:
            completed_snapshot = load_snapshot(path)
            if (
                completed_snapshot.window_days is None
                or completed_snapshot.window_days >= args.window_days
            ):
                print(f"{prefix}: using {path}")
                continue
            print(
                f"{prefix}: existing snapshot covers ±"
                f"{completed_snapshot.window_days} days; recollecting for ±"
                f"{args.window_days} days"
            )

        checkpoint = (
            load_snapshot(partial_path)
            if partial_path.exists()
            and not args.refresh
            and not path.exists()
            else None
        )
        resumed = len(checkpoint.pull_requests) if checkpoint is not None else 0
        resume_note = f"; resuming {resumed} cached PRs" if resumed else ""
        print(
            f"{prefix}: scanning ±{args.window_days}-day window{resume_note}",
            flush=True,
        )
        progress = ProgressBar(prefix, item_name="PR")

        def checkpoint_progress(
            snapshot,
            completed,
            total,
            pull_request_number,
            cached,
        ):
            if not cached:
                save_snapshot(snapshot, partial_path)
            progress.update(
                completed,
                total,
                item_identifier=f"#{pull_request_number}",
                cached=cached,
                remaining=github.rate_limiting[0],
            )

        try:
            snapshot = collect_repository_snapshot(
                submission.repository,
                accepted_at=submission.accepted_at,
                github=github,
                window_days=args.window_days,
                existing_snapshot=checkpoint,
                on_progress=checkpoint_progress,
            )
            save_snapshot(snapshot, path)
            partial_path.unlink(missing_ok=True)
            progress.finish(len(snapshot.pull_requests))
        except KeyboardInterrupt:
            progress.finish_message("interrupted")
            print(
                f"{prefix}: stopped; rerun the command to resume from {partial_path}",
                file=sys.stderr,
            )
            return 130
        except RateLimitExceededException:
            progress.finish_message("rate limited")
            reset_at = datetime.fromtimestamp(github.rate_limiting_resettime, UTC)
            print(
                f"{prefix}: GitHub rate limit exhausted; stopping. "
                f"The limit resets at {reset_at:%Y-%m-%d %H:%M:%S %Z}. "
                "Rerun afterward; completed snapshots will be skipped.",
                file=sys.stderr,
            )
            return 2
        except Exception as error:  # Continue so a long batch remains resumable.
            progress.finish_message("failed")
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
