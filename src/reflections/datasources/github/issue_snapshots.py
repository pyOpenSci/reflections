"""Read and write versioned issue snapshots."""

from datetime import datetime
import json
from pathlib import Path
from typing import Any

from .models import IssueEvent, IssueRecord, IssueSnapshot

SUPPORTED_SCHEMA_VERSION = 1


def save_issue_snapshot(snapshot: IssueSnapshot, path: str | Path) -> Path:
    """Atomically write an issue snapshot as readable JSON."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_text(
        json.dumps(_snapshot_to_dict(snapshot), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)
    return destination


def load_issue_snapshot(path: str | Path) -> IssueSnapshot:
    """Load an issue snapshot written by :func:`save_issue_snapshot`."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    version = data.get("schema_version")
    if version != SUPPORTED_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported issue snapshot schema version {version!r}; "
            f"expected {SUPPORTED_SCHEMA_VERSION}"
        )
    return _snapshot_from_dict(data)


def _snapshot_to_dict(snapshot: IssueSnapshot) -> dict[str, Any]:
    return {
        "schema_version": snapshot.schema_version,
        "repository": snapshot.repository,
        "accepted_at": snapshot.accepted_at.isoformat(),
        "fetched_at": snapshot.fetched_at.isoformat(),
        "window_days": snapshot.window_days,
        "issues": [
            {
                "number": issue.number,
                "title": issue.title,
                "url": issue.url,
                "author_login": issue.author_login,
                "created_at": issue.created_at.isoformat(),
                "closed_at": _optional_datetime(issue.closed_at),
                "events": [
                    {
                        "kind": event.kind,
                        "created_at": event.created_at.isoformat(),
                        "actor_login": event.actor_login,
                        "actor_association": event.actor_association,
                    }
                    for event in issue.events
                ],
            }
            for issue in snapshot.issues
        ],
    }


def _snapshot_from_dict(data: dict[str, Any]) -> IssueSnapshot:
    return IssueSnapshot(
        schema_version=data["schema_version"],
        repository=data["repository"],
        accepted_at=datetime.fromisoformat(data["accepted_at"]),
        fetched_at=datetime.fromisoformat(data["fetched_at"]),
        window_days=data["window_days"],
        issues=tuple(
            IssueRecord(
                number=issue["number"],
                title=issue["title"],
                url=issue["url"],
                author_login=issue["author_login"],
                created_at=datetime.fromisoformat(issue["created_at"]),
                closed_at=_parse_optional_datetime(issue["closed_at"]),
                events=tuple(
                    IssueEvent(
                        kind=event["kind"],
                        created_at=datetime.fromisoformat(event["created_at"]),
                        actor_login=event["actor_login"],
                        actor_association=event["actor_association"],
                    )
                    for event in issue["events"]
                ),
            )
            for issue in data["issues"]
        ),
    )


def _optional_datetime(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def _parse_optional_datetime(value: str | None) -> datetime | None:
    return None if value is None else datetime.fromisoformat(value)
