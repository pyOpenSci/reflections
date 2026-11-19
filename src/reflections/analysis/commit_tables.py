"""Build commit-level tables from local snapshots."""

from collections.abc import Iterable, Iterator
import csv
from pathlib import Path
from typing import Any

from reflections.datasources.github.models import CommitSnapshot

COMMIT_COLUMNS = (
    "repository",
    "default_branch",
    "snapshot_fetched_at",
    "snapshot_window_days",
    "analysis_window_days",
    "accepted_at",
    "sha",
    "url",
    "message",
    "authored_at",
    "committed_at",
    "author_login",
    "committer_login",
    "author_name",
    "committer_name",
    "author_identity",
    "parent_count",
    "is_merge",
    "author_is_bot",
    "committer_is_bot",
    "period",
    "days_from_acceptance",
    "within_window",
)


def commit_rows(
    snapshots: Iterable[CommitSnapshot],
    *,
    window_days: int = 365,
) -> Iterator[dict[str, Any]]:
    """Yield one analysis-ready row per default-branch commit."""

    if window_days <= 0:
        raise ValueError("window_days must be positive")

    for snapshot in snapshots:
        if window_days > snapshot.window_days:
            raise ValueError(
                f"Requested {window_days}-day analysis window exceeds the "
                f"{snapshot.window_days}-day snapshot window for {snapshot.repository}"
            )
        for commit in snapshot.commits:
            days_from_acceptance = (
                commit.committed_at - snapshot.accepted_at
            ).total_seconds() / 86_400
            yield {
                "repository": snapshot.repository,
                "default_branch": snapshot.default_branch,
                "snapshot_fetched_at": snapshot.fetched_at.isoformat(),
                "snapshot_window_days": snapshot.window_days,
                "analysis_window_days": window_days,
                "accepted_at": snapshot.accepted_at.isoformat(),
                "sha": commit.sha,
                "url": commit.url,
                "message": commit.message,
                "authored_at": _optional_datetime(commit.authored_at),
                "committed_at": commit.committed_at.isoformat(),
                "author_login": commit.author_login or "",
                "committer_login": commit.committer_login or "",
                "author_name": commit.author_name or "",
                "committer_name": commit.committer_name or "",
                "author_identity": commit.author_login or commit.author_name or "",
                "parent_count": commit.parent_count,
                "is_merge": commit.is_merge,
                "author_is_bot": commit.author_is_bot,
                "committer_is_bot": commit.committer_is_bot,
                "period": (
                    "after_acceptance"
                    if commit.committed_at > snapshot.accepted_at
                    else "before_acceptance"
                ),
                "days_from_acceptance": days_from_acceptance,
                "within_window": abs(days_from_acceptance) <= window_days,
            }


def write_commit_csv(
    snapshots: Iterable[CommitSnapshot],
    path: str | Path,
    *,
    window_days: int = 365,
) -> Path:
    """Write a deterministic commit-level CSV from local snapshots."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(
        commit_rows(snapshots, window_days=window_days),
        key=lambda row: (
            row["repository"].casefold(),
            row["committed_at"],
            row["sha"],
        ),
    )
    with destination.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=COMMIT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return destination


def _optional_datetime(value: Any | None) -> str:
    return "" if value is None else value.isoformat()
