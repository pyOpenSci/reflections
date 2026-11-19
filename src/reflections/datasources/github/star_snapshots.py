"""Read and write versioned aggregate star-history snapshots."""

from datetime import datetime
import json
from pathlib import Path
from typing import Any

from .models import StarHistoryWeek, StarSnapshot

SUPPORTED_SCHEMA_VERSION = 1


def save_star_snapshot(snapshot: StarSnapshot, path: str | Path) -> Path:
    """Atomically write a star-history snapshot as readable JSON."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_text(
        json.dumps(_snapshot_to_dict(snapshot), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)
    return destination


def load_star_snapshot(path: str | Path) -> StarSnapshot:
    """Load a star-history snapshot written by :func:`save_star_snapshot`."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    version = data.get("schema_version")
    if version != SUPPORTED_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported star snapshot schema version {version!r}; "
            f"expected {SUPPORTED_SCHEMA_VERSION}"
        )
    return StarSnapshot(
        schema_version=data["schema_version"],
        repository=data["repository"],
        accepted_at=datetime.fromisoformat(data["accepted_at"]),
        fetched_at=datetime.fromisoformat(data["fetched_at"]),
        current_stargazers=data["current_stargazers"],
        pages_collected=data["pages_collected"],
        total_pages=data["total_pages"],
        complete=data["complete"],
        weeks=tuple(
            StarHistoryWeek(
                week_started_at=datetime.fromisoformat(week["week_started_at"]),
                total=week["total"],
                days=tuple(week["days"]),
            )
            for week in data["weeks"]
        ),
    )


def _snapshot_to_dict(snapshot: StarSnapshot) -> dict[str, Any]:
    return {
        "schema_version": snapshot.schema_version,
        "repository": snapshot.repository,
        "accepted_at": snapshot.accepted_at.isoformat(),
        "fetched_at": snapshot.fetched_at.isoformat(),
        "current_stargazers": snapshot.current_stargazers,
        "pages_collected": snapshot.pages_collected,
        "total_pages": snapshot.total_pages,
        "complete": snapshot.complete,
        "weeks": [
            {
                "week_started_at": week.week_started_at.isoformat(),
                "total": week.total,
                "days": list(week.days),
            }
            for week in snapshot.weeks
        ],
    }
