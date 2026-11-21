"""Internal commit activity collection command."""

import argparse
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from github import RateLimitExceededException

from reflections import (
    collect_commit_snapshot,
    get_accepted_submissions,
    load_commit_snapshot,
    save_commit_snapshot,
)
from reflections._cli import ProgressBar, github_token
from reflections.datasources.github import create_github


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/github/commits"),
        help="commit snapshot directory (default: data/github/commits)",
    )
    parser.add_argument("--refresh", action="store_true", help="replace snapshots")
    parser.add_argument("--limit", type=int, help="collect only the first N submissions")
    parser.add_argument(
        "--window-days",
        type=int,
        default=365,
        help="days before/after acceptance (default: 365)",
    )
    parser.add_argument(
        "--check-auth",
        action="store_true",
        help="verify authentication and print quota without collecting",
    )
    parser.add_argument(
        "--minimum-post-acceptance-days",
        type=int,
        default=90,
        help="skip packages accepted fewer than this many days ago (default: 90)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit is not None and args.limit <= 0:
        raise SystemExit("--limit must be positive")
    if args.window_days <= 0:
        raise SystemExit("--window-days must be positive")
    if args.minimum_post_acceptance_days < 0:
        raise SystemExit("--minimum-post-acceptance-days must not be negative")

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
    eligible_before = datetime.now(UTC) - timedelta(
        days=args.minimum_post_acceptance_days
    )
    eligible_submissions = tuple(
        submission
        for submission in submissions
        if submission.accepted_at <= eligible_before
    )
    skipped = len(submissions) - len(eligible_submissions)
    if skipped:
        print(
            f"Skipping {skipped} package(s) with fewer than "
            f"{args.minimum_post_acceptance_days} post-acceptance days"
        )
    submissions = eligible_submissions
    if args.limit is not None:
        submissions = submissions[: args.limit]

    failures = 0
    for index, submission in enumerate(submissions, start=1):
        path = args.output / _snapshot_filename(submission.repository)
        partial_path = path.with_suffix(".partial.json")
        prefix = f"[{index}/{len(submissions)}] {submission.repository}"
        if path.exists() and not args.refresh:
            completed = load_commit_snapshot(path)
            if completed.window_days >= args.window_days:
                print(f"{prefix}: using {path}")
                continue

        checkpoint = (
            load_commit_snapshot(partial_path)
            if partial_path.exists() and not args.refresh and not path.exists()
            else None
        )
        resumed = len(checkpoint.commits) if checkpoint is not None else 0
        resume_note = f"; resuming {resumed} cached commits" if resumed else ""
        print(
            f"{prefix}: listing default-branch commits in ±"
            f"{args.window_days}-day window{resume_note}",
            flush=True,
        )
        progress = ProgressBar(prefix, item_name="commit")

        def checkpoint_progress(
            snapshot,
            current,
            total,
            sha,
            cached,
            *,
            partial_path=partial_path,
            progress=progress,
        ):
            if not cached and (current % 25 == 0 or current == total):
                save_commit_snapshot(snapshot, partial_path)
            progress.update(
                current,
                total,
                item_identifier=sha[:8],
                cached=cached,
                remaining=github.rate_limiting[0],
            )

        try:
            snapshot = collect_commit_snapshot(
                submission.repository,
                accepted_at=submission.accepted_at,
                window_days=args.window_days,
                github=github,
                existing_snapshot=checkpoint,
                on_progress=checkpoint_progress,
            )
            save_commit_snapshot(snapshot, path)
            partial_path.unlink(missing_ok=True)
            progress.finish(len(snapshot.commits))
        except KeyboardInterrupt:
            progress.finish_message("interrupted")
            print(f"{prefix}: stopped; rerun to resume", file=sys.stderr)
            return 130
        except RateLimitExceededException:
            progress.finish_message("rate limited")
            reset_at = datetime.fromtimestamp(github.rate_limiting_resettime, UTC)
            print(
                f"{prefix}: rate limit exhausted; stopping until "
                f"{reset_at:%Y-%m-%d %H:%M:%S %Z}",
                file=sys.stderr,
            )
            return 2
        except Exception as error:  # noqa: BLE001 - continue with the cohort
            progress.finish_message("failed")
            failures += 1
            print(f"{prefix}: failed: {error}", file=sys.stderr)

    return 1 if failures else 0


def _snapshot_filename(repository: str) -> str:
    return f"{repository.replace('/', '--').casefold()}.json"


if __name__ == "__main__":
    raise SystemExit(main())
