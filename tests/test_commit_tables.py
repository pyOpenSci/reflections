from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import csv
import unittest

from reflections.analysis import commit_rows, write_commit_csv
from reflections.datasources.github.models import CommitRecord, CommitSnapshot


ACCEPTED_AT = datetime(2025, 1, 1, tzinfo=UTC)


def commit(sha: str, days: int, *, merge: bool = False) -> CommitRecord:
    committed_at = ACCEPTED_AT + timedelta(days=days)
    return CommitRecord(
        sha=sha,
        url=f"https://github.com/example/project/commit/{sha}",
        message=f"Commit {sha}",
        authored_at=committed_at - timedelta(hours=1),
        committed_at=committed_at,
        author_login="author",
        committer_login="committer",
        author_name="Author Name",
        committer_name="Committer Name",
        parent_count=2 if merge else 1,
        is_merge=merge,
        author_is_bot=False,
        committer_is_bot=False,
    )


class CommitTableTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = CommitSnapshot(
            repository="example/project",
            default_branch="main",
            accepted_at=ACCEPTED_AT,
            fetched_at=ACCEPTED_AT + timedelta(days=400),
            window_days=365,
            commits=(commit("b", 20, merge=True), commit("a", -10)),
        )

    def test_rows_classify_period_and_retain_merge_flag(self):
        rows = list(commit_rows([self.snapshot]))

        self.assertEqual(
            [row["period"] for row in rows],
            ["after_acceptance", "before_acceptance"],
        )
        self.assertTrue(rows[0]["is_merge"])
        self.assertEqual(rows[1]["days_from_acceptance"], -10.0)

    def test_csv_is_sorted_by_commit_time(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "derived" / "commits.csv"
            write_commit_csv([self.snapshot], path)
            with path.open(encoding="utf-8", newline="") as input_file:
                rows = list(csv.DictReader(input_file))

        self.assertEqual([row["sha"] for row in rows], ["a", "b"])

    def test_window_cannot_exceed_snapshot(self):
        with self.assertRaisesRegex(ValueError, "exceeds"):
            list(commit_rows([self.snapshot], window_days=366))

    def test_excludes_package_without_three_months_of_follow_up(self):
        recent_snapshot = CommitSnapshot(
            repository="example/recent",
            default_branch="main",
            accepted_at=ACCEPTED_AT,
            fetched_at=ACCEPTED_AT + timedelta(days=89),
            window_days=365,
            commits=(commit("recent", 20),),
        )

        self.assertEqual(list(commit_rows([recent_snapshot])), [])

    def test_follow_up_threshold_is_configurable(self):
        recent_snapshot = CommitSnapshot(
            repository="example/recent",
            default_branch="main",
            accepted_at=ACCEPTED_AT,
            fetched_at=ACCEPTED_AT + timedelta(days=30),
            window_days=365,
            commits=(commit("recent", 20),),
        )

        rows = list(
            commit_rows([recent_snapshot], minimum_post_acceptance_days=30)
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["post_acceptance_observation_days"], 30.0)


if __name__ == "__main__":
    unittest.main()
