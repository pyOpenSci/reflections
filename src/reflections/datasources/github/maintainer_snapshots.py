"""Persist maintainer rosters and contribution activity snapshots."""

from datetime import date, datetime
import json
from pathlib import Path
from typing import Any

from .models import (
    MaintainerActivitySnapshot,
    RepositoryContribution,
    Submission,
)

SUPPORTED_SCHEMA_VERSION = 1


def save_maintainer_activity(
    snapshot: MaintainerActivitySnapshot,
    path: str | Path,
) -> Path:
    """Atomically write one maintainer activity snapshot."""

    return _atomic_json_write(path, _activity_to_dict(snapshot))


def load_maintainer_activity(path: str | Path) -> MaintainerActivitySnapshot:
    """Load one maintainer activity snapshot."""

    data = _read_versioned_json(path)
    return MaintainerActivitySnapshot(
        schema_version=data["schema_version"],
        requested_login=data["requested_login"],
        canonical_login=data["canonical_login"],
        user_exists=data["user_exists"],
        fetched_at=datetime.fromisoformat(data["fetched_at"]),
        observation_start=datetime.fromisoformat(data["observation_start"]),
        observation_end=datetime.fromisoformat(data["observation_end"]),
        total_commits=data["total_commits"],
        total_issues=data["total_issues"],
        total_pull_requests=data["total_pull_requests"],
        total_pull_request_reviews=data["total_pull_request_reviews"],
        restricted_contributions=data["restricted_contributions"],
        last_activity_on=(
            None
            if data["last_activity_on"] is None
            else date.fromisoformat(data["last_activity_on"])
        ),
        repositories=tuple(
            RepositoryContribution(
                repository=item["repository"],
                commits=item["commits"],
                issues=item["issues"],
                pull_requests=item["pull_requests"],
                pull_request_reviews=item["pull_request_reviews"],
            )
            for item in data["repositories"]
        ),
        commits_truncated=data["commits_truncated"],
        issues_truncated=data["issues_truncated"],
        pull_requests_truncated=data["pull_requests_truncated"],
        pull_request_reviews_truncated=data["pull_request_reviews_truncated"],
        graphql_rate_remaining=data.get("graphql_rate_remaining"),
    )


def save_maintainer_roster(
    submissions: tuple[Submission, ...],
    *,
    observation_start: datetime,
    observation_end: datetime,
    fetched_at: datetime,
    path: str | Path,
) -> Path:
    """Save the package-to-maintainer roster and fixed observation window."""

    data = {
        "schema_version": SUPPORTED_SCHEMA_VERSION,
        "fetched_at": fetched_at.isoformat(),
        "observation_start": observation_start.isoformat(),
        "observation_end": observation_end.isoformat(),
        "submissions": [
            {
                "package": submission.package,
                "repository": submission.repository,
                "accepted_at": submission.accepted_at.isoformat(),
                "issue_number": submission.issue_number,
                "issue_url": submission.issue_url,
                "title": submission.title,
                "maintainers": list(submission.maintainers),
            }
            for submission in submissions
        ],
    }
    return _atomic_json_write(path, data)


def load_maintainer_roster(
    path: str | Path,
) -> tuple[tuple[Submission, ...], datetime, datetime, datetime]:
    """Load roster, observation start/end, and roster fetch time."""

    data = _read_versioned_json(path)
    submissions = tuple(
        Submission(
            package=item["package"],
            repository=item["repository"],
            accepted_at=datetime.fromisoformat(item["accepted_at"]),
            issue_number=item["issue_number"],
            issue_url=item["issue_url"],
            title=item["title"],
            maintainers=tuple(item["maintainers"]),
        )
        for item in data["submissions"]
    )
    return (
        submissions,
        datetime.fromisoformat(data["observation_start"]),
        datetime.fromisoformat(data["observation_end"]),
        datetime.fromisoformat(data["fetched_at"]),
    )


def _activity_to_dict(snapshot: MaintainerActivitySnapshot) -> dict[str, Any]:
    return {
        "schema_version": snapshot.schema_version,
        "requested_login": snapshot.requested_login,
        "canonical_login": snapshot.canonical_login,
        "user_exists": snapshot.user_exists,
        "fetched_at": snapshot.fetched_at.isoformat(),
        "observation_start": snapshot.observation_start.isoformat(),
        "observation_end": snapshot.observation_end.isoformat(),
        "total_commits": snapshot.total_commits,
        "total_issues": snapshot.total_issues,
        "total_pull_requests": snapshot.total_pull_requests,
        "total_pull_request_reviews": snapshot.total_pull_request_reviews,
        "restricted_contributions": snapshot.restricted_contributions,
        "last_activity_on": (
            None
            if snapshot.last_activity_on is None
            else snapshot.last_activity_on.isoformat()
        ),
        "repositories": [
            {
                "repository": item.repository,
                "commits": item.commits,
                "issues": item.issues,
                "pull_requests": item.pull_requests,
                "pull_request_reviews": item.pull_request_reviews,
            }
            for item in snapshot.repositories
        ],
        "commits_truncated": snapshot.commits_truncated,
        "issues_truncated": snapshot.issues_truncated,
        "pull_requests_truncated": snapshot.pull_requests_truncated,
        "pull_request_reviews_truncated": (
            snapshot.pull_request_reviews_truncated
        ),
        "graphql_rate_remaining": snapshot.graphql_rate_remaining,
    }


def _read_versioned_json(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported maintainer snapshot schema {data.get('schema_version')!r}"
        )
    return data


def _atomic_json_write(path: str | Path, data: dict[str, Any]) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)
    return destination
