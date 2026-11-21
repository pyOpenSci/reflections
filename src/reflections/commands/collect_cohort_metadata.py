"""Internal cohort metadata collection command."""

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from github import GithubException, RateLimitExceededException

from reflections import (
    collect_cohort_metadata,
    load_cohort_metadata,
    save_cohort_metadata,
)
from reflections._cli import github_token
from reflections.datasources.github import create_github, load_maintainer_roster


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--roster",
        type=Path,
        default=Path("data/github/maintainers/roster.json"),
        help="cached accepted-package roster",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/github/cohort"),
        help="metadata snapshot directory (default: data/github/cohort)",
    )
    parser.add_argument("--refresh", action="store_true", help="replace snapshots")
    parser.add_argument("--limit", type=int, help="collect only the first N packages")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit is not None and args.limit <= 0:
        raise SystemExit("--limit must be positive")

    submissions, _, _, _ = load_maintainer_roster(args.roster)
    if args.limit is not None:
        submissions = submissions[: args.limit]
    github = create_github(token=github_token())
    remaining, limit = github.rate_limiting
    if limit <= 60:
        raise SystemExit(
            "Authenticated GitHub access is required for batch collection. "
            "Set GITHUB_TOKEN in the environment or in .env."
        )
    print(f"GitHub API quota: {remaining:,}/{limit:,} requests remaining")

    failures = 0
    for index, submission in enumerate(submissions, start=1):
        path = args.output / _snapshot_filename(submission.repository)
        prefix = f"[{index}/{len(submissions)}] {submission.repository}"
        if path.exists() and not args.refresh:
            load_cohort_metadata(path)
            print(f"{prefix}: using {path}")
            continue
        print(f"{prefix}: collecting", flush=True)
        try:
            snapshot = collect_cohort_metadata(submission, github=github)
            save_cohort_metadata(snapshot, path)
            print(f"{prefix}: complete; {github.rate_limiting[0]:,} requests remain")
        except KeyboardInterrupt:
            print(f"{prefix}: interrupted; rerun to resume", file=sys.stderr)
            return 130
        except RateLimitExceededException:
            reset_at = datetime.fromtimestamp(github.rate_limiting_resettime, UTC)
            print(
                f"Rate limit exhausted until {reset_at:%Y-%m-%d %H:%M:%S %Z}",
                file=sys.stderr,
            )
            return 2
        except (GithubException, OSError, ValueError) as error:
            failures += 1
            print(f"{prefix}: failed: {error}", file=sys.stderr)
    return 1 if failures else 0


def _snapshot_filename(repository: str) -> str:
    return f"{repository.replace('/', '--').casefold()}.json"


if __name__ == "__main__":
    raise SystemExit(main())
