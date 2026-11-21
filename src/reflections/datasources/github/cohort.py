"""Collect stable submission and repository metadata for the cohort."""

from datetime import UTC, datetime

from github import Github

from .client import SUBMISSIONS_REPOSITORY, create_github
from .models import CohortMetadataSnapshot, Submission


def collect_cohort_metadata(
    submission: Submission,
    *,
    github: Github | None = None,
    submissions_repository: str = SUBMISSIONS_REPOSITORY,
) -> CohortMetadataSnapshot:
    """Collect the two timestamps needed for cohort-level durations."""

    client = github or create_github()
    issue = client.get_repo(submissions_repository).get_issue(submission.issue_number)
    repository = client.get_repo(submission.repository)
    last_commit_at = None
    if repository.size > 0:
        commit = repository.get_commits(sha=repository.default_branch)[0].commit
        signature = commit.committer or commit.author
        if signature is not None:
            last_commit_at = signature.date
    return CohortMetadataSnapshot(
        package=submission.package,
        repository=submission.repository,
        issue_number=submission.issue_number,
        issue_url=submission.issue_url,
        submitted_at=issue.created_at,
        accepted_at=submission.accepted_at,
        repository_created_at=repository.created_at,
        last_default_branch_commit_at=last_commit_at,
        default_branch=repository.default_branch,
        fetched_at=datetime.now(UTC),
        maintainer_count=len(submission.maintainers),
        repository_archived=repository.archived,
        repository_is_fork=repository.fork,
    )
