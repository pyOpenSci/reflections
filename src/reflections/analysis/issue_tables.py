"""Build issue-level analysis tables from local snapshots."""

from collections.abc import Iterable, Iterator
import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from reflections.datasources.github.models import IssueSnapshot
from reflections.metrics.issue_times import IssueResponsePolicy, calculate_issue_times

ISSUE_COLUMNS = (
    "repository",
    "package",
    "snapshot_fetched_at",
    "snapshot_window_days",
    "accepted_at",
    "issue_number",
    "title",
    "url",
    "author_login",
    "created_at",
    "closed_at",
    "is_closed",
    "time_to_close_days",
    "observed_open_days",
    "resolution_censored",
    "period",
    "days_from_acceptance",
    "within_window",
    "first_acknowledgement_at",
    "acknowledgement_days",
    "has_acknowledgement",
    "first_triage_at",
    "triage_days",
    "has_triage",
    "first_addressed_at",
    "addressed_days",
    "has_been_addressed",
    "addressed_observation_days",
    "addressed_censored",
)


def issue_rows(
    snapshots: Iterable[IssueSnapshot],
    *,
    window_days: int = 365,
    policy: IssueResponsePolicy | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield one analysis-ready row per issue, retaining censored issues."""

    if window_days <= 0:
        raise ValueError("window_days must be positive")

    for snapshot in snapshots:
        if window_days > snapshot.window_days:
            raise ValueError(
                f"Requested {window_days}-day analysis window exceeds the "
                f"{snapshot.window_days}-day snapshot window for {snapshot.repository}"
            )
        timing_by_number = {
            timing.number: timing
            for timing in calculate_issue_times(snapshot, policy=policy)
        }
        for issue in snapshot.issues:
            timing = timing_by_number[issue.number]
            days_from_acceptance = _elapsed_days(snapshot.accepted_at, issue.created_at)
            resolution_end = issue.closed_at or snapshot.fetched_at
            addressed_end = (
                timing.first_addressed_at or issue.closed_at or snapshot.fetched_at
            )
            yield {
                "repository": snapshot.repository,
                "package": snapshot.repository.rsplit("/", 1)[-1],
                "snapshot_fetched_at": snapshot.fetched_at.isoformat(),
                "snapshot_window_days": snapshot.window_days,
                "accepted_at": snapshot.accepted_at.isoformat(),
                "issue_number": issue.number,
                "title": issue.title,
                "url": issue.url,
                "author_login": issue.author_login or "",
                "created_at": issue.created_at.isoformat(),
                "closed_at": _optional_datetime(issue.closed_at),
                "is_closed": issue.closed_at is not None,
                "time_to_close_days": _elapsed_days(issue.created_at, issue.closed_at),
                "observed_open_days": _elapsed_days(issue.created_at, resolution_end),
                "resolution_censored": issue.closed_at is None,
                "period": timing.period,
                "days_from_acceptance": days_from_acceptance,
                "within_window": abs(days_from_acceptance) <= window_days,
                "first_acknowledgement_at": _optional_datetime(
                    timing.first_acknowledgement_at
                ),
                "acknowledgement_days": timing.acknowledgement_days,
                "has_acknowledgement": timing.first_acknowledgement_at is not None,
                "first_triage_at": _optional_datetime(timing.first_triage_at),
                "triage_days": timing.triage_days,
                "has_triage": timing.first_triage_at is not None,
                "first_addressed_at": _optional_datetime(timing.first_addressed_at),
                "addressed_days": timing.addressed_days,
                "has_been_addressed": timing.first_addressed_at is not None,
                "addressed_observation_days": _elapsed_days(
                    issue.created_at,
                    addressed_end,
                ),
                "addressed_censored": timing.first_addressed_at is None,
            }


def write_issue_csv(
    snapshots: Iterable[IssueSnapshot],
    path: str | Path,
    *,
    window_days: int = 365,
    policy: IssueResponsePolicy | None = None,
) -> Path:
    """Write a deterministic issue-level CSV from local snapshots."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(
        issue_rows(snapshots, window_days=window_days, policy=policy),
        key=lambda row: (row["repository"].casefold(), row["issue_number"]),
    )
    with destination.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=ISSUE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return destination


def _optional_datetime(value: datetime | None) -> str:
    return "" if value is None else value.isoformat()


def _elapsed_days(start: datetime, end: datetime | None) -> float | None:
    if end is None:
        return None
    return (end - start).total_seconds() / 86_400
