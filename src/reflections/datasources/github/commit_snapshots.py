"""Read and write versioned commit snapshots."""

from datetime import datetime
import json
from pathlib import Path
from typing import Any

from .models import CommitRecord, CommitSnapshot

SUPPORTED_SCHEMA_VERSION = 1


def save_commit_snapshot(snapshot: CommitSnapshot, path: str | Path) -> Path:
    """Atomically write a commit snapshot as readable JSON."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_text(
        json.dumps(_snapshot_to_dict(snapshot), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)
    return destination


def load_commit_snapshot(path: str | Path) -> CommitSnapshot:
    """Load a commit snapshot written by :func:`save_commit_snapshot`."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    version = data.get("schema_version")
    if version != SUPPORTED_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported commit snapshot schema version {version!r}; "
            f"expected {SUPPORTED_SCHEMA_VERSION}"
        )
    return _snapshot_from_dict(data)


def _snapshot_to_dict(snapshot: CommitSnapshot) -> dict[str, Any]:
    return {
        "schema_version": snapshot.schema_version,
        "repository": snapshot.repository,
        "default_branch": snapshot.default_branch,
        "accepted_at": snapshot.accepted_at.isoformat(),
        "fetched_at": snapshot.fetched_at.isoformat(),
        "window_days": snapshot.window_days,
        "commits": [
            {
                "sha": commit.sha,
                "url": commit.url,
                "message": commit.message,
                "authored_at": _optional_datetime(commit.authored_at),
                "committed_at": commit.committed_at.isoformat(),
                "author_login": commit.author_login,
                "committer_login": commit.committer_login,
                "author_name": commit.author_name,
                "committer_name": commit.committer_name,
                "parent_count": commit.parent_count,
                "is_merge": commit.is_merge,
                "author_is_bot": commit.author_is_bot,
                "committer_is_bot": commit.committer_is_bot,
            }
            for commit in snapshot.commits
        ],
    }


def _snapshot_from_dict(data: dict[str, Any]) -> CommitSnapshot:
    return CommitSnapshot(
        schema_version=data["schema_version"],
        repository=data["repository"],
        default_branch=data["default_branch"],
        accepted_at=datetime.fromisoformat(data["accepted_at"]),
        fetched_at=datetime.fromisoformat(data["fetched_at"]),
        window_days=data["window_days"],
        commits=tuple(
            CommitRecord(
                sha=commit["sha"],
                url=commit["url"],
                message=commit["message"],
                authored_at=_parse_optional_datetime(commit["authored_at"]),
                committed_at=datetime.fromisoformat(commit["committed_at"]),
                author_login=commit["author_login"],
                committer_login=commit["committer_login"],
                author_name=commit["author_name"],
                committer_name=commit["committer_name"],
                parent_count=commit["parent_count"],
                is_merge=commit["is_merge"],
                author_is_bot=commit["author_is_bot"],
                committer_is_bot=commit["committer_is_bot"],
            )
            for commit in data["commits"]
        ),
    )


def _optional_datetime(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def _parse_optional_datetime(value: str | None) -> datetime | None:
    return None if value is None else datetime.fromisoformat(value)
