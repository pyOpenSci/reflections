"""Collect aggregate GitHub repository star history without user identities."""

from collections.abc import Callable
from datetime import UTC, datetime
import re
from typing import Any

from github import Github

from .client import create_github
from .models import StarHistoryWeek, StarSnapshot

PAGE_SIZE = 30
MAX_PAGES = 100
_LAST_PAGE = re.compile(r"[?&]page=(\d+)>;\s*rel=\"last\"")


def collect_star_snapshot(
    repository: str,
    *,
    accepted_at: datetime,
    github: Github | None = None,
    existing_snapshot: StarSnapshot | None = None,
    on_progress: Callable[[StarSnapshot, int, int, bool], None] | None = None,
) -> StarSnapshot:
    """Collect GitHub's aggregate daily star history, resuming by page."""

    _validate_existing_snapshot(
        existing_snapshot,
        repository=repository,
        accepted_at=accepted_at,
    )
    if existing_snapshot is not None and existing_snapshot.complete:
        return existing_snapshot

    client = github or create_github()
    github_repository = client.get_repo(repository)

    weeks = {
        week.week_started_at: week
        for week in (existing_snapshot.weeks if existing_snapshot is not None else ())
    }
    current_stargazers = (
        existing_snapshot.current_stargazers
        if existing_snapshot is not None
        else github_repository.stargazers_count
    )
    page = (
        existing_snapshot.pages_collected + 1
        if existing_snapshot is not None
        else 1
    )
    total_pages = (
        existing_snapshot.total_pages if existing_snapshot is not None else None
    )

    while page <= MAX_PAGES:
        headers, data = github_repository._requester.requestJsonAndCheck(
            "GET",
            f"{github_repository.url}/stargazers/history",
            parameters={"per_page": PAGE_SIZE, "page": page},
        )
        if total_pages is None:
            total_pages = _total_pages(headers, page=page, item_count=len(data))
        for item in data:
            week = _star_week(item)
            weeks[week.week_started_at] = week

        complete = len(data) < PAGE_SIZE or page >= (total_pages or MAX_PAGES)
        snapshot = _star_snapshot(
            repository,
            accepted_at=accepted_at,
            current_stargazers=current_stargazers,
            weeks=weeks.values(),
            pages_collected=page,
            total_pages=total_pages,
            complete=complete,
        )
        if on_progress is not None:
            on_progress(snapshot, page, total_pages or MAX_PAGES, complete)
        if complete:
            return snapshot
        page += 1

    return _star_snapshot(
        repository,
        accepted_at=accepted_at,
        current_stargazers=current_stargazers,
        weeks=weeks.values(),
        pages_collected=MAX_PAGES,
        total_pages=total_pages or MAX_PAGES,
        complete=True,
    )


def _star_week(data: dict[str, Any]) -> StarHistoryWeek:
    days = tuple(int(value) for value in data["days"])
    if len(days) != 7:
        raise ValueError("GitHub star-history week does not contain seven days")
    total = int(data["total"])
    if total != sum(days):
        raise ValueError("GitHub star-history weekly total does not match daily counts")
    return StarHistoryWeek(
        week_started_at=datetime.fromtimestamp(int(data["week"]), UTC),
        total=total,
        days=days,
    )


def _total_pages(headers: dict[str, Any], *, page: int, item_count: int) -> int:
    link = str(headers.get("link") or headers.get("Link") or "")
    match = _LAST_PAGE.search(link)
    if match:
        return min(int(match.group(1)), MAX_PAGES)
    return page if item_count < PAGE_SIZE else MAX_PAGES


def _star_snapshot(
    repository: str,
    *,
    accepted_at: datetime,
    current_stargazers: int,
    weeks: Any,
    pages_collected: int,
    total_pages: int | None,
    complete: bool,
) -> StarSnapshot:
    return StarSnapshot(
        repository=repository,
        accepted_at=accepted_at,
        fetched_at=datetime.now(UTC),
        current_stargazers=current_stargazers,
        weeks=tuple(sorted(weeks, key=lambda week: week.week_started_at)),
        pages_collected=pages_collected,
        total_pages=total_pages,
        complete=complete,
    )


def _validate_existing_snapshot(
    snapshot: StarSnapshot | None,
    *,
    repository: str,
    accepted_at: datetime,
) -> None:
    if snapshot is None:
        return
    if snapshot.repository.casefold() != repository.casefold():
        raise ValueError("checkpoint repository does not match collection target")
    if snapshot.accepted_at != accepted_at:
        raise ValueError("checkpoint acceptance time does not match collection target")
