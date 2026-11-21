"""Read and write page-checkpointed full-history indexes."""

import json
from datetime import datetime
from pathlib import Path

from .models import HistoryIndexRecord, HistoryIndexSnapshot

SCHEMA_VERSION = 2
SUPPORTED_SCHEMA_VERSIONS = {1, SCHEMA_VERSION}


def save_history_index(snapshot: HistoryIndexSnapshot, path: str | Path) -> Path:
    """Atomically write a history-index snapshot."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_text(
        json.dumps(_to_dict(snapshot), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)
    return destination


def load_history_index(path: str | Path) -> HistoryIndexSnapshot:
    """Load a history-index snapshot."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    version = data.get("schema_version")
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        raise ValueError(f"Unsupported history index schema: {version}")
    return HistoryIndexSnapshot(
        schema_version=SCHEMA_VERSION,
        repository=data["repository"],
        entity_type=data["entity_type"],
        fetched_at=datetime.fromisoformat(data["fetched_at"]),
        next_page=data["next_page"],
        next_url=data.get("next_url"),
        source_endpoint=data.get("source_endpoint"),
        complete=data["complete"],
        requests_used=data["requests_used"],
        rate_remaining=data["rate_remaining"],
        records=tuple(
            _record_from_dict(
                item,
                legacy_review_count=(
                    version == 1 and data["entity_type"] == "pull_requests"
                ),
            )
            for item in data["records"]
        ),
    )


def _to_dict(snapshot: HistoryIndexSnapshot) -> dict:
    return {
        "schema_version": snapshot.schema_version,
        "repository": snapshot.repository,
        "entity_type": snapshot.entity_type,
        "fetched_at": snapshot.fetched_at.isoformat(),
        "next_page": snapshot.next_page,
        "next_url": snapshot.next_url,
        "source_endpoint": snapshot.source_endpoint,
        "complete": snapshot.complete,
        "requests_used": snapshot.requests_used,
        "rate_remaining": snapshot.rate_remaining,
        "records": [
            {
                "number": item.number,
                "title": item.title,
                "url": item.url,
                "author_login": item.author_login,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
                "closed_at": _optional_datetime(item.closed_at),
                "merged_at": _optional_datetime(item.merged_at),
                "state": item.state,
                "comment_count": item.comment_count,
                "review_comment_count": item.review_comment_count,
                "is_draft": item.is_draft,
            }
            for item in snapshot.records
        ],
    }


def _record_from_dict(
    data: dict,
    *,
    legacy_review_count: bool = False,
) -> HistoryIndexRecord:
    return HistoryIndexRecord(
        number=data["number"],
        title=data["title"],
        url=data["url"],
        author_login=data["author_login"],
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"]),
        closed_at=_parse_optional_datetime(data["closed_at"]),
        merged_at=_parse_optional_datetime(data["merged_at"]),
        state=data["state"],
        comment_count=data["comment_count"],
        review_comment_count=(
            None if legacy_review_count else data["review_comment_count"]
        ),
        is_draft=data["is_draft"],
    )


def _optional_datetime(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def _parse_optional_datetime(value: str | None) -> datetime | None:
    return None if value is None else datetime.fromisoformat(value)
