"""Collect unwindowed issue and pull-request indexes with hard request limits."""

import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from github import Github, GithubException

from .client import create_github
from .models import HistoryIndexRecord, HistoryIndexSnapshot

PAGE_SIZE = 100
ENTITY_ENDPOINTS = {"issues": "issues", "pull_requests": "pulls"}
_LAST_PAGE = re.compile(r"[?&]page=(\d+)[^>]*>;\s*rel=\"last\"")
_NEXT_LINK = re.compile(r'<([^>]+)>;\s*rel="next"')


def collect_history_index(
    repository: str,
    entity_type: str,
    *,
    github: Github | None = None,
    existing_snapshot: HistoryIndexSnapshot | None = None,
    request_budget: int = 25,
    quota_floor: int = 500,
    known_rate_remaining: int | None = None,
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
    remaining = (
        known_rate_remaining
        if known_rate_remaining is not None
        else client.rate_limiting[0]
    )
    allowed = min(request_budget, max(0, remaining - quota_floor))
    records = {
        item.number: item
        for item in (existing_snapshot.records if existing_snapshot else ())
    }
    page = existing_snapshot.next_page if existing_snapshot else 1
    next_url = existing_snapshot.next_url if existing_snapshot else None
    source_endpoint = (
        existing_snapshot.source_endpoint
        if existing_snapshot and existing_snapshot.source_endpoint
        else ENTITY_ENDPOINTS[entity_type]
    )
    # Version 1 checkpoints did not retain GitHub's cursor URL. Re-read the
    # last successful page at the 10,000-result boundary to recover it.
    if existing_snapshot is not None and next_url is None and page >= 100:
        page -= 1
    prior_requests = existing_snapshot.requests_used if existing_snapshot else 0
    snapshot = _snapshot(
        repository,
        entity_type,
        records.values(),
        page,
        next_url,
        source_endpoint,
        False,
        prior_requests,
        remaining,
    )
    used = 0
    while used < allowed:
        url, parameters = _request_target(
            repository, source_endpoint, page, next_url
        )
        try:
            headers, data = client.requester.requestJsonAndCheck(
                "GET",
                url,
                parameters=parameters,
            )
        except GithubException as error:
            used += 1
            if (
                error.status == 404
                and entity_type == "pull_requests"
                and source_endpoint == "pulls"
                and not records
            ):
                source_endpoint = "issues"
                page = 1
                next_url = None
                remaining = max(0, remaining - 1)
                continue
            raise
        used += 1
        for item in data:
            if entity_type == "issues" and "pull_request" in item:
                continue
            if (
                entity_type == "pull_requests"
                and source_endpoint == "issues"
                and "pull_request" not in item
            ):
                continue
            record = _record(item, entity_type)
            records[record.number] = record
        next_url = _next_url(headers)
        complete = next_url is None and len(data) < PAGE_SIZE
        remaining = _rate_remaining(headers, fallback=remaining - 1)
        page += 1
        snapshot = _snapshot(
            repository,
            entity_type,
            records.values(),
            page,
            next_url,
            source_endpoint,
            complete,
            prior_requests + used,
            remaining,
        )
        if on_progress is not None:
            on_progress(snapshot, page - 1, _total_pages(headers))
        if complete or remaining <= quota_floor:
            break
    if snapshot.requests_used != prior_requests + used:
        snapshot = _snapshot(
            repository,
            entity_type,
            records.values(),
            page,
            next_url,
            source_endpoint,
            False,
            prior_requests + used,
            remaining,
        )
    return snapshot


def _record(data: dict[str, Any], entity_type: str) -> HistoryIndexRecord:
    return HistoryIndexRecord(
        number=int(data["number"]),
        title=str(data["title"]),
        url=str(data["html_url"]),
        author_login=(data.get("user") or {}).get("login"),
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"]),
        closed_at=_parse_datetime(data.get("closed_at")),
        merged_at=_parse_datetime(data.get("merged_at")),
        state=str(data["state"]),
        comment_count=int(data.get("comments", 0)),
        review_comment_count=(
            int(data["review_comments"])
            if entity_type == "pull_requests" and "review_comments" in data
            else None
        ),
        is_draft=(
            bool(data["draft"])
            if entity_type == "pull_requests" and "draft" in data
            else None
        ),
    )


def _snapshot(
    repository,
    entity_type,
    records,
    next_page,
    next_url,
    source_endpoint,
    complete,
    requests,
    remaining,
):
    return HistoryIndexSnapshot(
        repository=repository,
        entity_type=entity_type,
        fetched_at=datetime.now(UTC),
        records=tuple(sorted(records, key=lambda item: (item.created_at, item.number))),
        next_page=next_page,
        next_url=next_url,
        source_endpoint=source_endpoint,
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
        else datetime.fromisoformat(value)
    )


def _next_url(headers: dict[str, Any]) -> str | None:
    link = str(headers.get("link") or headers.get("Link") or "")
    match = _NEXT_LINK.search(link)
    return match.group(1) if match else None


def _request_target(
    repository: str,
    source_endpoint: str,
    page: int,
    next_url: str | None,
) -> tuple[str, dict[str, Any]]:
    if next_url is not None:
        parsed = urlsplit(next_url)
        return parsed.path, dict(parse_qsl(parsed.query))
    return f"/repos/{repository}/{source_endpoint}", {
        "state": "all",
        "sort": "created",
        "direction": "asc",
        "per_page": PAGE_SIZE,
        "page": page,
    }


def _total_pages(headers: dict[str, Any]) -> int | None:
    link = str(headers.get("link") or headers.get("Link") or "")
    match = _LAST_PAGE.search(link)
    return int(match.group(1)) if match else None


def _rate_remaining(headers: dict[str, Any], *, fallback: int) -> int:
    value = headers.get("x-ratelimit-remaining") or headers.get("X-RateLimit-Remaining")
    return int(value) if value is not None else fallback
