"""Collect or refresh local snapshots for accepted pyOpenSci packages."""

import argparse
from datetime import UTC, datetime
import os
from pathlib import Path
import sys

from github import RateLimitExceededException

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
    parser.add_argument(
        "--check-auth",
        action="store_true",
        help="verify authentication and print the current quota without collecting",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit is not None and args.limit <= 0:
        raise SystemExit("--limit must be positive")

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
        except RateLimitExceededException:
            reset_at = datetime.fromtimestamp(github.rate_limiting_resettime, UTC)
            print(
                f"{prefix}: GitHub rate limit exhausted; stopping. "
                f"The limit resets at {reset_at:%Y-%m-%d %H:%M:%S %Z}. "
                "Rerun afterward; completed snapshots will be skipped.",
                file=sys.stderr,
            )
            return 2
        except Exception as error:  # Continue so a long batch remains resumable.
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


if __name__ == "__main__":
    raise SystemExit(main())
