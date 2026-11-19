"""Collect or refresh local snapshots for accepted pyOpenSci packages."""

import argparse
from datetime import UTC, datetime
import os
from pathlib import Path
import sys
import time

from github import RateLimitExceededException

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

    github = create_github(token=_github_token())
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
        progress = ProgressBar(prefix)

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
                pull_request_number=pull_request_number,
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


def _github_token(dotenv_path: Path = Path(".env")) -> str | None:
    """Read GitHub credentials without exposing or broadly loading .env."""

    token = os.getenv("GITHUB_TOKEN") or os.getenv("github_pat")
    if token or not dotenv_path.exists():
        return token

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.removeprefix("export ").split("=", 1)
        if key.strip() in {"GITHUB_TOKEN", "github_pat"}:
            return value.strip().strip("'\"") or None
    return None


class ProgressBar:
    """A dependency-free terminal progress bar for repository collection."""

    width = 24

    def __init__(self, label: str):
        self.label = label
        self.started_at = time.monotonic()
        self._last_non_terminal_update = 0

    def update(
        self,
        current: int,
        total: int,
        *,
        pull_request_number: int,
        cached: bool,
        remaining: int,
    ) -> None:
        if not sys.stdout.isatty():
            interval = max(1, total // 20)
            if current != total and current - self._last_non_terminal_update < interval:
                return
            self._last_non_terminal_update = current
            print(
                f"{self.label}: PR {current}/{total} "
                f"(#{pull_request_number}, quota {remaining:,})"
                + (" [cached]" if cached else ""),
                flush=True,
            )
            return

        fraction = current / total if total else 1
        filled = round(self.width * fraction)
        bar = "#" * filled + "-" * (self.width - filled)
        elapsed = _format_elapsed(time.monotonic() - self.started_at)
        cached_note = " cached" if cached else ""
        print(
            f"\r{self.label} [{bar}] {current}/{total} "
            f"PR #{pull_request_number}{cached_note} | {elapsed} | quota {remaining:,}",
            end="",
            flush=True,
        )

    def finish(self, pull_request_count: int) -> None:
        self.finish_message(f"saved {pull_request_count} PRs")

    def finish_message(self, message: str) -> None:
        if sys.stdout.isatty():
            print()
        elapsed = _format_elapsed(time.monotonic() - self.started_at)
        print(f"{self.label}: {message} in {elapsed}", flush=True)


def _format_elapsed(seconds: float) -> str:
    minutes, whole_seconds = divmod(round(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{whole_seconds:02d}"
    return f"{minutes:02d}:{whole_seconds:02d}"


if __name__ == "__main__":
    raise SystemExit(main())
