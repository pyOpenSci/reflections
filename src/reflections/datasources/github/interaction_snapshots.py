"""Read and write page-checkpointed interaction streams."""

import json
from datetime import datetime
from pathlib import Path

from .models import InteractionRecord, InteractionSnapshot

SCHEMA_VERSION = 1


def save_interaction_snapshot(
    snapshot: InteractionSnapshot,
    path: str | Path,
) -> Path:
    """Atomically write an interaction snapshot."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_text(
        json.dumps(_to_dict(snapshot), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)
    return destination


def load_interaction_snapshot(path: str | Path) -> InteractionSnapshot:
    """Load an interaction snapshot."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != SCHEMA_VERSION:
        version = data.get("schema_version")
        raise ValueError(f"Unsupported interaction snapshot schema: {version}")
    return InteractionSnapshot(
        schema_version=SCHEMA_VERSION,
        repository=data["repository"],
        interaction_type=data["interaction_type"],
        fetched_at=datetime.fromisoformat(data["fetched_at"]),
        next_page=data["next_page"],
        next_url=data["next_url"],
        complete=data["complete"],
        requests_used=data["requests_used"],
        rate_remaining=data["rate_remaining"],
        records=tuple(_record_from_dict(item) for item in data["records"]),
    )


def _to_dict(snapshot: InteractionSnapshot) -> dict:
    return {
        "schema_version": snapshot.schema_version,
        "repository": snapshot.repository,
        "interaction_type": snapshot.interaction_type,
        "fetched_at": snapshot.fetched_at.isoformat(),
        "next_page": snapshot.next_page,
        "next_url": snapshot.next_url,
        "complete": snapshot.complete,
        "requests_used": snapshot.requests_used,
        "rate_remaining": snapshot.rate_remaining,
        "records": [
            {
                "id": item.id,
                "parent_number": item.parent_number,
                "kind": item.kind,
                "url": item.url,
                "author_login": item.author_login,
                "author_association": item.author_association,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
            }
            for item in snapshot.records
        ],
    }


def _record_from_dict(data: dict) -> InteractionRecord:
    return InteractionRecord(
        id=data["id"],
        parent_number=data["parent_number"],
        kind=data["kind"],
        url=data["url"],
        author_login=data["author_login"],
        author_association=data["author_association"],
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"]),
    )
