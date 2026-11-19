from datetime import UTC, datetime
import unittest

from reflections.datasources.github.models import (
    PullRequestRecord,
    RepositorySnapshot,
    ResponseEvent,
)
from reflections.metrics import MaintainerResponsePolicy, calculate_first_response_times


def timestamp(day: int, hour: int = 0) -> datetime:
    return datetime(2025, 1, day, hour, tzinfo=UTC)


def response(
    day: int,
    *,
    login: str = "maintainer",
    association: str = "MEMBER",
) -> ResponseEvent:
    return ResponseEvent(
        kind="issue_comment",
        created_at=timestamp(day),
        author_login=login,
        author_association=association,
    )


class ResponseTimeTests(unittest.TestCase):
    def test_uses_earliest_eligible_maintainer_activity(self):
        pull_request = PullRequestRecord(
            number=1,
            title="Feature",
            url="https://github.com/example/project/pull/1",
            author_login="contributor",
            created_at=timestamp(1),
            closed_at=timestamp(8),
            merged_at=None,
            responses=(
                response(2, association="CONTRIBUTOR"),
                response(4),
                response(3, association="OWNER"),
            ),
        )
        snapshot = self._snapshot(pull_request)

        result = calculate_first_response_times(snapshot)[0]

        self.assertEqual(result.first_response_at, timestamp(3))
        self.assertEqual(result.response_days, 2.0)
        self.assertEqual(result.period, "before_acceptance")

    def test_excludes_bots_author_and_activity_after_close(self):
        pull_request = PullRequestRecord(
            number=2,
            title="Fix",
            url="https://github.com/example/project/pull/2",
            author_login="owner",
            created_at=timestamp(6),
            closed_at=timestamp(8),
            merged_at=None,
            responses=(
                response(7, login="dependabot[bot]", association="COLLABORATOR"),
                response(7, login="owner", association="OWNER"),
                response(9),
            ),
        )

        result = calculate_first_response_times(self._snapshot(pull_request))[0]

        self.assertIsNone(result.first_response_at)
        self.assertIsNone(result.response_days)
        self.assertEqual(result.period, "after_acceptance")

    def test_policy_can_include_pull_request_author(self):
        pull_request = PullRequestRecord(
            number=3,
            title="Maintainer PR",
            url="https://github.com/example/project/pull/3",
            author_login="owner",
            created_at=timestamp(1),
            closed_at=None,
            merged_at=None,
            responses=(response(2, login="owner", association="OWNER"),),
        )
        policy = MaintainerResponsePolicy(exclude_pull_request_author=False)

        result = calculate_first_response_times(
            self._snapshot(pull_request), policy=policy
        )[0]

        self.assertEqual(result.response_days, 1.0)

    @staticmethod
    def _snapshot(pull_request: PullRequestRecord) -> RepositorySnapshot:
        return RepositorySnapshot(
            repository="example/project",
            accepted_at=timestamp(5),
            fetched_at=timestamp(10),
            pull_requests=(pull_request,),
        )


if __name__ == "__main__":
    unittest.main()
