"""Metrics describing issue acknowledgement, triage, and resolution."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from reflections.datasources.github.models import IssueEvent, IssueRecord, IssueSnapshot


@dataclass(frozen=True)
class IssueResponsePolicy:
    """Documented choices for deciding when an issue was addressed."""

    maintainer_associations: frozenset[str] = field(
        default_factory=lambda: frozenset({"OWNER", "MEMBER", "COLLABORATOR"})
    )
    triage_kinds: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {"assigned", "labeled", "milestoned", "closed"}
        )
    )
    exclude_bots: bool = True
    exclude_issue_author: bool = True
    ignore_activity_after_close: bool = True


@dataclass(frozen=True)
class IssueTiming:
    """Acknowledgement and triage results for one issue."""

    number: int
    period: Literal["before_acceptance", "after_acceptance"]
    first_acknowledgement_at: datetime | None
    acknowledgement_days: float | None
    first_triage_at: datetime | None
    triage_days: float | None
    first_addressed_at: datetime | None
    addressed_days: float | None


def calculate_issue_times(
    snapshot: IssueSnapshot,
    *,
    policy: IssueResponsePolicy | None = None,
) -> tuple[IssueTiming, ...]:
    """Calculate first maintainer acknowledgement and first triage action."""

    resolved_policy = policy or IssueResponsePolicy()
    return tuple(
        _calculate_issue_timing(
            issue,
            accepted_at=snapshot.accepted_at,
            policy=resolved_policy,
        )
        for issue in snapshot.issues
    )


def _calculate_issue_timing(
    issue: IssueRecord,
    *,
    accepted_at: datetime,
    policy: IssueResponsePolicy,
) -> IssueTiming:
    acknowledgement = min(
        (
            event.created_at
            for event in issue.events
            if event.kind == "commented"
            and _is_eligible_event(event, issue=issue, policy=policy)
            and (event.actor_association or "").upper()
            in policy.maintainer_associations
        ),
        default=None,
    )
    triage = min(
        (
            event.created_at
            for event in issue.events
            if event.kind in policy.triage_kinds
            and _is_eligible_event(event, issue=issue, policy=policy)
        ),
        default=None,
    )
    addressed = min(
        (value for value in (acknowledgement, triage) if value is not None),
        default=None,
    )
    return IssueTiming(
        number=issue.number,
        period=(
            "after_acceptance"
            if issue.created_at > accepted_at
            else "before_acceptance"
        ),
        first_acknowledgement_at=acknowledgement,
        acknowledgement_days=_elapsed_days(issue.created_at, acknowledgement),
        first_triage_at=triage,
        triage_days=_elapsed_days(issue.created_at, triage),
        first_addressed_at=addressed,
        addressed_days=_elapsed_days(issue.created_at, addressed),
    )


def _is_eligible_event(
    event: IssueEvent,
    *,
    issue: IssueRecord,
    policy: IssueResponsePolicy,
) -> bool:
    if event.created_at < issue.created_at:
        return False
    if (
        policy.ignore_activity_after_close
        and issue.closed_at is not None
        and event.created_at > issue.closed_at
    ):
        return False
    login = event.actor_login
    if policy.exclude_bots and login is not None and login.casefold().endswith("[bot]"):
        return False
    return not (
        policy.exclude_issue_author
        and login is not None
        and issue.author_login is not None
        and login.casefold() == issue.author_login.casefold()
    )


def _elapsed_days(start: datetime, end: datetime | None) -> float | None:
    if end is None:
        return None
    return (end - start).total_seconds() / 86_400
