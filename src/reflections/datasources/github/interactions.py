"""Collect unwindowed repository-wide GitHub interaction streams."""

import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from github import Github

from .client import create_github
from .models import InteractionRecord, InteractionSnapshot

PAGE_SIZE = 100
INTERACTION_ENDPOINTS = {
    "issue_comments": "issues/comments",
    "review_comments": "pulls/comments",
}
INTERACTION_KINDS = {
    "issue_comments": "issue_comment",
    "review_comments": "review_comment",
}
PARENT_URL_FIELDS = {
    "issue_comments": "issue_url",
    "review_comments": "pull_request_url",
}
_NEXT_LINK = re.compile(r'<([^>]+)>;\s*rel="next"')
_LAST_PAGE = re.compile(r"[?&]page=(\d+)[^>]*>;\s*rel=\"last\"")
_PARENT_NUMBER = re.compile(r"/(\d+)/?$")


def collect_interaction_stream(
    repository: str,
    interaction_type: str,
    *,
    github: Github | None = None,
    existing_snapshot: InteractionSnapshot | None = None,
    request_budget: int = 25,
    quota_floor: int = 500,
    known_rate_remaining: int | None = None,
    on_progress: Callable[[InteractionSnapshot, int, int | None], None] | None = None,
) -> InteractionSnapshot:
    """Collect a bulk comment stream with hard request and quota limits."""

    if interaction_type not in INTERACTION_ENDPOINTS:
        raise ValueError(f"Unsupported interaction type: {interaction_type}")
    if request_budget <= 0:
        raise ValueError("request_budget must be positive")
    if quota_floor < 0:
        raise ValueError("quota_floor must not be negative")
    _validate_existing(existing_snapshot, repository, interaction_type)
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
        item.id: item
        for item in (existing_snapshot.records if existing_snapshot else ())
    }
    page = existing_snapshot.next_page if existing_snapshot else 1
    next_url = existing_snapshot.next_url if existing_snapshot else None
    prior_requests = existing_snapshot.requests_used if existing_snapshot else 0
    snapshot = _snapshot(
        repository,
        interaction_type,
        records.values(),
        page,
        next_url,
        False,
        prior_requests,
        remaining,
    )

    for used in range(1, allowed + 1):
        url, parameters = _request_target(
            repository, interaction_type, page, next_url
        )
        headers, data = client.requester.requestJsonAndCheck(
            "GET",
            url,
            parameters=parameters,
        )
        for item in data:
            record = _record(item, interaction_type)
            records[record.id] = record
        next_url = _next_url(headers)
        complete = next_url is None and len(data) < PAGE_SIZE
        remaining = _rate_remaining(headers, fallback=remaining - 1)
        page += 1
        snapshot = _snapshot(
            repository,
            interaction_type,
            records.values(),
            page,
            next_url,
            complete,
            prior_requests + used,
            remaining,
        )
        if on_progress is not None:
            on_progress(snapshot, page - 1, _total_pages(headers))
        if complete or remaining <= quota_floor:
            break
    return snapshot


def _record(data: dict[str, Any], interaction_type: str) -> InteractionRecord:
    parent_field = PARENT_URL_FIELDS[interaction_type]
    match = _PARENT_NUMBER.search(str(data[parent_field]))
    if match is None:
        raise ValueError(f"Could not determine parent number from {data[parent_field]!r}")
    return InteractionRecord(
        id=int(data["id"]),
        parent_number=int(match.group(1)),
        kind=INTERACTION_KINDS[interaction_type],
        url=str(data["html_url"]),
        author_login=(data.get("user") or {}).get("login"),
        author_association=data.get("author_association"),
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"]),
    )


def _snapshot(
    repository,
    interaction_type,
    records,
    next_page,
    next_url,
    complete,
    requests,
    remaining,
):
    return InteractionSnapshot(
        repository=repository,
        interaction_type=interaction_type,
        fetched_at=datetime.now(UTC),
        records=tuple(
            sorted(records, key=lambda item: (item.created_at, item.id))
        ),
        next_page=next_page,
        next_url=next_url,
        complete=complete,
        requests_used=requests,
        rate_remaining=remaining,
    )


def _validate_existing(snapshot, repository: str, interaction_type: str) -> None:
    if snapshot is None:
        return
    if snapshot.repository.casefold() != repository.casefold():
        raise ValueError("checkpoint repository does not match collection target")
    if snapshot.interaction_type != interaction_type:
        raise ValueError("checkpoint interaction type does not match collection target")


def _request_target(
    repository: str,
    interaction_type: str,
    page: int,
    next_url: str | None,
) -> tuple[str, dict[str, Any]]:
    if next_url is not None:
        parsed = urlsplit(next_url)
        return parsed.path, dict(parse_qsl(parsed.query))
    endpoint = INTERACTION_ENDPOINTS[interaction_type]
    return f"/repos/{repository}/{endpoint}", {
        "sort": "created",
        "direction": "asc",
        "per_page": PAGE_SIZE,
        "page": page,
    }


def _next_url(headers: dict[str, Any]) -> str | None:
    link = str(headers.get("link") or headers.get("Link") or "")
    match = _NEXT_LINK.search(link)
    return match.group(1) if match else None


def _total_pages(headers: dict[str, Any]) -> int | None:
    link = str(headers.get("link") or headers.get("Link") or "")
    match = _LAST_PAGE.search(link)
    return int(match.group(1)) if match else None


def _rate_remaining(headers: dict[str, Any], *, fallback: int) -> int:
    value = headers.get("x-ratelimit-remaining") or headers.get(
        "X-RateLimit-Remaining"
    )
    return int(value) if value is not None else fallback
