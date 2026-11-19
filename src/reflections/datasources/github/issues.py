"""Collect normalized GitHub issue timelines."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from github import Github

from .client import create_github
from .models import IssueEvent, IssueRecord, IssueSnapshot


def collect_issue_snapshot(
    repository: str,
    *,
    accepted_at: datetime,
    window_days: int = 365,
    github: Github | None = None,
    existing_snapshot: IssueSnapshot | None = None,
    on_progress: Callable[[IssueSnapshot, int, int, int, bool], None] | None = None,
) -> IssueSnapshot:
    """Collect issues opened in a matched window around acceptance.

    Pull requests are excluded even though GitHub exposes them through the
    Issues API. Supplying an existing snapshot resumes timeline collection.
    """

    if window_days <= 0:
        raise ValueError("window_days must be positive")
    _validate_existing_snapshot(
        existing_snapshot,
        repository=repository,
        accepted_at=accepted_at,
        window_days=window_days,
    )

    client = github or create_github()
    github_repository = client.get_repo(repository)
    candidates = _issues_in_window(
        github_repository.get_issues(state="all", sort="created", direction="asc"),
        accepted_at=accepted_at,
        window_days=window_days,
    )
    collected = {
        issue.number: issue
        for issue in (
            existing_snapshot.issues if existing_snapshot is not None else ()
        )
    }

    for completed, issue in enumerate(candidates, start=1):
        cached = issue.number in collected
        if not cached:
            collected[issue.number] = _collect_issue(issue)
        snapshot = _issue_snapshot(
            repository,
            accepted_at=accepted_at,
            window_days=window_days,
            issues=collected.values(),
        )
        if on_progress is not None:
            on_progress(snapshot, completed, len(candidates), issue.number, cached)

    return _issue_snapshot(
        repository,
        accepted_at=accepted_at,
        window_days=window_days,
        issues=collected.values(),
    )


def _issues_in_window(
    issues: Any,
    *,
    accepted_at: datetime,
    window_days: int,
) -> list[Any]:
    start = accepted_at - timedelta(days=window_days)
    end = accepted_at + timedelta(days=window_days)
    candidates = []
    for issue in issues:
        if issue.created_at < start:
            continue
        if issue.created_at > end:
            break
        if getattr(issue, "pull_request", None) is not None:
            continue
        candidates.append(issue)
    return candidates


def _collect_issue(issue: Any) -> IssueRecord:
    events = []
    for event in issue.get_timeline():
        created_at = getattr(event, "created_at", None)
        kind = getattr(event, "event", None)
        if created_at is None or kind is None:
            continue
        actor = getattr(event, "user", None) or getattr(event, "actor", None)
        events.append(
            IssueEvent(
                kind=kind,
                created_at=created_at,
                actor_login=_login(actor),
                actor_association=getattr(event, "author_association", None),
            )
        )
    events.sort(key=lambda event: event.created_at)
    return IssueRecord(
        number=issue.number,
        title=issue.title,
        url=issue.html_url,
        author_login=_login(issue.user),
        created_at=issue.created_at,
        closed_at=issue.closed_at,
        events=tuple(events),
    )


def _issue_snapshot(
    repository: str,
    *,
    accepted_at: datetime,
    window_days: int,
    issues: Any,
) -> IssueSnapshot:
    return IssueSnapshot(
        repository=repository,
        accepted_at=accepted_at,
        fetched_at=datetime.now(UTC),
        window_days=window_days,
        issues=tuple(sorted(issues, key=lambda issue: issue.created_at)),
    )


def _validate_existing_snapshot(
    snapshot: IssueSnapshot | None,
    *,
    repository: str,
    accepted_at: datetime,
    window_days: int,
) -> None:
    if snapshot is None:
        return
    if snapshot.repository.casefold() != repository.casefold():
        raise ValueError("checkpoint repository does not match collection target")
    if snapshot.accepted_at != accepted_at:
        raise ValueError("checkpoint acceptance time does not match collection target")
    if snapshot.window_days != window_days:
        raise ValueError("checkpoint window does not match collection window")


def _login(user: Any | None) -> str | None:
    return None if user is None else user.login
