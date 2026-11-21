"""Read the authoritative derived cohort without analysis dependencies."""

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class CohortRepository:
    """The cohort fields shared by collection and GitHub analyses."""

    repository: str
    package: str
    accepted_at: datetime


def load_cohort(path: str | Path) -> tuple[CohortRepository, ...]:
    """Load and validate repository identities and acceptance dates."""

    source = Path(path)
    with source.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError(f"No repositories found in {source}")
    required = {"repository", "package", "accepted_at"}
    missing = sorted(required - set(rows[0]))
    if missing:
        raise ValueError(f"Cohort CSV is missing: {', '.join(missing)}")
    repositories = tuple(
        CohortRepository(
            repository=row["repository"],
            package=row["package"],
            accepted_at=datetime.fromisoformat(row["accepted_at"]),
        )
        for row in rows
    )
    normalized = [item.repository.casefold() for item in repositories]
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"Duplicate repositories found in {source}")
    return repositories


def read_repositories(path: str | Path) -> list[str]:
    """Return repository names from the validated cohort."""

    return [item.repository for item in load_cohort(path)]
