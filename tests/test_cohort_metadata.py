import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from reflections.analysis.cohort_tables import cohort_rows
from reflections.datasources.github.cohort import collect_cohort_metadata
from reflections.datasources.github.cohort_snapshots import (
    load_cohort_metadata,
    save_cohort_metadata,
)
from reflections.datasources.github.models import Submission


def timestamp(year, month, day):
    return datetime(year, month, day, tzinfo=UTC)


class FakeGithub:
    def get_repo(self, name):
        if name == "PyOpenSci/software-submission":
            return SimpleNamespace(
                get_issue=lambda number: SimpleNamespace(
                    created_at=timestamp(2024, 1, 1)
                )
            )
        commit = SimpleNamespace(
            commit=SimpleNamespace(
                committer=SimpleNamespace(date=timestamp(2024, 5, 1)), author=None
            )
        )
        return SimpleNamespace(
            created_at=timestamp(2020, 1, 1),
            archived=False,
            fork=False,
            size=10,
            default_branch="main",
            get_commits=lambda **kwargs: [commit],
        )


class CohortMetadataTests(unittest.TestCase):
    def setUp(self):
        self.submission = Submission(
            package="example",
            repository="example/example",
            accepted_at=timestamp(2024, 4, 1),
            issue_number=12,
            issue_url="https://github.com/PyOpenSci/software-submission/issues/12",
            title="Example submission",
            maintainers=("one", "two"),
        )

    def test_collects_submission_and_repository_dates(self):
        snapshot = collect_cohort_metadata(self.submission, github=FakeGithub())
        self.assertEqual(snapshot.submitted_at, timestamp(2024, 1, 1))
        self.assertEqual(snapshot.repository_created_at, timestamp(2020, 1, 1))
        self.assertEqual(snapshot.last_default_branch_commit_at, timestamp(2024, 5, 1))
        self.assertEqual(snapshot.maintainer_count, 2)

    def test_snapshot_round_trip(self):
        snapshot = collect_cohort_metadata(self.submission, github=FakeGithub())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            save_cohort_metadata(snapshot, path)
            self.assertEqual(load_cohort_metadata(path), snapshot)

    def test_cohort_row_derives_durations(self):
        snapshot = collect_cohort_metadata(self.submission, github=FakeGithub())
        row = next(cohort_rows([snapshot]))
        self.assertEqual(row["review_days"], 91)
        self.assertEqual(row["repository_age_at_submission_days"], 1461)
        self.assertEqual(row["repository_age_at_acceptance_days"], 1552)


if __name__ == "__main__":
    unittest.main()
