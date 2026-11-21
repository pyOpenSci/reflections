"""GitHub-backed data collection for reflections."""

from .client import (
    APPROVED_LABEL,
    RepositoryLinkNotFoundError,
    SubmissionNotFoundError,
    UnsupportedRepositoryHostError,
    UnsupportedRepositoryWarning,
    create_github,
    get_accepted_submissions,
    get_submission,
)
from .cohort import collect_cohort_metadata
from .cohort_snapshots import load_cohort_metadata, save_cohort_metadata
from .commit_snapshots import load_commit_snapshot, save_commit_snapshot
from .commits import collect_commit_snapshot
from .history_index_snapshots import load_history_index, save_history_index
from .history_indexes import collect_history_index
from .interaction_snapshots import (
    load_interaction_snapshot,
    save_interaction_snapshot,
)
from .interactions import collect_interaction_stream
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
    HistoryIndexRecord,
    HistoryIndexSnapshot,
    InteractionRecord,
    InteractionSnapshot,
    MaintainerActivitySnapshot,
    RepositoryContribution,
    StarHistoryWeek,
    StarSnapshot,
    Submission,
)
from .star_snapshots import load_star_snapshot, save_star_snapshot
from .stars import collect_star_snapshot

__all__ = [
    "APPROVED_LABEL",
    "CohortMetadataSnapshot",
    "CommitRecord",
    "CommitSnapshot",
    "HistoryIndexRecord",
    "HistoryIndexSnapshot",
    "InteractionRecord",
    "InteractionSnapshot",
    "MaintainerActivitySnapshot",
    "RepositoryContribution",
    "RepositoryLinkNotFoundError",
    "StarHistoryWeek",
    "StarSnapshot",
    "Submission",
    "SubmissionNotFoundError",
    "UnsupportedRepositoryHostError",
    "UnsupportedRepositoryWarning",
    "collect_cohort_metadata",
    "collect_commit_snapshot",
    "collect_history_index",
    "collect_interaction_stream",
    "collect_maintainer_activity",
    "collect_star_snapshot",
    "create_github",
    "get_accepted_submissions",
    "get_submission",
    "load_cohort_metadata",
    "load_commit_snapshot",
    "load_history_index",
    "load_interaction_snapshot",
    "load_maintainer_activity",
    "load_maintainer_roster",
    "load_star_snapshot",
    "save_cohort_metadata",
    "save_commit_snapshot",
    "save_history_index",
    "save_interaction_snapshot",
    "save_maintainer_activity",
    "save_maintainer_roster",
    "save_star_snapshot",
]
