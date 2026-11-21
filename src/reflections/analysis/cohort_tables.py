"""Create an analysis-ready cohort table from cached metadata."""

from collections.abc import Iterable, Iterator
from pathlib import Path

import pandas as pd

from reflections.datasources.github.models import CohortMetadataSnapshot

COHORT_COLUMNS = (
    "package",
    "repository",
    "issue_number",
    "issue_url",
    "submitted_at",
    "accepted_at",
    "review_days",
    "repository_created_at",
    "repository_age_at_submission_days",
    "repository_age_at_acceptance_days",
    "repository_age_at_snapshot_days",
    "default_branch",
    "last_default_branch_commit_at",
    "days_since_last_default_branch_commit",
    "maintainer_count",
    "repository_archived",
    "repository_is_fork",
    "snapshot_fetched_at",
)


def cohort_rows(
    snapshots: Iterable[CohortMetadataSnapshot],
) -> Iterator[dict[str, object]]:
    """Yield one analysis-ready row per accepted package."""

    for snapshot in snapshots:
        yield {
            "package": snapshot.package,
            "repository": snapshot.repository,
            "issue_number": snapshot.issue_number,
            "issue_url": snapshot.issue_url,
            "submitted_at": snapshot.submitted_at.isoformat(),
            "accepted_at": snapshot.accepted_at.isoformat(),
            "review_days": _days(snapshot.submitted_at, snapshot.accepted_at),
            "repository_created_at": snapshot.repository_created_at.isoformat(),
            "repository_age_at_submission_days": _days(
                snapshot.repository_created_at, snapshot.submitted_at
            ),
            "repository_age_at_acceptance_days": _days(
                snapshot.repository_created_at, snapshot.accepted_at
            ),
            "repository_age_at_snapshot_days": _days(
                snapshot.repository_created_at, snapshot.fetched_at
            ),
            "default_branch": snapshot.default_branch,
            "last_default_branch_commit_at": (
                snapshot.last_default_branch_commit_at.isoformat()
                if snapshot.last_default_branch_commit_at is not None
                else None
            ),
            "days_since_last_default_branch_commit": (
                _days(snapshot.last_default_branch_commit_at, snapshot.fetched_at)
                if snapshot.last_default_branch_commit_at is not None
                else None
            ),
            "maintainer_count": snapshot.maintainer_count,
            "repository_archived": snapshot.repository_archived,
            "repository_is_fork": snapshot.repository_is_fork,
            "snapshot_fetched_at": snapshot.fetched_at.isoformat(),
        }


def write_cohort_csv(
    snapshots: Iterable[CohortMetadataSnapshot], path: str | Path
) -> Path:
    """Write cohort metadata without making GitHub requests."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(cohort_rows(snapshots), key=lambda row: row["accepted_at"])
    pd.DataFrame(rows, columns=COHORT_COLUMNS).to_csv(destination, index=False)
    return destination


def _days(start, end) -> float:
    return (end - start).total_seconds() / 86_400
