from datetime import UTC, date, datetime
import unittest

from reflections.analysis import maintainer_rows, roster_rows
from reflections.datasources.github.models import (
    MaintainerActivitySnapshot,
    RepositoryContribution,
    Submission,
)


START = datetime(2025, 1, 1, tzinfo=UTC)
END = datetime(2026, 1, 1, tzinfo=UTC)


def submission(maintainers=("maintainer",)):
    return Submission(
        package="project",
        repository="example/project",
        accepted_at=START,
        issue_number=1,
        issue_url="https://github.com/pyOpenSci/software-submission/issues/1",
        title="Project",
        maintainers=maintainers,
    )


def snapshot(*, truncated=False):
    return MaintainerActivitySnapshot(
        requested_login="maintainer",
        canonical_login="Maintainer",
        user_exists=True,
        fetched_at=END,
        observation_start=START,
        observation_end=END,
        total_commits=20,
        total_issues=4,
        total_pull_requests=3,
        total_pull_request_reviews=5,
        restricted_contributions=7,
        last_activity_on=date(2025, 12, 20),
        repositories=(
            RepositoryContribution("Example/Project", 8, 2, 1, 3),
        ),
        commits_truncated=truncated,
    )


class MaintainerTableTests(unittest.TestCase):
    def test_calculates_recent_activity_and_package_share(self):
        row = next(maintainer_rows([submission()], [snapshot()]))

        self.assertEqual(row["total_observed_public_activity"], 32)
        self.assertEqual(row["package_activity_lower_bound"], 14)
        self.assertTrue(row["package_activity_exact"])
        self.assertEqual(row["package_activity_share"], 14 / 32)
        self.assertEqual(row["days_since_last_activity"], 12)
        self.assertTrue(row["has_restricted_contributions"])

    def test_missing_package_in_truncated_list_is_unknown(self):
        activity = snapshot(truncated=True)
        activity = MaintainerActivitySnapshot(
            **{
                **activity.__dict__,
                "repositories": (),
            }
        )

        row = next(maintainer_rows([submission()], [activity]))

        self.assertIsNone(row["package_commits"])
        self.assertFalse(row["package_activity_exact"])
        self.assertIsNone(row["package_activity_share"])

    def test_roster_coverage_retains_package_without_maintainers(self):
        row = next(roster_rows([submission(maintainers=())]))

        self.assertFalse(row["has_maintainer_roster"])
        self.assertEqual(row["maintainer_count"], 0)

    def test_missing_user_snapshot_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "No activity snapshot"):
            list(maintainer_rows([submission()], []))


if __name__ == "__main__":
    unittest.main()
