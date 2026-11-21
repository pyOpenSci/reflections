"""Internal Tier 1 dataset build command."""

import argparse
from pathlib import Path

from reflections.analysis.tier1_tables import (
    write_tier1_issue_csv,
    write_tier1_pull_request_csv,
)
from reflections.datasources.github import load_history_index
from reflections.workflows import load_cohort, repository_cache_key


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", type=Path, default=Path("data/derived/cohort.csv"))
    parser.add_argument(
        "--indexes",
        type=Path,
        default=Path("data/github/history_indexes"),
    )
    parser.add_argument(
        "--issue-output",
        type=Path,
        default=Path("data/derived/tier1_issues.csv"),
    )
    parser.add_argument(
        "--pr-output",
        type=Path,
        default=Path("data/derived/tier1_pull_requests.csv"),
    )
    parser.add_argument("--window-days", type=int, default=90)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.window_days <= 0:
        raise SystemExit("--window-days must be positive")
    try:
        cohort = load_cohort(args.cohort)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    repositories = [item.repository for item in cohort]
    accepted_at = {item.repository: item.accepted_at for item in cohort}
    packages = {item.repository: item.package for item in cohort}
    issue_snapshots = _snapshots(args.indexes, "issues", repositories)
    pull_request_snapshots = _snapshots(
        args.indexes,
        "pull_requests",
        repositories,
    )
    issue_path = write_tier1_issue_csv(
        issue_snapshots,
        args.issue_output,
        accepted_at=accepted_at,
        packages=packages,
        window_days=args.window_days,
    )
    pr_path = write_tier1_pull_request_csv(
        pull_request_snapshots,
        args.pr_output,
        accepted_at=accepted_at,
        packages=packages,
        window_days=args.window_days,
    )
    eligible = sum(
        (snapshot.fetched_at - accepted_at[snapshot.repository]).total_seconds()
        / 86_400
        >= args.window_days
        for snapshot in issue_snapshots
    )
    print(
        f"Wrote {sum(len(snapshot.records) for snapshot in issue_snapshots):,} "
        f"issues to {issue_path}"
    )
    print(
        f"Wrote {sum(len(snapshot.records) for snapshot in pull_request_snapshots):,} "
        f"pull requests to {pr_path}"
    )
    print(
        f"Analysis window: ±{args.window_days} days; "
        f"eligible follow-up: {eligible}/{len(repositories)} repositories"
    )
    return 0


def _snapshots(directory: Path, entity: str, repositories: list[str]):
    snapshots = []
    for repository in repositories:
        key = repository_cache_key(repository)
        path = directory / entity / f"{key}.json"
        if not path.exists():
            raise SystemExit(f"Missing complete Tier 1 snapshot: {path}")
        snapshot = load_history_index(path)
        if not snapshot.complete:
            raise SystemExit(f"Incomplete Tier 1 snapshot: {path}")
        snapshots.append(snapshot)
    return snapshots


if __name__ == "__main__":
    raise SystemExit(main())
