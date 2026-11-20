"""Stable records collected from GitHub.

These records deliberately do not expose PyGithub objects.  They form the
boundary between the changing GitHub API and the analyses in reflections.
"""

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(frozen=True)
class Submission:
    """An accepted pyOpenSci software submission."""

    package: str
    repository: str
    accepted_at: datetime
    issue_number: int
    issue_url: str
    title: str
    maintainers: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CohortMetadataSnapshot:
    """Submission and repository dates used to describe the cohort."""

    package: str
    repository: str
    issue_number: int
    issue_url: str
    submitted_at: datetime
    accepted_at: datetime
    repository_created_at: datetime
    last_default_branch_commit_at: datetime | None
    default_branch: str
    fetched_at: datetime
    maintainer_count: int
    repository_archived: bool
    repository_is_fork: bool
    schema_version: int = 2


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
    window_days: int | None = None
    schema_version: int = 2


@dataclass(frozen=True)
class CommitRecord:
    """A commit reachable from a repository's default branch."""

    sha: str
    url: str
    message: str
    authored_at: datetime | None
    committed_at: datetime
    author_login: str | None
    committer_login: str | None
    author_name: str | None
    committer_name: str | None
    parent_count: int
    is_merge: bool
    author_is_bot: bool
    committer_is_bot: bool


@dataclass(frozen=True)
class CommitSnapshot:
    """A point-in-time collection of default-branch commits."""

    repository: str
    default_branch: str
    accepted_at: datetime
    fetched_at: datetime
    window_days: int
    commits: tuple[CommitRecord, ...] = field(default_factory=tuple)
    schema_version: int = 1


@dataclass(frozen=True)
class IssueEvent:
    """A timestamped event from an issue timeline."""

    kind: str
    created_at: datetime
    actor_login: str | None
    actor_association: str | None


@dataclass(frozen=True)
class IssueRecord:
    """The issue fields needed for response and resolution metrics."""

    number: int
    title: str
    url: str
    author_login: str | None
    created_at: datetime
    closed_at: datetime | None
    events: tuple[IssueEvent, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class IssueSnapshot:
    """A point-in-time collection of repository issues and timelines."""

    repository: str
    accepted_at: datetime
    fetched_at: datetime
    window_days: int
    issues: tuple[IssueRecord, ...] = field(default_factory=tuple)
    schema_version: int = 1


@dataclass(frozen=True)
class HistoryIndexRecord:
    """Lightweight issue or pull-request metadata from a list endpoint."""

    number: int
    title: str
    url: str
    author_login: str | None
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None
    merged_at: datetime | None
    state: str
    comment_count: int
    review_comment_count: int | None
    is_draft: bool | None


@dataclass(frozen=True)
class HistoryIndexSnapshot:
    """A page-checkpointed, unwindowed issue or pull-request index."""

    repository: str
    entity_type: str
    fetched_at: datetime
    records: tuple[HistoryIndexRecord, ...] = field(default_factory=tuple)
    next_page: int = 1
    complete: bool = False
    requests_used: int = 0
    rate_remaining: int | None = None
    schema_version: int = 1


@dataclass(frozen=True)
class StarHistoryWeek:
    """Daily star acquisitions for one GitHub calendar week."""

    week_started_at: datetime
    total: int
    days: tuple[int, ...]


@dataclass(frozen=True)
class StarSnapshot:
    """A resumable aggregate repository star-history snapshot."""

    repository: str
    accepted_at: datetime
    fetched_at: datetime
    current_stargazers: int
    weeks: tuple[StarHistoryWeek, ...] = field(default_factory=tuple)
    pages_collected: int = 0
    total_pages: int | None = None
    complete: bool = False
    schema_version: int = 1


@dataclass(frozen=True)
class RepositoryContribution:
    """Observed public contributions by one maintainer to one repository."""

    repository: str
    commits: int | None
    issues: int | None
    pull_requests: int | None
    pull_request_reviews: int | None


@dataclass(frozen=True)
class MaintainerActivitySnapshot:
    """A maintainer's observed GitHub contribution activity in a fixed window."""

    requested_login: str
    canonical_login: str | None
    user_exists: bool
    fetched_at: datetime
    observation_start: datetime
    observation_end: datetime
    total_commits: int
    total_issues: int
    total_pull_requests: int
    total_pull_request_reviews: int
    restricted_contributions: int
    last_activity_on: date | None
    repositories: tuple[RepositoryContribution, ...] = field(default_factory=tuple)
    commits_truncated: bool = False
    issues_truncated: bool = False
    pull_requests_truncated: bool = False
    pull_request_reviews_truncated: bool = False
    graphql_rate_remaining: int | None = None
    schema_version: int = 1
