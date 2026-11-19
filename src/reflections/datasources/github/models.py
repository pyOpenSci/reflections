"""Stable records collected from GitHub.

These records deliberately do not expose PyGithub objects.  They form the
boundary between the changing GitHub API and the analyses in reflections.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Submission:
    """An accepted pyOpenSci software submission."""

    package: str
    repository: str
    accepted_at: datetime
    issue_number: int
    issue_url: str
    title: str


@dataclass(frozen=True)
class ResponseEvent:
    """An activity on a pull request that could constitute a response."""

    kind: str
    created_at: datetime
    author_login: str | None
    author_association: str | None


@dataclass(frozen=True)
class PullRequestRecord:
    """The pull-request fields needed by the initial reflections metrics."""

    number: int
    title: str
    url: str
    author_login: str | None
    created_at: datetime
    closed_at: datetime | None
    merged_at: datetime | None
    responses: tuple[ResponseEvent, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RepositorySnapshot:
    """A point-in-time collection of repository activity."""

    repository: str
    accepted_at: datetime
    fetched_at: datetime
    pull_requests: tuple[PullRequestRecord, ...] = field(default_factory=tuple)
    schema_version: int = 1
