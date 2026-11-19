from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import csv
import unittest

from reflections.analysis import issue_rows, write_issue_csv
from reflections.datasources.github.models import IssueEvent, IssueRecord, IssueSnapshot


def timestamp(day: int) -> datetime:
    return datetime(2025, 1, day, tzinfo=UTC)


class IssueTableTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = IssueSnapshot(
            repository="example/project",
            accepted_at=timestamp(10),
            fetched_at=timestamp(30),
            window_days=10,
            issues=(
                IssueRecord(
                    number=1,
                    title="Before",
                    url="https://github.com/example/project/issues/1",
                    author_login="reporter",
                    created_at=timestamp(5),
                    closed_at=timestamp(9),
                    events=(
                        IssueEvent(
                            kind="commented",
                            created_at=timestamp(6),
                            actor_login="maintainer",
                            actor_association="MEMBER",
                        ),
                    ),
                ),
                IssueRecord(
                    number=2,
                    title="After",
                    url="https://github.com/example/project/issues/2",
                    author_login="reporter",
                    created_at=timestamp(12),
                    closed_at=None,
                    events=(
                        IssueEvent(
                            kind="labeled",
                            created_at=timestamp(14),
                            actor_login="maintainer",
                            actor_association=None,
                        ),
                    ),
                ),
                IssueRecord(
                    number=3,
                    title="Unaddressed",
                    url="https://github.com/example/project/issues/3",
                    author_login="reporter",
                    created_at=timestamp(15),
                    closed_at=None,
                ),
            ),
        )

    def test_rows_distinguish_acknowledgement_triage_and_closure(self):
        rows = {
            row["issue_number"]: row
            for row in issue_rows([self.snapshot], window_days=10)
        }

        acknowledged = rows[1]
        self.assertEqual(acknowledged["period"], "before_acceptance")
        self.assertEqual(acknowledged["acknowledgement_days"], 1.0)
        self.assertFalse(acknowledged["has_triage"])
        self.assertEqual(acknowledged["addressed_days"], 1.0)
        self.assertEqual(acknowledged["time_to_close_days"], 4.0)
        self.assertFalse(acknowledged["resolution_censored"])

        triaged = rows[2]
        self.assertEqual(triaged["period"], "after_acceptance")
        self.assertFalse(triaged["has_acknowledgement"])
        self.assertEqual(triaged["triage_days"], 2.0)
        self.assertEqual(triaged["addressed_days"], 2.0)
        self.assertTrue(triaged["resolution_censored"])

        unaddressed = rows[3]
        self.assertFalse(unaddressed["has_been_addressed"])
        self.assertEqual(unaddressed["addressed_observation_days"], 15.0)
        self.assertTrue(unaddressed["addressed_censored"])

    def test_nonmaintainer_and_author_comments_are_not_acknowledgements(self):
        issue = IssueRecord(
            number=4,
            title="Question",
            url="https://github.com/example/project/issues/4",
            author_login="reporter",
            created_at=timestamp(12),
            closed_at=None,
            events=(
                IssueEvent(
                    kind="commented",
                    created_at=timestamp(13),
                    actor_login="reporter",
                    actor_association="MEMBER",
                ),
                IssueEvent(
                    kind="commented",
                    created_at=timestamp(14),
                    actor_login="visitor",
                    actor_association="NONE",
                ),
            ),
        )
        snapshot = IssueSnapshot(
            repository=self.snapshot.repository,
            accepted_at=self.snapshot.accepted_at,
            fetched_at=self.snapshot.fetched_at,
            window_days=10,
            issues=(issue,),
        )

        row = next(issue_rows([snapshot], window_days=10))

        self.assertFalse(row["has_acknowledgement"])

    def test_csv_is_sorted_by_repository_and_issue_number(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "issues.csv"
            write_issue_csv([self.snapshot], path, window_days=10)
            with path.open(encoding="utf-8", newline="") as input_file:
                rows = list(csv.DictReader(input_file))

        self.assertEqual([row["issue_number"] for row in rows], ["1", "2", "3"])

    def test_analysis_window_cannot_exceed_snapshot(self):
        with self.assertRaisesRegex(ValueError, "exceeds"):
            list(issue_rows([self.snapshot], window_days=11))


if __name__ == "__main__":
    unittest.main()
