from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from reflections.datasources.github import (
    IssueEvent,
    IssueRecord,
    IssueSnapshot,
    collect_issue_snapshot,
    load_issue_snapshot,
    save_issue_snapshot,
)


def timestamp(day: int) -> datetime:
    return datetime(2025, 1, day, tzinfo=UTC)


def github_issue(number: int, day: int, *, is_pull_request: bool = False):
    user = SimpleNamespace(login="reporter")
    timeline = [
        SimpleNamespace(
            event="commented",
            created_at=timestamp(day + 1),
            user=SimpleNamespace(login="maintainer"),
            actor=None,
            author_association="MEMBER",
        ),
        SimpleNamespace(
            event="labeled",
            created_at=timestamp(day + 2),
            user=None,
            actor=SimpleNamespace(login="maintainer"),
            author_association=None,
        ),
    ]
    return SimpleNamespace(
        number=number,
        title=f"Issue {number}",
        html_url=f"https://github.com/example/project/issues/{number}",
        user=user,
        created_at=timestamp(day),
        closed_at=None,
        pull_request=SimpleNamespace() if is_pull_request else None,
        get_timeline=lambda: timeline,
    )


class IssueCollectionTests(unittest.TestCase):
    def test_collects_issues_in_window_and_excludes_pull_requests(self):
        issues = [
            github_issue(1, 1),
            github_issue(2, 8),
            github_issue(3, 9, is_pull_request=True),
            github_issue(4, 12),
            github_issue(5, 20),
        ]
        queries = []
        repository = SimpleNamespace(
            get_issues=lambda **query: queries.append(query) or issues
        )
        github = SimpleNamespace(get_repo=lambda name: repository)

        snapshot = collect_issue_snapshot(
            "example/project",
            accepted_at=timestamp(10),
            window_days=3,
            github=github,
        )

        self.assertEqual([issue.number for issue in snapshot.issues], [2, 4])
        self.assertEqual(
            [event.kind for event in snapshot.issues[0].events],
            ["commented", "labeled"],
        )
        self.assertEqual(
            queries,
            [{"state": "all", "sort": "created", "direction": "asc"}],
        )

    def test_resumes_cached_issue(self):
        calls = []
        issue = github_issue(2, 8)
        issue.get_timeline = lambda: calls.append(2) or []
        repository = SimpleNamespace(get_issues=lambda **query: [issue])
        github = SimpleNamespace(get_repo=lambda name: repository)
        cached = IssueRecord(
            number=2,
            title="Issue 2",
            url="https://github.com/example/project/issues/2",
            author_login="reporter",
            created_at=timestamp(8),
            closed_at=None,
        )
        checkpoint = IssueSnapshot(
            repository="example/project",
            accepted_at=timestamp(10),
            fetched_at=timestamp(15),
            window_days=3,
            issues=(cached,),
        )
        progress = []

        snapshot = collect_issue_snapshot(
            "example/project",
            accepted_at=timestamp(10),
            window_days=3,
            github=github,
            existing_snapshot=checkpoint,
            on_progress=(
                lambda snapshot, current, total, number, cached: progress.append(
                    (current, total, number, cached)
                )
            ),
        )

        self.assertEqual(calls, [])
        self.assertEqual(snapshot.issues, (cached,))
        self.assertEqual(progress, [(1, 1, 2, True)])

    def test_issue_snapshot_round_trip(self):
        snapshot = IssueSnapshot(
            repository="example/project",
            accepted_at=timestamp(10),
            fetched_at=timestamp(15),
            window_days=365,
            issues=(
                IssueRecord(
                    number=2,
                    title="A bug",
                    url="https://github.com/example/project/issues/2",
                    author_login="reporter",
                    created_at=timestamp(8),
                    closed_at=timestamp(12),
                    events=(
                        IssueEvent(
                            kind="commented",
                            created_at=timestamp(9),
                            actor_login="maintainer",
                            actor_association="MEMBER",
                        ),
                    ),
                ),
            ),
        )
        with TemporaryDirectory() as directory:
            path = Path(directory) / "issues.json"
            save_issue_snapshot(snapshot, path)
            loaded = load_issue_snapshot(path)

        self.assertEqual(loaded, snapshot)

    def test_rejects_mismatched_checkpoint(self):
        checkpoint = IssueSnapshot(
            repository="other/project",
            accepted_at=timestamp(10),
            fetched_at=timestamp(15),
            window_days=3,
        )
        with self.assertRaisesRegex(ValueError, "checkpoint repository"):
            collect_issue_snapshot(
                "example/project",
                accepted_at=timestamp(10),
                window_days=3,
                github=SimpleNamespace(),
                existing_snapshot=checkpoint,
            )


if __name__ == "__main__":
    unittest.main()
