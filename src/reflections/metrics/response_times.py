"""Metrics describing the first maintainer response to pull requests."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from reflections.datasources.github.models import (
    PullRequestRecord,
    RepositorySnapshot,
    ResponseEvent,
)


@dataclass(frozen=True)
class MaintainerResponsePolicy:
    """Documented choices for deciding what constitutes a response."""

    maintainer_associations: frozenset[str] = field(
        default_factory=lambda: frozenset({"OWNER", "MEMBER", "COLLABORATOR"})
    )
    exclude_bots: bool = True
    exclude_pull_request_author: bool = True
    ignore_activity_after_close: bool = True


@dataclass(frozen=True)
class PullRequestResponseTime:
    """First-response result for one pull request."""

    number: int
    title: str
    url: str
    created_at: datetime
    period: Literal["before_acceptance", "after_acceptance"]
    first_response_at: datetime | None
    response_days: float | None


def calculate_first_response_times(
    snapshot: RepositorySnapshot,
    *,
    policy: MaintainerResponsePolicy | None = None,
) -> tuple[PullRequestResponseTime, ...]:
    """Calculate first maintainer-response time for every pull request.

    A response can be a conversation comment, inline review comment, or
    submitted review (including a review without a written body). By default,
    bot activity, the pull-request author's activity, and events after closure
    are excluded.
    """

    resolved_policy = policy or MaintainerResponsePolicy()
    return tuple(
        _calculate_pull_request_response(
            pull_request,
            accepted_at=snapshot.accepted_at,
            policy=resolved_policy,
        )
        for pull_request in snapshot.pull_requests
    )


def _calculate_pull_request_response(
    pull_request: PullRequestRecord,
    *,
    accepted_at: datetime,
    policy: MaintainerResponsePolicy,
) -> PullRequestResponseTime:
    eligible_responses = [
        response
        for response in pull_request.responses
        if _is_eligible_response(response, pull_request=pull_request, policy=policy)
    ]
    first_response_at = min(
        (response.created_at for response in eligible_responses),
        default=None,
    )
    response_days = (
        None
        if first_response_at is None
        else (first_response_at - pull_request.created_at).total_seconds() / 86_400
    )
    period: Literal["before_acceptance", "after_acceptance"] = (
        "after_acceptance"
        if pull_request.created_at > accepted_at
        else "before_acceptance"
    )
    return PullRequestResponseTime(
        number=pull_request.number,
        title=pull_request.title,
        url=pull_request.url,
        created_at=pull_request.created_at,
        period=period,
        first_response_at=first_response_at,
        response_days=response_days,
    )


def _is_eligible_response(
    response: ResponseEvent,
    *,
    pull_request: PullRequestRecord,
    policy: MaintainerResponsePolicy,
) -> bool:
    association = (response.author_association or "").upper()
    if association not in policy.maintainer_associations:
        return False
    if response.created_at < pull_request.created_at:
        return False
    if (
        policy.ignore_activity_after_close
        and pull_request.closed_at is not None
        and response.created_at > pull_request.closed_at
    ):
        return False

    login = response.author_login
    if policy.exclude_bots and login is not None and login.casefold().endswith("[bot]"):
        return False
    return not (
        policy.exclude_pull_request_author
        and login is not None
        and pull_request.author_login is not None
        and login.casefold() == pull_request.author_login.casefold()
    )
