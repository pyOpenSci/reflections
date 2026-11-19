from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import csv
import unittest

from reflections.analysis import pull_request_rows, write_pull_request_csv
from reflections.datasources.github.models import (
    PullRequestRecord,
    RepositorySnapshot,
    ResponseEvent,
)


def timestamp(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=UTC)


class PullRequestTableTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = RepositorySnapshot(
            repository="example/package",
            accepted_at=timestamp(2025, 1, 1),
            fetched_at=timestamp(2026, 1, 1),
            pull_requests=(
                PullRequestRecord(
                    number=2,
                    title="After acceptance",
                    url="https://github.com/example/package/pull/2",
                    author_login="contributor",
                    created_at=timestamp(2025, 2, 1),
                    closed_at=None,
                    merged_at=None,
                    responses=(),
                ),
                PullRequestRecord(
                    number=1,
                    title="Before acceptance",
                    url="https://github.com/example/package/pull/1",
                    author_login="contributor",
                    created_at=timestamp(2024, 12, 15),
                    closed_at=timestamp(2024, 12, 20),
                    merged_at=timestamp(2024, 12, 20),
                    responses=(
                        ResponseEvent(
                            kind="review",
                            created_at=timestamp(2024, 12, 17),
                            author_login="maintainer",
                            author_association="MEMBER",
                        ),
                    ),
                ),
            ),
        )

    def test_rows_include_all_prs_and_mark_matched_window(self):
        rows = list(pull_request_rows([self.snapshot], window_days=30))

        self.assertEqual(len(rows), 2)
        self.assertFalse(rows[0]["within_window"])
        self.assertTrue(rows[1]["within_window"])
        self.assertIsNone(rows[0]["response_days"])
        self.assertEqual(rows[1]["response_days"], 2.0)

    def test_csv_is_sorted_by_repository_and_pr_number(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "derived" / "pull_requests.csv"
            write_pull_request_csv([self.snapshot], path)
            with path.open(encoding="utf-8", newline="") as input_file:
                rows = list(csv.DictReader(input_file))

        self.assertEqual([row["pr_number"] for row in rows], ["1", "2"])
        self.assertEqual(rows[0]["has_response"], "True")
        self.assertEqual(rows[1]["has_response"], "False")

    def test_window_must_be_positive(self):
        with self.assertRaisesRegex(ValueError, "window_days"):
            list(pull_request_rows([self.snapshot], window_days=0))

    def test_analysis_window_cannot_exceed_snapshot_window(self):
        limited_snapshot = RepositorySnapshot(
            repository=self.snapshot.repository,
            accepted_at=self.snapshot.accepted_at,
            fetched_at=self.snapshot.fetched_at,
            pull_requests=self.snapshot.pull_requests,
            window_days=30,
        )

        with self.assertRaisesRegex(ValueError, "exceeds"):
            list(pull_request_rows([limited_snapshot], window_days=31))


if __name__ == "__main__":
    unittest.main()
