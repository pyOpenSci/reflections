from datetime import UTC, datetime
from types import SimpleNamespace
import unittest

from reflections.datasources.github.client import (
    APPROVED_LABEL,
    RepositoryLinkNotFoundError,
    _collect_pull_request,
    _repository_from_issue_body,
    get_accepted_submissions,
    get_submission,
)


def timestamp(day: int) -> datetime:
    return datetime(2025, 1, day, tzinfo=UTC)


class FakeRepository:
    def __init__(self, issues):
        self.issues = issues
        self.query = None

    def get_issues(self, **query):
        self.query = query
        return self.issues


class GitHubClientTests(unittest.TestCase):
    def test_get_submission_uses_approved_closed_issues(self):
        issue = SimpleNamespace(
            title="Submission: swiftgalaxy",
            number=211,
            body="Package: https://github.com/SWIFTSIM/swiftgalaxy",
            closed_at=timestamp(4),
            html_url="https://github.com/PyOpenSci/software-submission/issues/211",
        )
        repository = FakeRepository([issue])
        github = SimpleNamespace(get_repo=lambda name: repository)

        submission = get_submission("swiftgalaxy", github=github)

        self.assertEqual(repository.query, {"state": "closed", "labels": [APPROVED_LABEL]})
        self.assertEqual(submission.repository, "SWIFTSIM/swiftgalaxy")
        self.assertEqual(submission.accepted_at, timestamp(4))

    def test_get_accepted_submissions_returns_acceptance_order(self):
        issues = [
            SimpleNamespace(
                title="Submission: newer",
                number=20,
                body="Repository: https://github.com/example/newer",
                closed_at=timestamp(8),
                html_url="https://github.com/PyOpenSci/software-submission/issues/20",
            ),
            SimpleNamespace(
                title="Submission: older",
                number=10,
                body="Repository: https://github.com/example/older",
                closed_at=timestamp(2),
                html_url="https://github.com/PyOpenSci/software-submission/issues/10",
            ),
        ]
        repository = FakeRepository(issues)
        github = SimpleNamespace(get_repo=lambda name: repository)

        submissions = get_accepted_submissions(github=github)

        self.assertEqual(
            [submission.package for submission in submissions],
            ["older", "newer"],
        )
        self.assertEqual(repository.query, {"state": "closed", "labels": [APPROVED_LABEL]})

    def test_repository_parser_ignores_submission_repository(self):
        body = """
        Tracking: https://github.com/PyOpenSci/software-submission/issues/211
        Repository: https://github.com/example/useful-package.git
        """

        repository = _repository_from_issue_body(
            body,
            excluded_repository="PyOpenSci/software-submission",
        )

        self.assertEqual(repository, "example/useful-package")

    def test_repository_parser_requires_a_link(self):
        with self.assertRaises(RepositoryLinkNotFoundError):
            _repository_from_issue_body("No link", excluded_repository="some/repo")

    def test_pull_request_collection_includes_review_without_body(self):
        user = SimpleNamespace(login="maintainer")
        issue_comment = SimpleNamespace(
            created_at=timestamp(3), user=user, author_association="MEMBER"
        )
        review = SimpleNamespace(
            submitted_at=timestamp(2),
            state="APPROVED",
            body="",
            user=user,
            author_association="MEMBER",
        )
        pull_request = SimpleNamespace(
            number=12,
            title="Improve docs",
            html_url="https://github.com/example/project/pull/12",
            user=SimpleNamespace(login="contributor"),
            created_at=timestamp(1),
            closed_at=timestamp(4),
            merged_at=timestamp(4),
            get_issue_comments=lambda: [issue_comment],
            get_review_comments=lambda: [],
            get_reviews=lambda: [review],
        )

        record = _collect_pull_request(pull_request)

        self.assertEqual([event.kind for event in record.responses], ["review", "issue_comment"])


if __name__ == "__main__":
    unittest.main()
