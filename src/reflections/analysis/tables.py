"""Build analysis-ready tables without making network requests."""

from collections.abc import Iterable, Iterator
import csv
from pathlib import Path
from typing import Any

from reflections.datasources.github.models import RepositorySnapshot
from reflections.metrics import MaintainerResponsePolicy, calculate_first_response_times

PULL_REQUEST_COLUMNS = (
    "repository",
    "package",
    "snapshot_fetched_at",
    "snapshot_window_days",
    "accepted_at",
    "pr_number",
    "title",
    "url",
    "author_login",
    "created_at",
    "closed_at",
    "merged_at",
    "outcome",
    "is_closed",
    "is_merged",
    "time_to_close_days",
    "time_to_merge_days",
    "observed_open_days",
    "resolution_censored",
    "period",
    "days_from_acceptance",
    "within_window",
    "first_response_at",
    "response_days",
    "response_observation_days",
    "response_censored",
    "has_response",
)


def pull_request_rows(
    snapshots: Iterable[RepositorySnapshot],
    *,
    window_days: int = 365,
    policy: MaintainerResponsePolicy | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield one analysis-ready row per pull request.

    ``within_window`` identifies PRs opened within the matched interval before
    or after acceptance. All PRs remain in the output so alternate windows can
    be derived without recollecting GitHub data.
    """

    if window_days <= 0:
        raise ValueError("window_days must be positive")

    for snapshot in snapshots:
        if snapshot.window_days is not None and window_days > snapshot.window_days:
            raise ValueError(
                f"Requested {window_days}-day analysis window exceeds the "
                f"{snapshot.window_days}-day snapshot window for {snapshot.repository}"
            )
        response_times = {
            result.number: result
            for result in calculate_first_response_times(snapshot, policy=policy)
        }
        for pull_request in snapshot.pull_requests:
            response = response_times[pull_request.number]
            observation_end = pull_request.closed_at or snapshot.fetched_at
            response_observation_end = (
                response.first_response_at or pull_request.closed_at or snapshot.fetched_at
            )
            days_from_acceptance = (
                pull_request.created_at - snapshot.accepted_at
            ).total_seconds() / 86_400
            yield {
                "repository": snapshot.repository,
                "package": snapshot.repository.rsplit("/", 1)[-1],
                "snapshot_fetched_at": snapshot.fetched_at.isoformat(),
                "snapshot_window_days": snapshot.window_days,
                "accepted_at": snapshot.accepted_at.isoformat(),
                "pr_number": pull_request.number,
                "title": pull_request.title,
                "url": pull_request.url,
                "author_login": pull_request.author_login or "",
                "created_at": pull_request.created_at.isoformat(),
                "closed_at": _optional_datetime(pull_request.closed_at),
                "merged_at": _optional_datetime(pull_request.merged_at),
                "outcome": _pull_request_outcome(pull_request),
                "is_closed": pull_request.closed_at is not None,
                "is_merged": pull_request.merged_at is not None,
                "time_to_close_days": _elapsed_days(
                    pull_request.created_at,
                    pull_request.closed_at,
                ),
                "time_to_merge_days": _elapsed_days(
                    pull_request.created_at,
                    pull_request.merged_at,
                ),
                "observed_open_days": _elapsed_days(
                    pull_request.created_at,
                    observation_end,
                ),
                "resolution_censored": pull_request.closed_at is None,
                "period": response.period,
                "days_from_acceptance": days_from_acceptance,
                "within_window": abs(days_from_acceptance) <= window_days,
                "first_response_at": _optional_datetime(response.first_response_at),
                "response_days": response.response_days,
                "response_observation_days": _elapsed_days(
                    pull_request.created_at,
                    response_observation_end,
                ),
                "response_censored": response.first_response_at is None,
                "has_response": response.response_days is not None,
            }


def write_pull_request_csv(
    snapshots: Iterable[RepositorySnapshot],
    path: str | Path,
    *,
    window_days: int = 365,
    policy: MaintainerResponsePolicy | None = None,
) -> Path:
    """Write a deterministic PR-level CSV from local snapshots."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(
        pull_request_rows(snapshots, window_days=window_days, policy=policy),
        key=lambda row: (row["repository"].casefold(), row["pr_number"]),
    )
    with destination.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=PULL_REQUEST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return destination


def _optional_datetime(value: Any | None) -> str:
    return "" if value is None else value.isoformat()


def _elapsed_days(start: Any, end: Any | None) -> float | None:
    if end is None:
        return None
    return (end - start).total_seconds() / 86_400


def _pull_request_outcome(pull_request: Any) -> str:
    if pull_request.merged_at is not None:
        return "merged"
    if pull_request.closed_at is not None:
        return "closed_unmerged"
    return "open"
