from datetime import UTC, date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from reflections.datasources.github import (
    MaintainerActivitySnapshot,
    RepositoryContribution,
    Submission,
    collect_maintainer_activity,
    load_maintainer_activity,
    load_maintainer_roster,
    save_maintainer_activity,
    save_maintainer_roster,
)


START = datetime(2025, 1, 1, tzinfo=UTC)
END = datetime(2026, 1, 1, tzinfo=UTC)


class FakeRequester:
    def __init__(self, response):
        self.response = response
        self.request = None

    def requestJsonAndCheck(self, method, url, *, input):
        self.request = (method, url, input)
        return {}, self.response


def group(repository: str, count: int):
    return {
        "repository": {"nameWithOwner": repository},
        "contributions": {"totalCount": count},
    }


def response():
    return {
        "data": {
            "rateLimit": {"remaining": 4321},
            "user": {
                "login": "Maintainer",
                "contributionsCollection": {
                    "totalCommitContributions": 20,
                    "totalIssueContributions": 4,
                    "totalPullRequestContributions": 3,
                    "totalPullRequestReviewContributions": 5,
                    "totalRepositoriesWithContributedCommits": 2,
                    "totalRepositoriesWithContributedIssues": 1,
                    "totalRepositoriesWithContributedPullRequests": 1,
                    "totalRepositoriesWithContributedPullRequestReviews": 1,
                    "restrictedContributionsCount": 7,
                    "contributionCalendar": {
                        "weeks": [
                            {
                                "contributionDays": [
                                    {"date": "2025-03-01", "contributionCount": 2},
                                    {"date": "2025-03-02", "contributionCount": 0},
                                ]
                            }
                        ]
                    },
                    "commitContributionsByRepository": [
                        group("example/project", 8)
                    ],
                    "issueContributionsByRepository": [
                        group("example/project", 2)
                    ],
                    "pullRequestContributionsByRepository": [
                        group("example/project", 1)
                    ],
                    "pullRequestReviewContributionsByRepository": [
                        group("example/project", 3)
                    ],
                },
            },
        }
    }


class MaintainerCollectionTests(unittest.TestCase):
    def test_collects_totals_repository_counts_and_visibility_flags(self):
        requester = FakeRequester(response())
        github = SimpleNamespace(_Github__requester=requester)

        snapshot = collect_maintainer_activity(
            "maintainer",
            observation_start=START,
            observation_end=END,
            github=github,
        )

        self.assertEqual(snapshot.canonical_login, "Maintainer")
        self.assertEqual(snapshot.total_commits, 20)
        self.assertEqual(snapshot.restricted_contributions, 7)
        self.assertEqual(snapshot.last_activity_on, date(2025, 3, 1))
        self.assertEqual(snapshot.repositories[0].commits, 8)
        self.assertEqual(snapshot.repositories[0].pull_request_reviews, 3)
        self.assertTrue(snapshot.commits_truncated)
        self.assertFalse(snapshot.issues_truncated)
        self.assertEqual(snapshot.graphql_rate_remaining, 4321)
        self.assertEqual(requester.request[0:2], ("POST", "/graphql"))

    def test_missing_user_is_retained(self):
        requester = FakeRequester(
            {"data": {"rateLimit": {"remaining": 100}, "user": None}}
        )
        github = SimpleNamespace(_Github__requester=requester)

        snapshot = collect_maintainer_activity(
            "renamed-user",
            observation_start=START,
            observation_end=END,
            github=github,
        )

        self.assertFalse(snapshot.user_exists)
        self.assertEqual(snapshot.total_commits, 0)

    def test_activity_snapshot_round_trip(self):
        snapshot = MaintainerActivitySnapshot(
            requested_login="maintainer",
            canonical_login="Maintainer",
            user_exists=True,
            fetched_at=END,
            observation_start=START,
            observation_end=END,
            total_commits=5,
            total_issues=2,
            total_pull_requests=1,
            total_pull_request_reviews=3,
            restricted_contributions=4,
            last_activity_on=date(2025, 12, 1),
            repositories=(
                RepositoryContribution("example/project", 2, 1, 1, 2),
            ),
            commits_truncated=True,
            graphql_rate_remaining=200,
        )
        with TemporaryDirectory() as directory:
            path = Path(directory) / "maintainer.json"
            save_maintainer_activity(snapshot, path)
            loaded = load_maintainer_activity(path)

        self.assertEqual(loaded, snapshot)

    def test_roster_round_trip(self):
        submission = Submission(
            package="project",
            repository="example/project",
            accepted_at=START,
            issue_number=1,
            issue_url="https://github.com/pyOpenSci/software-submission/issues/1",
            title="Project submission",
            maintainers=("maintainer", "second"),
        )
        with TemporaryDirectory() as directory:
            path = Path(directory) / "roster.json"
            save_maintainer_roster(
                (submission,),
                observation_start=START,
                observation_end=END,
                fetched_at=END,
                path=path,
            )
            loaded = load_maintainer_roster(path)

        self.assertEqual(loaded, ((submission,), START, END, END))


if __name__ == "__main__":
    unittest.main()
