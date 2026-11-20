"""Collect unwindowed issue and pull-request indexes with hard request limits."""

from collections.abc import Callable
from datetime import UTC, datetime
import re
from typing import Any

from github import Github

from .client import create_github
from .models import HistoryIndexRecord, HistoryIndexSnapshot

PAGE_SIZE = 100
ENTITY_ENDPOINTS = {"issues": "issues", "pull_requests": "pulls"}
_LAST_PAGE = re.compile(r"[?&]page=(\d+)>;\s*rel=\"last\"")


def collect_history_index(
    repository: str,
    entity_type: str,
    *,
    github: Github | None = None,
    existing_snapshot: HistoryIndexSnapshot | None = None,
    request_budget: int = 25,
    quota_floor: int = 500,
    on_progress: Callable[[HistoryIndexSnapshot, int, int | None], None] | None = None,
) -> HistoryIndexSnapshot:
    """Collect list metadata while respecting a hard local and GitHub quota budget."""

    if entity_type not in ENTITY_ENDPOINTS:
        raise ValueError(f"Unsupported history entity type: {entity_type}")
    if request_budget <= 0:
        raise ValueError("request_budget must be positive")
    if quota_floor < 0:
        raise ValueError("quota_floor must not be negative")
    _validate_existing(existing_snapshot, repository, entity_type)
    if existing_snapshot is not None and existing_snapshot.complete:
        return existing_snapshot

    client = github or create_github()
    remaining, _ = client.rate_limiting
    allowed = min(request_budget, max(0, remaining - quota_floor))
    records = {
        item.number: item
        for item in (existing_snapshot.records if existing_snapshot else ())
    }
    page = existing_snapshot.next_page if existing_snapshot else 1
    prior_requests = existing_snapshot.requests_used if existing_snapshot else 0
    snapshot = _snapshot(
        repository,
        entity_type,
        records.values(),
        page,
        False,
        prior_requests,
        remaining,
    )
    for used in range(1, allowed + 1):
        endpoint = ENTITY_ENDPOINTS[entity_type]
        headers, data = client.requester.requestJsonAndCheck(
            "GET",
            f"/repos/{repository}/{endpoint}",
            parameters={
                "state": "all",
                "sort": "created",
                "direction": "asc",
                "per_page": PAGE_SIZE,
                "page": page,
            },
        )
        for item in data:
            if entity_type == "issues" and "pull_request" in item:
                continue
            record = _record(item, entity_type)
            records[record.number] = record
        complete = not _has_next_page(headers, item_count=len(data))
        remaining = _rate_remaining(headers, fallback=remaining - 1)
        page += 1
        snapshot = _snapshot(
            repository,
            entity_type,
            records.values(),
            page,
            complete,
            prior_requests + used,
            remaining,
        )
        if on_progress is not None:
            on_progress(snapshot, page - 1, _total_pages(headers))
        if complete or remaining <= quota_floor:
            break
    return snapshot


def _record(data: dict[str, Any], entity_type: str) -> HistoryIndexRecord:
    return HistoryIndexRecord(
        number=int(data["number"]),
        title=str(data["title"]),
        url=str(data["html_url"]),
        author_login=(data.get("user") or {}).get("login"),
        created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
        updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
        closed_at=_parse_datetime(data.get("closed_at")),
        merged_at=_parse_datetime(data.get("merged_at")),
        state=str(data["state"]),
        comment_count=int(data.get("comments", 0)),
        review_comment_count=(
            int(data.get("review_comments", 0))
            if entity_type == "pull_requests"
            else None
        ),
        is_draft=(
            bool(data.get("draft", False))
            if entity_type == "pull_requests"
            else None
        ),
    )


def _snapshot(
    repository, entity_type, records, next_page, complete, requests, remaining
):
    return HistoryIndexSnapshot(
        repository=repository,
        entity_type=entity_type,
        fetched_at=datetime.now(UTC),
        records=tuple(sorted(records, key=lambda item: (item.created_at, item.number))),
        next_page=next_page,
        complete=complete,
        requests_used=requests,
        rate_remaining=remaining,
    )


def _validate_existing(snapshot, repository: str, entity_type: str) -> None:
    if snapshot is None:
        return
    if snapshot.repository.casefold() != repository.casefold():
        raise ValueError("checkpoint repository does not match collection target")
    if snapshot.entity_type != entity_type:
        raise ValueError("checkpoint entity type does not match collection target")


def _parse_datetime(value: str | None) -> datetime | None:
    return (
        None
        if value is None
        else datetime.fromisoformat(value.replace("Z", "+00:00"))
    )


def _has_next_page(headers: dict[str, Any], *, item_count: int) -> bool:
    link = str(headers.get("link") or headers.get("Link") or "")
    return 'rel="next"' in link or (not link and item_count == PAGE_SIZE)


def _total_pages(headers: dict[str, Any]) -> int | None:
    link = str(headers.get("link") or headers.get("Link") or "")
    match = _LAST_PAGE.search(link)
    return int(match.group(1)) if match else None


def _rate_remaining(headers: dict[str, Any], *, fallback: int) -> int:
    value = headers.get("x-ratelimit-remaining") or headers.get("X-RateLimit-Remaining")
    return int(value) if value is not None else fallback
