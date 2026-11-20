"""Read and write versioned cohort metadata snapshots."""

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from .models import CohortMetadataSnapshot

SUPPORTED_SCHEMA_VERSION = 2


def save_cohort_metadata(snapshot: CohortMetadataSnapshot, path: str | Path) -> Path:
    """Atomically write one package's cohort metadata."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    data = asdict(snapshot)
    for field in (
        "submitted_at",
        "accepted_at",
        "repository_created_at",
        "last_default_branch_commit_at",
        "fetched_at",
    ):
        data[field] = data[field].isoformat() if data[field] is not None else None
    temporary.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(destination)
    return destination


def load_cohort_metadata(path: str | Path) -> CohortMetadataSnapshot:
    """Load a cohort metadata snapshot."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    version = data.get("schema_version")
    if version != SUPPORTED_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported cohort metadata schema version {version!r}; "
            f"expected {SUPPORTED_SCHEMA_VERSION}"
        )
    for field in (
        "submitted_at",
        "accepted_at",
        "repository_created_at",
        "last_default_branch_commit_at",
        "fetched_at",
    ):
        data[field] = (
            datetime.fromisoformat(data[field]) if data[field] is not None else None
        )
    return CohortMetadataSnapshot(**data)
