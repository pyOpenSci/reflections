"""Collect recent public contribution activity for package maintainers."""

from datetime import UTC, date, datetime
from typing import Any

from github import Github

from .client import create_github
from .models import MaintainerActivitySnapshot, RepositoryContribution

MAX_REPOSITORIES = 100

_QUERY = """
query MaintainerActivity($login: String!, $from: DateTime!, $to: DateTime!) {
  rateLimit { remaining }
  user(login: $login) {
    login
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      totalRepositoriesWithContributedCommits
      totalRepositoriesWithContributedIssues
      totalRepositoriesWithContributedPullRequests
      totalRepositoriesWithContributedPullRequestReviews
      restrictedContributionsCount
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
      commitContributionsByRepository(maxRepositories: 100) {
        repository { nameWithOwner }
        contributions { totalCount }
      }
      issueContributionsByRepository(maxRepositories: 100) {
        repository { nameWithOwner }
        contributions { totalCount }
      }
      pullRequestContributionsByRepository(maxRepositories: 100) {
        repository { nameWithOwner }
        contributions { totalCount }
      }
      pullRequestReviewContributionsByRepository(maxRepositories: 100) {
        repository { nameWithOwner }
        contributions { totalCount }
      }
    }
  }
}
"""


def collect_maintainer_activity(
    login: str,
    *,
    observation_start: datetime,
    observation_end: datetime,
    github: Github | None = None,
) -> MaintainerActivitySnapshot:
    """Collect one maintainer's public contributions over a fixed window."""

    if not login.strip():
        raise ValueError("login must not be empty")
    if observation_start >= observation_end:
        raise ValueError("observation_start must be before observation_end")

    client = github or create_github()
    requester = getattr(client, "_Github__requester")
    _, response = requester.requestJsonAndCheck(
        "POST",
        "/graphql",
        input={
            "query": _QUERY,
            "variables": {
                "login": login,
                "from": observation_start.isoformat(),
                "to": observation_end.isoformat(),
            },
        },
    )
    if response.get("errors"):
        messages = "; ".join(
            str(error.get("message", error)) for error in response["errors"]
        )
        raise ValueError(f"GitHub GraphQL error for @{login}: {messages}")

    user = response.get("data", {}).get("user")
    if user is None:
        return _missing_user_snapshot(
            login,
            observation_start=observation_start,
            observation_end=observation_end,
            graphql_rate_remaining=response["data"]["rateLimit"]["remaining"],
        )
    contributions = user["contributionsCollection"]
    repository_maps = {
        "commits": _repository_counts(
            contributions["commitContributionsByRepository"]
        ),
        "issues": _repository_counts(
            contributions["issueContributionsByRepository"]
        ),
        "pull_requests": _repository_counts(
            contributions["pullRequestContributionsByRepository"]
        ),
        "pull_request_reviews": _repository_counts(
            contributions["pullRequestReviewContributionsByRepository"]
        ),
    }
    repository_names = set().union(*repository_maps.values())
    return MaintainerActivitySnapshot(
        requested_login=login,
        canonical_login=user["login"],
        user_exists=True,
        fetched_at=datetime.now(UTC),
        observation_start=observation_start,
        observation_end=observation_end,
        total_commits=contributions["totalCommitContributions"],
        total_issues=contributions["totalIssueContributions"],
        total_pull_requests=contributions["totalPullRequestContributions"],
        total_pull_request_reviews=contributions[
            "totalPullRequestReviewContributions"
        ],
        restricted_contributions=contributions["restrictedContributionsCount"],
        last_activity_on=_last_activity_date(contributions["contributionCalendar"]),
        repositories=tuple(
            RepositoryContribution(
                repository=repository,
                commits=repository_maps["commits"].get(repository),
                issues=repository_maps["issues"].get(repository),
                pull_requests=repository_maps["pull_requests"].get(repository),
                pull_request_reviews=repository_maps["pull_request_reviews"].get(
                    repository
                ),
            )
            for repository in sorted(repository_names, key=str.casefold)
        ),
        commits_truncated=_is_truncated(
            contributions["totalRepositoriesWithContributedCommits"],
            repository_maps["commits"],
        ),
        issues_truncated=_is_truncated(
            contributions["totalRepositoriesWithContributedIssues"],
            repository_maps["issues"],
        ),
        pull_requests_truncated=_is_truncated(
            contributions["totalRepositoriesWithContributedPullRequests"],
            repository_maps["pull_requests"],
        ),
        pull_request_reviews_truncated=_is_truncated(
            contributions[
                "totalRepositoriesWithContributedPullRequestReviews"
            ],
            repository_maps["pull_request_reviews"],
        ),
        graphql_rate_remaining=response["data"]["rateLimit"]["remaining"],
    )


def _repository_counts(groups: list[dict[str, Any]]) -> dict[str, int]:
    return {
        group["repository"]["nameWithOwner"]: group["contributions"]["totalCount"]
        for group in groups
    }


def _is_truncated(total_repositories: int, observed: dict[str, int]) -> bool:
    return total_repositories > len(observed)


def _last_activity_date(calendar: dict[str, Any]) -> date | None:
    active_dates = [
        date.fromisoformat(day["date"])
        for week in calendar["weeks"]
        for day in week["contributionDays"]
        if day["contributionCount"] > 0
    ]
    return max(active_dates, default=None)


def _missing_user_snapshot(
    login: str,
    *,
    observation_start: datetime,
    observation_end: datetime,
    graphql_rate_remaining: int,
) -> MaintainerActivitySnapshot:
    return MaintainerActivitySnapshot(
        requested_login=login,
        canonical_login=None,
        user_exists=False,
        fetched_at=datetime.now(UTC),
        observation_start=observation_start,
        observation_end=observation_end,
        total_commits=0,
        total_issues=0,
        total_pull_requests=0,
        total_pull_request_reviews=0,
        restricted_contributions=0,
        last_activity_on=None,
        graphql_rate_remaining=graphql_rate_remaining,
    )
