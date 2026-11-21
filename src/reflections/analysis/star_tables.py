"""Build daily aggregate star-history tables from local snapshots."""

from collections.abc import Iterable, Iterator
import csv
from datetime import timedelta
from pathlib import Path
from typing import Any

from reflections.datasources.github.models import StarSnapshot

STAR_COLUMNS = (
    "repository",
    "package",
    "snapshot_fetched_at",
    "accepted_at",
    "current_stargazers",
    "star_date",
    "new_stars",
    "cumulative_star_acquisitions",
    "period",
    "days_from_acceptance",
    "within_window",
)


def star_rows(
    snapshots: Iterable[StarSnapshot],
    *,
    window_days: int = 365,
) -> Iterator[dict[str, Any]]:
    """Yield one row per calendar day in the aggregate star history."""

    if window_days <= 0:
        raise ValueError("window_days must be positive")
    for snapshot in snapshots:
        if not snapshot.complete:
            raise ValueError(f"Star snapshot is incomplete for {snapshot.repository}")
        cumulative = 0
        for week in snapshot.weeks:
            for offset, new_stars in enumerate(week.days):
                star_at = week.week_started_at + timedelta(days=offset)
                cumulative += new_stars
                days_from_acceptance = (
                    star_at - snapshot.accepted_at
                ).total_seconds() / 86_400
                yield {
                    "repository": snapshot.repository,
                    "package": snapshot.repository.rsplit("/", 1)[-1],
                    "snapshot_fetched_at": snapshot.fetched_at.isoformat(),
                    "accepted_at": snapshot.accepted_at.isoformat(),
                    "current_stargazers": snapshot.current_stargazers,
                    "star_date": star_at.date().isoformat(),
                    "new_stars": new_stars,
                    "cumulative_star_acquisitions": cumulative,
                    "period": (
                        "after_acceptance"
                        if star_at > snapshot.accepted_at
                        else "before_acceptance"
                    ),
                    "days_from_acceptance": days_from_acceptance,
                    "within_window": abs(days_from_acceptance) <= window_days,
                }


def write_star_csv(
    snapshots: Iterable[StarSnapshot],
    path: str | Path,
    *,
    window_days: int = 365,
) -> Path:
    """Write a deterministic daily star-history CSV."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(
        star_rows(snapshots, window_days=window_days),
        key=lambda row: (row["repository"].casefold(), row["star_date"]),
    )
    with destination.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=STAR_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return destination
