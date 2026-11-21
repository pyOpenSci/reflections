"""Collect commit activity independently from pull-request snapshots."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from github import Github

from .client import create_github
from .models import CommitRecord, CommitSnapshot


def collect_commit_snapshot(
    repository: str,
    *,
    accepted_at: datetime,
    window_days: int = 365,
    github: Github | None = None,
    existing_snapshot: CommitSnapshot | None = None,
    on_progress: Callable[[CommitSnapshot, int, int, str, bool], None]
    | None = None,
) -> CommitSnapshot:
    """Collect default-branch commits in a matched acceptance window."""

    if window_days <= 0:
        raise ValueError("window_days must be positive")
    _validate_existing_snapshot(
        existing_snapshot,
        repository=repository,
        accepted_at=accepted_at,
        window_days=window_days,
    )

    client = github or create_github()
    github_repository = client.get_repo(repository)
    start = accepted_at - timedelta(days=window_days)
    end = accepted_at + timedelta(days=window_days)
    candidates = list(github_repository.get_commits(since=start, until=end))
    collected = {
        commit.sha: commit
        for commit in (
            existing_snapshot.commits if existing_snapshot is not None else ()
        )
    }

    for completed, github_commit in enumerate(candidates, start=1):
        cached = github_commit.sha in collected
        if not cached:
            commit = _commit_record(github_commit)
            if start <= commit.committed_at <= end:
                collected[commit.sha] = commit
        snapshot = _commit_snapshot(
            repository,
            default_branch=github_repository.default_branch,
            accepted_at=accepted_at,
            window_days=window_days,
            commits=collected.values(),
        )
        if on_progress is not None:
            on_progress(
                snapshot,
                completed,
                len(candidates),
                github_commit.sha,
                cached,
            )

    return _commit_snapshot(
        repository,
        default_branch=github_repository.default_branch,
        accepted_at=accepted_at,
        window_days=window_days,
        commits=collected.values(),
    )


def _commit_record(commit: Any) -> CommitRecord:
    git_commit = commit.commit
    git_author = git_commit.author
    git_committer = git_commit.committer
    committed_at = getattr(git_committer, "date", None) or getattr(
        git_author, "date", None
    )
    if committed_at is None:
        raise ValueError(f"Commit {commit.sha} has no author or committer timestamp")

    author_login = _login(commit.author)
    committer_login = _login(commit.committer)
    parent_count = len(commit.parents)
    return CommitRecord(
        sha=commit.sha,
        url=commit.html_url,
        message=git_commit.message,
        authored_at=getattr(git_author, "date", None),
        committed_at=committed_at,
        author_login=author_login,
        committer_login=committer_login,
        author_name=getattr(git_author, "name", None),
        committer_name=getattr(git_committer, "name", None),
        parent_count=parent_count,
        is_merge=parent_count > 1,
        author_is_bot=_is_bot(author_login),
        committer_is_bot=_is_bot(committer_login),
    )


def _commit_snapshot(
    repository: str,
    *,
    default_branch: str,
    accepted_at: datetime,
    window_days: int,
    commits: Any,
) -> CommitSnapshot:
    return CommitSnapshot(
        repository=repository,
        default_branch=default_branch,
        accepted_at=accepted_at,
        fetched_at=datetime.now(UTC),
        window_days=window_days,
        commits=tuple(sorted(commits, key=lambda commit: (commit.committed_at, commit.sha))),
    )


def _validate_existing_snapshot(
    snapshot: CommitSnapshot | None,
    *,
    repository: str,
    accepted_at: datetime,
    window_days: int,
) -> None:
    if snapshot is None:
        return
    if snapshot.repository.casefold() != repository.casefold():
        raise ValueError("checkpoint repository does not match collection target")
    if snapshot.accepted_at != accepted_at:
        raise ValueError("checkpoint acceptance time does not match collection target")
    if snapshot.window_days != window_days:
        raise ValueError("checkpoint window does not match collection window")


def _login(user: Any | None) -> str | None:
    return None if user is None else user.login


def _is_bot(login: str | None) -> bool:
    return login is not None and login.casefold().endswith("[bot]")
