from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import csv
import unittest

from reflections.analysis import star_rows, write_star_csv
from reflections.datasources.github.models import StarHistoryWeek, StarSnapshot


class StarTableTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = StarSnapshot(
            repository="example/project",
            accepted_at=datetime(2025, 1, 7, tzinfo=UTC),
            fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
            current_stargazers=4,
            weeks=(
                StarHistoryWeek(
                    week_started_at=datetime(2025, 1, 5, tzinfo=UTC),
                    total=4,
                    days=(1, 0, 2, 0, 1, 0, 0),
                ),
            ),
            pages_collected=1,
            total_pages=1,
            complete=True,
        )

    def test_expands_week_into_daily_cumulative_rows(self):
        rows = list(star_rows([self.snapshot], window_days=3))

        self.assertEqual(len(rows), 7)
        self.assertEqual([row["new_stars"] for row in rows], [1, 0, 2, 0, 1, 0, 0])
        self.assertEqual(
            [row["cumulative_star_acquisitions"] for row in rows],
            [1, 1, 3, 3, 4, 4, 4],
        )
        self.assertEqual(rows[0]["period"], "before_acceptance")
        self.assertEqual(rows[3]["period"], "after_acceptance")
        self.assertTrue(rows[0]["within_window"])
        self.assertFalse(rows[-1]["within_window"])

    def test_incomplete_snapshot_is_rejected(self):
        incomplete = StarSnapshot(
            repository=self.snapshot.repository,
            accepted_at=self.snapshot.accepted_at,
            fetched_at=self.snapshot.fetched_at,
            current_stargazers=4,
            complete=False,
        )

        with self.assertRaisesRegex(ValueError, "incomplete"):
            list(star_rows([incomplete]))

    def test_csv_is_sorted_and_has_one_row_per_day(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "stars.csv"
            write_star_csv([self.snapshot], path)
            with path.open(encoding="utf-8", newline="") as input_file:
                rows = list(csv.DictReader(input_file))

        self.assertEqual(len(rows), 7)
        self.assertEqual(rows[0]["star_date"], "2025-01-05")
        self.assertEqual(rows[-1]["star_date"], "2025-01-11")


if __name__ == "__main__":
    unittest.main()
