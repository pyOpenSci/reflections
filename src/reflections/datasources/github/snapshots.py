"""Read and write reproducible GitHub repository snapshots."""

from datetime import datetime
import json
from pathlib import Path
from typing import Any

from .models import PullRequestRecord, RepositorySnapshot, ResponseEvent

SUPPORTED_SCHEMA_VERSION = 1


def save_snapshot(snapshot: RepositorySnapshot, path: str | Path) -> Path:
    """Write a repository snapshot as readable, versioned JSON."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(_snapshot_to_dict(snapshot), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return destination


def load_snapshot(path: str | Path) -> RepositorySnapshot:
    """Load a repository snapshot written by :func:`save_snapshot`."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    version = data.get("schema_version")
    if version != SUPPORTED_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported snapshot schema version {version!r}; "
            f"expected {SUPPORTED_SCHEMA_VERSION}"
        )
    return _snapshot_from_dict(data)


def _snapshot_to_dict(snapshot: RepositorySnapshot) -> dict[str, Any]:
    return {
        "schema_version": snapshot.schema_version,
        "repository": snapshot.repository,
        "accepted_at": snapshot.accepted_at.isoformat(),
        "fetched_at": snapshot.fetched_at.isoformat(),
        "pull_requests": [
            {
                "number": pull_request.number,
                "title": pull_request.title,
                "url": pull_request.url,
                "author_login": pull_request.author_login,
                "created_at": pull_request.created_at.isoformat(),
                "closed_at": _optional_datetime(pull_request.closed_at),
                "merged_at": _optional_datetime(pull_request.merged_at),
                "responses": [
                    {
                        "kind": response.kind,
                        "created_at": response.created_at.isoformat(),
                        "author_login": response.author_login,
                        "author_association": response.author_association,
                    }
                    for response in pull_request.responses
                ],
            }
            for pull_request in snapshot.pull_requests
        ],
    }


def _snapshot_from_dict(data: dict[str, Any]) -> RepositorySnapshot:
    return RepositorySnapshot(
        schema_version=data["schema_version"],
        repository=data["repository"],
        accepted_at=datetime.fromisoformat(data["accepted_at"]),
        fetched_at=datetime.fromisoformat(data["fetched_at"]),
        pull_requests=tuple(
            PullRequestRecord(
                number=pull_request["number"],
                title=pull_request["title"],
                url=pull_request["url"],
                author_login=pull_request["author_login"],
                created_at=datetime.fromisoformat(pull_request["created_at"]),
                closed_at=_parse_optional_datetime(pull_request["closed_at"]),
                merged_at=_parse_optional_datetime(pull_request["merged_at"]),
                responses=tuple(
                    ResponseEvent(
                        kind=response["kind"],
                        created_at=datetime.fromisoformat(response["created_at"]),
                        author_login=response["author_login"],
                        author_association=response["author_association"],
                    )
                    for response in pull_request["responses"]
                ),
            )
            for pull_request in data["pull_requests"]
        ),
    )


def _optional_datetime(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def _parse_optional_datetime(value: str | None) -> datetime | None:
    return None if value is None else datetime.fromisoformat(value)
