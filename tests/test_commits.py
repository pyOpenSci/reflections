from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from reflections.datasources.github import (
    collect_commit_snapshot,
    load_commit_snapshot,
    save_commit_snapshot,
)
from reflections.datasources.github.models import CommitRecord, CommitSnapshot


ACCEPTED_AT = datetime(2025, 1, 15, tzinfo=UTC)


def github_commit(
    sha: str,
    committed_at: datetime,
    *,
    parents: int = 1,
    author_login: str | None = "author",
) -> SimpleNamespace:
    author_user = None if author_login is None else SimpleNamespace(login=author_login)
    git_author = SimpleNamespace(
        date=committed_at - timedelta(hours=1),
        name="Author Name",
    )
    git_committer = SimpleNamespace(date=committed_at, name="Committer Name")
    return SimpleNamespace(
        sha=sha,
        html_url=f"https://github.com/example/project/commit/{sha}",
        author=author_user,
        committer=SimpleNamespace(login="committer"),
        parents=[SimpleNamespace() for _ in range(parents)],
        commit=SimpleNamespace(
            author=git_author,
            committer=git_committer,
            message=f"Commit {sha}",
        ),
    )


class CommitCollectionTests(unittest.TestCase):
    def test_collects_default_branch_commits_in_server_side_window(self):
        commits = [
            github_commit("a", ACCEPTED_AT - timedelta(days=2)),
            github_commit("b", ACCEPTED_AT + timedelta(days=2), parents=2),
        ]
        queries = []
        repository = SimpleNamespace(
            default_branch="main",
            get_commits=lambda **query: queries.append(query) or commits,
        )
        github = SimpleNamespace(get_repo=lambda name: repository)

        snapshot = collect_commit_snapshot(
            "example/project",
            accepted_at=ACCEPTED_AT,
            window_days=5,
            github=github,
        )

        self.assertEqual([commit.sha for commit in snapshot.commits], ["a", "b"])
        self.assertFalse(snapshot.commits[0].is_merge)
        self.assertTrue(snapshot.commits[1].is_merge)
        self.assertEqual(snapshot.default_branch, "main")
        self.assertEqual(
            queries,
            [
                {
                    "since": ACCEPTED_AT - timedelta(days=5),
                    "until": ACCEPTED_AT + timedelta(days=5),
                }
            ],
        )

    def test_resumes_existing_commit_snapshot(self):
        existing_record = CommitRecord(
            sha="a",
            url="https://github.com/example/project/commit/a",
            message="Commit a",
            authored_at=ACCEPTED_AT - timedelta(days=2, hours=1),
            committed_at=ACCEPTED_AT - timedelta(days=2),
            author_login="author",
            committer_login="committer",
            author_name="Author Name",
            committer_name="Committer Name",
            parent_count=1,
            is_merge=False,
            author_is_bot=False,
            committer_is_bot=False,
        )
        checkpoint = CommitSnapshot(
            repository="example/project",
            default_branch="main",
            accepted_at=ACCEPTED_AT,
            fetched_at=ACCEPTED_AT,
            window_days=5,
            commits=(existing_record,),
        )
        repository = SimpleNamespace(
            default_branch="main",
            get_commits=lambda **query: [
                github_commit("a", ACCEPTED_AT - timedelta(days=2)),
                github_commit("b", ACCEPTED_AT + timedelta(days=2)),
            ],
        )
        progress = []

        snapshot = collect_commit_snapshot(
            "example/project",
            accepted_at=ACCEPTED_AT,
            window_days=5,
            github=SimpleNamespace(get_repo=lambda name: repository),
            existing_snapshot=checkpoint,
            on_progress=lambda snapshot, current, total, sha, cached: progress.append(
                (current, total, sha, cached)
            ),
        )

        self.assertEqual([commit.sha for commit in snapshot.commits], ["a", "b"])
        self.assertEqual(progress, [(1, 2, "a", True), (2, 2, "b", False)])

    def test_commit_snapshot_round_trip(self):
        record = CommitRecord(
            sha="abc",
            url="https://github.com/example/project/commit/abc",
            message="A commit",
            authored_at=ACCEPTED_AT - timedelta(hours=1),
            committed_at=ACCEPTED_AT,
            author_login="author",
            committer_login="committer",
            author_name="Author Name",
            committer_name="Committer Name",
            parent_count=1,
            is_merge=False,
            author_is_bot=False,
            committer_is_bot=False,
        )
        snapshot = CommitSnapshot(
            repository="example/project",
            default_branch="main",
            accepted_at=ACCEPTED_AT,
            fetched_at=ACCEPTED_AT + timedelta(days=10),
            window_days=365,
            commits=(record,),
        )

        with TemporaryDirectory() as directory:
            path = Path(directory) / "commits" / "snapshot.json"
            save_commit_snapshot(snapshot, path)
            restored = load_commit_snapshot(path)

        self.assertEqual(restored, snapshot)


if __name__ == "__main__":
    unittest.main()
