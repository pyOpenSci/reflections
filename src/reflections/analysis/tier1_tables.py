"""Build analysis tables from complete Tier 1 GitHub history indexes."""

import csv
from collections.abc import Iterable, Iterator, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from reflections.datasources.github.models import HistoryIndexSnapshot

COMMON_COLUMNS = (
    "repository",
    "package",
    "snapshot_fetched_at",
    "accepted_at",
    "analysis_window_days",
    "post_acceptance_observation_days",
    "eligible_followup",
    "number",
    "title",
    "url",
    "author_login",
    "created_at",
    "updated_at",
    "closed_at",
    "state",
    "comment_count",
    "is_closed",
    "time_to_close_days",
    "observed_open_days",
    "resolution_censored",
    "period",
    "days_from_acceptance",
    "within_window",
)

TIER1_ISSUE_COLUMNS = COMMON_COLUMNS
TIER1_PULL_REQUEST_COLUMNS = COMMON_COLUMNS + (
    "merged_at",
    "outcome",
    "is_merged",
    "time_to_merge_days",
    "review_comment_count",
    "is_draft",
)


def tier1_issue_rows(
    snapshots: Iterable[HistoryIndexSnapshot],
    *,
    accepted_at: Mapping[str, datetime],
    packages: Mapping[str, str] | None = None,
    window_days: int = 90,
) -> Iterator[dict[str, Any]]:
    """Yield full-history issue rows with configurable analysis flags."""

    yield from _tier1_rows(
        snapshots,
        entity_type="issues",
        accepted_at=accepted_at,
        packages=packages,
        window_days=window_days,
    )


def tier1_pull_request_rows(
    snapshots: Iterable[HistoryIndexSnapshot],
    *,
    accepted_at: Mapping[str, datetime],
    packages: Mapping[str, str] | None = None,
    window_days: int = 90,
) -> Iterator[dict[str, Any]]:
    """Yield full-history pull-request rows with configurable analysis flags."""

    yield from _tier1_rows(
        snapshots,
        entity_type="pull_requests",
        accepted_at=accepted_at,
        packages=packages,
        window_days=window_days,
    )


def write_tier1_issue_csv(
    snapshots: Iterable[HistoryIndexSnapshot],
    path: str | Path,
    *,
    accepted_at: Mapping[str, datetime],
    packages: Mapping[str, str] | None = None,
    window_days: int = 90,
) -> Path:
    """Write a deterministic issue table from Tier 1 snapshots."""

    return _write_rows(
        tier1_issue_rows(
            snapshots,
            accepted_at=accepted_at,
            packages=packages,
            window_days=window_days,
        ),
        TIER1_ISSUE_COLUMNS,
        path,
    )


def write_tier1_pull_request_csv(
    snapshots: Iterable[HistoryIndexSnapshot],
    path: str | Path,
    *,
    accepted_at: Mapping[str, datetime],
    packages: Mapping[str, str] | None = None,
    window_days: int = 90,
) -> Path:
    """Write a deterministic pull-request table from Tier 1 snapshots."""

    return _write_rows(
        tier1_pull_request_rows(
            snapshots,
            accepted_at=accepted_at,
            packages=packages,
            window_days=window_days,
        ),
        TIER1_PULL_REQUEST_COLUMNS,
        path,
    )


def _tier1_rows(
    snapshots,
    *,
    entity_type,
    accepted_at,
    packages,
    window_days,
):
    if window_days <= 0:
        raise ValueError("window_days must be positive")
    normalized_acceptance = {
        repository.casefold(): value for repository, value in accepted_at.items()
    }
    normalized_packages = {
        repository.casefold(): value for repository, value in (packages or {}).items()
    }
    for snapshot in snapshots:
        if snapshot.entity_type != entity_type:
            raise ValueError(
                f"Expected {entity_type} snapshot; got {snapshot.entity_type} "
                f"for {snapshot.repository}"
            )
        if not snapshot.complete:
            raise ValueError(f"Tier 1 snapshot is incomplete for {snapshot.repository}")
        key = snapshot.repository.casefold()
        if key not in normalized_acceptance:
            raise ValueError(f"No acceptance date found for {snapshot.repository}")
        acceptance = normalized_acceptance[key]
        followup_days = _elapsed_days(acceptance, snapshot.fetched_at)
        eligible = followup_days >= window_days
        package = normalized_packages.get(
            key,
            snapshot.repository.rsplit("/", 1)[-1],
        )
        for record in snapshot.records:
            days_from_acceptance = _elapsed_days(acceptance, record.created_at)
            observation_end = record.closed_at or snapshot.fetched_at
            row = {
                "repository": snapshot.repository,
                "package": package,
                "snapshot_fetched_at": snapshot.fetched_at.isoformat(),
                "accepted_at": acceptance.isoformat(),
                "analysis_window_days": window_days,
                "post_acceptance_observation_days": followup_days,
                "eligible_followup": eligible,
                "number": record.number,
                "title": record.title,
                "url": record.url,
                "author_login": record.author_login or "",
                "created_at": record.created_at.isoformat(),
                "updated_at": record.updated_at.isoformat(),
                "closed_at": _optional_datetime(record.closed_at),
                "state": record.state,
                "comment_count": record.comment_count,
                "is_closed": record.closed_at is not None,
                "time_to_close_days": _optional_elapsed_days(
                    record.created_at,
                    record.closed_at,
                ),
                "observed_open_days": _elapsed_days(
                    record.created_at,
                    observation_end,
                ),
                "resolution_censored": record.closed_at is None,
                "period": (
                    "after_acceptance"
                    if record.created_at > acceptance
                    else "before_acceptance"
                ),
                "days_from_acceptance": days_from_acceptance,
                "within_window": abs(days_from_acceptance) <= window_days,
            }
            if entity_type == "pull_requests":
                row.update(
                    {
                        "merged_at": _optional_datetime(record.merged_at),
                        "outcome": _pull_request_outcome(record),
                        "is_merged": record.merged_at is not None,
                        "time_to_merge_days": _optional_elapsed_days(
                            record.created_at,
                            record.merged_at,
                        ),
                        "review_comment_count": record.review_comment_count,
                        "is_draft": record.is_draft,
                    }
                )
            yield row


def _write_rows(rows, columns, path):
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(
        rows,
        key=lambda row: (row["repository"].casefold(), row["number"]),
    )
    with destination.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        writer.writerows(ordered)
    return destination


def _optional_datetime(value: datetime | None) -> str:
    return "" if value is None else value.isoformat()


def _elapsed_days(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / 86_400


def _optional_elapsed_days(start: datetime, end: datetime | None) -> float | None:
    return None if end is None else _elapsed_days(start, end)


def _pull_request_outcome(record: Any) -> str:
    if record.merged_at is not None:
        return "merged"
    if record.closed_at is not None:
        return "closed_unmerged"
    return "open"
