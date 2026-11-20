"""Build package-maintainer activity tables from local GitHub snapshots."""

from collections.abc import Iterable, Iterator
import csv
from pathlib import Path
from typing import Any

from reflections.datasources.github.models import (
    MaintainerActivitySnapshot,
    RepositoryContribution,
    Submission,
)

MAINTAINER_COLUMNS = (
    "repository", "package", "accepted_at", "submission_issue_url",
    "requested_login", "canonical_login", "user_exists", "snapshot_fetched_at",
    "observation_start", "observation_end", "last_activity_on",
    "days_since_last_activity", "has_public_activity", "total_public_commits",
    "total_public_issues", "total_public_pull_requests",
    "total_public_pull_request_reviews", "total_observed_public_activity",
    "restricted_contributions", "has_restricted_contributions", "package_commits",
    "package_issues", "package_pull_requests", "package_pull_request_reviews",
    "package_activity_lower_bound", "package_activity_exact",
    "package_activity_share",
)
ROSTER_COLUMNS = (
    "repository", "package", "accepted_at", "submission_issue_url",
    "maintainer_count", "maintainers", "has_maintainer_roster",
)


def maintainer_rows(
    submissions: Iterable[Submission],
    snapshots: Iterable[MaintainerActivitySnapshot],
) -> Iterator[dict[str, Any]]:
    """Yield one row per accepted package and listed maintainer."""

    by_login = {item.requested_login.casefold(): item for item in snapshots}
    for submission in submissions:
        for login in submission.maintainers:
            snapshot = by_login.get(login.casefold())
            if snapshot is None:
                raise ValueError(f"No activity snapshot found for maintainer @{login}")
            repository = _repository_record(snapshot, submission.repository)
            package_counts = {
                "commits": _package_count(
                    repository, "commits", snapshot.commits_truncated
                ),
                "issues": _package_count(
                    repository, "issues", snapshot.issues_truncated
                ),
                "pull_requests": _package_count(
                    repository, "pull_requests", snapshot.pull_requests_truncated
                ),
                "pull_request_reviews": _package_count(
                    repository,
                    "pull_request_reviews",
                    snapshot.pull_request_reviews_truncated,
                ),
            }
            known_activity = sum(
                value for value in package_counts.values() if value is not None
            )
            exact = all(value is not None for value in package_counts.values())
            total = (
                snapshot.total_commits
                + snapshot.total_issues
                + snapshot.total_pull_requests
                + snapshot.total_pull_request_reviews
            )
            yield {
                "repository": submission.repository,
                "package": submission.package,
                "accepted_at": submission.accepted_at.isoformat(),
                "submission_issue_url": submission.issue_url,
                "requested_login": snapshot.requested_login,
                "canonical_login": snapshot.canonical_login or "",
                "user_exists": snapshot.user_exists,
                "snapshot_fetched_at": snapshot.fetched_at.isoformat(),
                "observation_start": snapshot.observation_start.isoformat(),
                "observation_end": snapshot.observation_end.isoformat(),
                "last_activity_on": (
                    "" if snapshot.last_activity_on is None
                    else snapshot.last_activity_on.isoformat()
                ),
                "days_since_last_activity": (
                    None if snapshot.last_activity_on is None
                    else (snapshot.observation_end.date() - snapshot.last_activity_on).days
                ),
                "has_public_activity": total > 0,
                "total_public_commits": snapshot.total_commits,
                "total_public_issues": snapshot.total_issues,
                "total_public_pull_requests": snapshot.total_pull_requests,
                "total_public_pull_request_reviews": snapshot.total_pull_request_reviews,
                "total_observed_public_activity": total,
                "restricted_contributions": snapshot.restricted_contributions,
                "has_restricted_contributions": snapshot.restricted_contributions > 0,
                "package_commits": package_counts["commits"],
                "package_issues": package_counts["issues"],
                "package_pull_requests": package_counts["pull_requests"],
                "package_pull_request_reviews": package_counts["pull_request_reviews"],
                "package_activity_lower_bound": known_activity,
                "package_activity_exact": exact,
                "package_activity_share": (
                    known_activity / total if exact and total > 0 else None
                ),
            }


def roster_rows(submissions: Iterable[Submission]) -> Iterator[dict[str, Any]]:
    for submission in submissions:
        yield {
            "repository": submission.repository,
            "package": submission.package,
            "accepted_at": submission.accepted_at.isoformat(),
            "submission_issue_url": submission.issue_url,
            "maintainer_count": len(submission.maintainers),
            "maintainers": ";".join(submission.maintainers),
            "has_maintainer_roster": bool(submission.maintainers),
        }


def write_maintainer_csvs(
    submissions: Iterable[Submission],
    snapshots: Iterable[MaintainerActivitySnapshot],
    *,
    activity_path: str | Path,
    roster_path: str | Path,
) -> tuple[Path, Path]:
    submission_items = tuple(submissions)
    activity_destination, roster_destination = Path(activity_path), Path(roster_path)
    activity_destination.parent.mkdir(parents=True, exist_ok=True)
    roster_destination.parent.mkdir(parents=True, exist_ok=True)
    activity = sorted(
        maintainer_rows(submission_items, snapshots),
        key=lambda row: (row["repository"].casefold(), row["requested_login"].casefold()),
    )
    roster = sorted(
        roster_rows(submission_items), key=lambda row: row["repository"].casefold()
    )
    _write_csv(activity_destination, MAINTAINER_COLUMNS, activity)
    _write_csv(roster_destination, ROSTER_COLUMNS, roster)
    return activity_destination, roster_destination


def _repository_record(snapshot, repository) -> RepositoryContribution | None:
    return next(
        (item for item in snapshot.repositories
         if item.repository.casefold() == repository.casefold()),
        None,
    )


def _package_count(repository, field: str, truncated: bool) -> int | None:
    value = None if repository is None else getattr(repository, field)
    return value if value is not None else (None if truncated else 0)


def _write_csv(path, columns, rows) -> None:
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
