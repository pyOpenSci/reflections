"""Collect normalized pyOpenSci submission and repository data from GitHub."""

from datetime import UTC, datetime
import os
import re
from typing import Any
import warnings

from github import Auth, Github

from .models import PullRequestRecord, RepositorySnapshot, ResponseEvent, Submission

SUBMISSIONS_REPOSITORY = "PyOpenSci/software-submission"
APPROVED_LABEL = "6/pyOS-approved"

_GITHUB_REPOSITORY_URL = re.compile(
    r"https?://(?:www\.)?github\.com/([^/\s)>\]]+)/([^/\s#?)>\]]+)",
    flags=re.IGNORECASE,
)
_REPOSITORY_FIELD_URL = re.compile(
    r"^\s*Repository\s+Link:\s*(https?://[^\s)>]+)",
    flags=re.IGNORECASE | re.MULTILINE,
)


class SubmissionNotFoundError(LookupError):
    """Raised when an accepted submission cannot be found unambiguously."""


class RepositoryLinkNotFoundError(ValueError):
    """Raised when a submission does not contain a usable repository URL."""


class UnsupportedRepositoryHostError(ValueError):
    """Raised when a submission repository is not hosted on GitHub."""


class UnsupportedRepositoryWarning(UserWarning):
    """Warn that a submission cannot be collected by the GitHub data source."""


def create_github(token: str | None = None) -> Github:
    """Create a PyGithub client.

    ``GITHUB_TOKEN`` is preferred. ``github_pat`` is supported temporarily for
    compatibility with the original exploration notebook. Public GitHub data
    can also be queried anonymously, subject to a much lower rate limit.
    """

    resolved_token = token or os.getenv("GITHUB_TOKEN") or os.getenv("github_pat")
    if resolved_token:
        return Github(auth=Auth.Token(resolved_token))
    return Github()


def get_submission(
    package: str,
    *,
    github: Github | None = None,
    submissions_repository: str = SUBMISSIONS_REPOSITORY,
) -> Submission:
    """Return the uniquely matching approved pyOpenSci submission."""

    if not package.strip():
        raise ValueError("package must not be empty")

    client = github or create_github()
    approved_issues = _get_approved_issues(client, submissions_repository)
    matches = [
        issue
        for issue in approved_issues
        if _normalize_name(package) in _normalize_name(issue.title)
    ]

    if len(matches) != 1:
        issue_numbers = [issue.number for issue in matches]
        raise SubmissionNotFoundError(
            f"Expected one approved submission matching {package!r}; "
            f"found {len(matches)} (issues: {issue_numbers})"
        )

    return _submission_from_issue(
        matches[0],
        package=package,
        submissions_repository=submissions_repository,
    )


def get_accepted_submissions(
    *,
    github: Github | None = None,
    submissions_repository: str = SUBMISSIONS_REPOSITORY,
    on_unsupported: str = "raise",
) -> tuple[Submission, ...]:
    """Return approved GitHub-hosted submissions in acceptance order.

    Set ``on_unsupported="warn"`` for batch collection to report and skip
    submissions hosted elsewhere. The default remains strict so callers do
    not unknowingly analyze an incomplete cohort.
    """

    if on_unsupported not in {"raise", "warn"}:
        raise ValueError("on_unsupported must be 'raise' or 'warn'")

    client = github or create_github()
    submissions = []
    for issue in _get_approved_issues(client, submissions_repository):
        try:
            submission = _submission_from_issue(
                issue,
                submissions_repository=submissions_repository,
            )
        except (RepositoryLinkNotFoundError, UnsupportedRepositoryHostError) as error:
            if on_unsupported == "raise":
                raise
            warnings.warn(
                f"Skipping approved issue #{issue.number} ({issue.title}): {error}",
                UnsupportedRepositoryWarning,
                stacklevel=2,
            )
            continue
        submissions.append(submission)
    return tuple(
        sorted(
            submissions,
            key=lambda submission: (submission.accepted_at, submission.issue_number),
        )
    )


def collect_repository_snapshot(
    repository: str,
    *,
    accepted_at: datetime,
    github: Github | None = None,
) -> RepositorySnapshot:
    """Collect pull requests and their response events for a repository."""

    client = github or create_github()
    github_repository = client.get_repo(repository)
    pull_requests = tuple(
        _collect_pull_request(pull_request)
        for pull_request in github_repository.get_pulls(
            state="all",
            sort="created",
            direction="asc",
        )
    )
    return RepositorySnapshot(
        repository=repository,
        accepted_at=accepted_at,
        fetched_at=datetime.now(UTC),
        pull_requests=pull_requests,
    )


def _collect_pull_request(pull_request: Any) -> PullRequestRecord:
    responses = [
        *(
            _response_event(comment, "issue_comment")
            for comment in pull_request.get_issue_comments()
        ),
        *(
            _response_event(comment, "review_comment")
            for comment in pull_request.get_review_comments()
        ),
        *(
            _response_event(review, "review", created_at=review.submitted_at)
            for review in pull_request.get_reviews()
            if review.submitted_at is not None and review.state != "PENDING"
        ),
    ]
    responses.sort(key=lambda response: response.created_at)

    return PullRequestRecord(
        number=pull_request.number,
        title=pull_request.title,
        url=pull_request.html_url,
        author_login=_login(pull_request.user),
        created_at=pull_request.created_at,
        closed_at=pull_request.closed_at,
        merged_at=pull_request.merged_at,
        responses=tuple(responses),
    )


def _response_event(
    event: Any,
    kind: str,
    *,
    created_at: datetime | None = None,
) -> ResponseEvent:
    return ResponseEvent(
        kind=kind,
        created_at=created_at or event.created_at,
        author_login=_login(event.user),
        author_association=event.author_association,
    )


def _login(user: Any | None) -> str | None:
    return None if user is None else user.login


def _normalize_name(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def _get_approved_issues(client: Github, submissions_repository: str) -> Any:
    repository = client.get_repo(submissions_repository)
    return repository.get_issues(
        state="closed",
        labels=[APPROVED_LABEL],
    )


def _submission_from_issue(
    issue: Any,
    *,
    submissions_repository: str,
    package: str | None = None,
) -> Submission:
    if issue.closed_at is None:
        raise ValueError(f"Approved issue #{issue.number} has no closure time")

    repository_name = _repository_from_issue_body(
        issue.body or "",
        excluded_repository=submissions_repository,
    )
    return Submission(
        package=package or repository_name.rsplit("/", 1)[-1],
        repository=repository_name,
        accepted_at=issue.closed_at,
        issue_number=issue.number,
        issue_url=issue.html_url,
        title=issue.title,
    )


def _repository_from_issue_body(body: str, *, excluded_repository: str) -> str:
    candidates = _repository_links(body)
    eligible = [
        candidate
        for candidate in candidates
        if candidate.casefold() != excluded_repository.casefold()
    ]
    if not eligible:
        repository_field = _REPOSITORY_FIELD_URL.search(body)
        if repository_field:
            raise UnsupportedRepositoryHostError(
                "repository is not hosted on GitHub: "
                f"{repository_field.group(1).rstrip('.,;')}"
            )
        raise RepositoryLinkNotFoundError(
            "The approved submission issue does not contain a GitHub repository URL"
        )
    return eligible[0]


def _repository_links(body: str) -> list[str]:
    links: list[str] = []
    for owner, raw_repository in _GITHUB_REPOSITORY_URL.findall(body):
        repository = raw_repository.rstrip(".,;:'\"")
        if repository.endswith(".git"):
            repository = repository[:-4]
        name = f"{owner}/{repository}"
        if name not in links:
            links.append(name)
    return links
