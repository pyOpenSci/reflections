"""Collect recent public GitHub activity for accepted-package maintainers."""

import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys

from github import RateLimitExceededException

from reflections import (
    collect_maintainer_activity,
    get_accepted_submissions,
    load_maintainer_activity,
    load_maintainer_roster,
    save_maintainer_activity,
    save_maintainer_roster,
)
from reflections._cli import ProgressBar, github_token
from reflections.datasources.github import create_github


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path("data/github/maintainers")
    )
    parser.add_argument("--window-days", type=int, default=365)
    parser.add_argument("--refresh", action="store_true", help="replace snapshots")
    parser.add_argument("--limit", type=int, help="collect only the first N users")
    parser.add_argument("--check-auth", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.window_days <= 0 or args.window_days > 365:
        raise SystemExit("--window-days must be between 1 and 365")
    if args.limit is not None and args.limit <= 0:
        raise SystemExit("--limit must be positive")

    github = create_github(token=github_token())
    remaining, limit = github.rate_limiting
    if limit <= 60:
        raise SystemExit("Authenticated GitHub access is required")
    print(f"GitHub REST quota: {remaining:,}/{limit:,} requests remaining")
    if args.check_auth:
        return 0

    roster_path = args.output / "roster.json"
    if roster_path.exists() and not args.refresh:
        submissions, observation_start, observation_end, _ = load_maintainer_roster(
            roster_path
        )
    else:
        observation_end = datetime.now(UTC)
        observation_start = observation_end - timedelta(days=args.window_days)
        submissions = get_accepted_submissions(github=github, on_unsupported="warn")
        save_maintainer_roster(
            submissions,
            observation_start=observation_start,
            observation_end=observation_end,
            fetched_at=datetime.now(UTC),
            path=roster_path,
        )

    missing_rosters = [item.repository for item in submissions if not item.maintainers]
    if missing_rosters:
        print(
            f"Warning: {len(missing_rosters)} package(s) have no parsed roster; "
            f"see {roster_path}",
            file=sys.stderr,
        )
    logins = sorted(
        {login for item in submissions for login in item.maintainers},
        key=str.casefold,
    )
    if args.limit is not None:
        logins = logins[: args.limit]
    if not logins:
        raise SystemExit("No maintainer GitHub handles were found")

    failures = 0
    progress = ProgressBar("Maintainer activity", item_name="user")
    for index, login in enumerate(logins, start=1):
        path = args.output / "users" / f"{login.casefold()}.json"
        cached = False
        snapshot = None
        if path.exists() and not args.refresh:
            candidate = load_maintainer_activity(path)
            if (
                candidate.observation_start == observation_start
                and candidate.observation_end == observation_end
            ):
                snapshot = candidate
                cached = True
        try:
            if snapshot is None:
                snapshot = collect_maintainer_activity(
                    login,
                    observation_start=observation_start,
                    observation_end=observation_end,
                    github=github,
                )
                save_maintainer_activity(snapshot, path)
            progress.update(
                index,
                len(logins),
                item_identifier=f"@{login}",
                cached=cached,
                remaining=snapshot.graphql_rate_remaining or 0,
            )
        except KeyboardInterrupt:
            progress.finish_message("interrupted")
            return 130
        except RateLimitExceededException:
            progress.finish_message("rate limited")
            return 2
        except Exception as error:
            failures += 1
            print(f"@{login}: failed: {error}", file=sys.stderr)

    progress.finish(len(logins) - failures)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
