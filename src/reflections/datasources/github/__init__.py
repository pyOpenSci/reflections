"""GitHub-backed data collection for reflections."""

from .client import (
    APPROVED_LABEL,
    RepositoryLinkNotFoundError,
    SubmissionNotFoundError,
    UnsupportedRepositoryHostError,
    UnsupportedRepositoryWarning,
    collect_repository_snapshot,
    create_github,
    get_accepted_submissions,
    get_submission,
)
from .commits import collect_commit_snapshot
from .commit_snapshots import load_commit_snapshot, save_commit_snapshot
from .issues import collect_issue_snapshot
from .issue_snapshots import load_issue_snapshot, save_issue_snapshot
from .models import (
    CommitRecord,
    CommitSnapshot,
    IssueEvent,
    IssueRecord,
    IssueSnapshot,
    PullRequestRecord,
    RepositorySnapshot,
    ResponseEvent,
    StarHistoryWeek,
    StarSnapshot,
    Submission,
)
from .snapshots import load_snapshot, save_snapshot
from .stars import collect_star_snapshot
from .star_snapshots import load_star_snapshot, save_star_snapshot

__all__ = [
    "APPROVED_LABEL",
    "CommitRecord",
    "CommitSnapshot",
    "IssueEvent",
    "IssueRecord",
    "IssueSnapshot",
    "PullRequestRecord",
    "RepositoryLinkNotFoundError",
    "RepositorySnapshot",
    "ResponseEvent",
    "StarHistoryWeek",
    "StarSnapshot",
    "Submission",
    "SubmissionNotFoundError",
    "UnsupportedRepositoryHostError",
    "UnsupportedRepositoryWarning",
    "collect_repository_snapshot",
    "collect_commit_snapshot",
    "collect_issue_snapshot",
    "collect_star_snapshot",
    "create_github",
    "get_accepted_submissions",
    "get_submission",
    "load_snapshot",
    "load_commit_snapshot",
    "load_issue_snapshot",
    "load_star_snapshot",
    "save_commit_snapshot",
    "save_issue_snapshot",
    "save_star_snapshot",
    "save_snapshot",
]
