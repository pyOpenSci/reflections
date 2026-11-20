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
from .cohort import collect_cohort_metadata
from .cohort_snapshots import load_cohort_metadata, save_cohort_metadata
from .commit_snapshots import load_commit_snapshot, save_commit_snapshot
from .commits import collect_commit_snapshot
from .issue_snapshots import load_issue_snapshot, save_issue_snapshot
from .issues import collect_issue_snapshot
from .maintainer_snapshots import (
    load_maintainer_activity,
    load_maintainer_roster,
    save_maintainer_activity,
    save_maintainer_roster,
)
from .maintainers import collect_maintainer_activity
from .models import (
    CohortMetadataSnapshot,
    CommitRecord,
    CommitSnapshot,
    IssueEvent,
    IssueRecord,
    IssueSnapshot,
    MaintainerActivitySnapshot,
    PullRequestRecord,
    RepositoryContribution,
    RepositorySnapshot,
    ResponseEvent,
    StarHistoryWeek,
    StarSnapshot,
    Submission,
)
from .snapshots import load_snapshot, save_snapshot
from .star_snapshots import load_star_snapshot, save_star_snapshot
from .stars import collect_star_snapshot

__all__ = [
    "APPROVED_LABEL",
    "CohortMetadataSnapshot",
    "CommitRecord",
    "CommitSnapshot",
    "IssueEvent",
    "IssueRecord",
    "IssueSnapshot",
    "MaintainerActivitySnapshot",
    "PullRequestRecord",
    "RepositoryContribution",
    "RepositoryLinkNotFoundError",
    "RepositorySnapshot",
    "ResponseEvent",
    "StarHistoryWeek",
    "StarSnapshot",
    "Submission",
    "SubmissionNotFoundError",
    "UnsupportedRepositoryHostError",
    "UnsupportedRepositoryWarning",
    "collect_cohort_metadata",
    "collect_commit_snapshot",
    "collect_issue_snapshot",
    "collect_maintainer_activity",
    "collect_repository_snapshot",
    "collect_star_snapshot",
    "create_github",
    "get_accepted_submissions",
    "get_submission",
    "load_cohort_metadata",
    "load_commit_snapshot",
    "load_issue_snapshot",
    "load_maintainer_activity",
    "load_maintainer_roster",
    "load_snapshot",
    "load_star_snapshot",
    "save_cohort_metadata",
    "save_commit_snapshot",
    "save_issue_snapshot",
    "save_maintainer_activity",
    "save_maintainer_roster",
    "save_snapshot",
    "save_star_snapshot",
]
