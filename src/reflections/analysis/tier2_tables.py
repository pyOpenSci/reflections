"""Build comment-response tables from Tier 1 indexes and Tier 2 streams."""

import csv
from collections import defaultdict
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from reflections.datasources.github.models import (
    HistoryIndexSnapshot,
    InteractionRecord,
    InteractionSnapshot,
)

MAINTAINER_ASSOCIATIONS = frozenset({"OWNER", "MEMBER", "COLLABORATOR"})

TIER2_RESPONSE_COLUMNS = (
    "repository",
    "package",
    "entity_type",
    "number",
    "title",
    "url",
    "author_login",
    "created_at",
    "closed_at",
    "accepted_at",
    "observation_cutoff",
    "analysis_window_days",
    "post_acceptance_observation_days",
    "eligible_followup",
    "period",
    "days_from_acceptance",
    "within_window",
    "first_maintainer_comment_at",
    "comment_response_days",
    "comment_response_observation_days",
    "comment_response_censored",
    "has_maintainer_comment",
    "first_comment_kind",
    "first_comment_author_login",
    "first_comment_author_association",
    "qualifying_maintainer_comments",
)


@dataclass(frozen=True)
class CommentResponsePolicy:
    """Choices defining a qualifying maintainer comment."""

    maintainer_associations: frozenset[str] = MAINTAINER_ASSOCIATIONS
    exclude_bots: bool = True
    exclude_item_author: bool = True
    ignore_comments_after_close: bool = True


@dataclass(frozen=True)
class CumulativeResponsePoint:
    """One point on a censoring-aware cumulative-response curve."""

    day: int
    cumulative_response: float
    at_risk: int


def comment_response_rows(
    index: HistoryIndexSnapshot,
    issue_comments: InteractionSnapshot,
    *,
    accepted_at: datetime,
    package: str | None = None,
    review_comments: InteractionSnapshot | None = None,
    window_days: int = 90,
    policy: CommentResponsePolicy | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield one response-analysis row per indexed issue or pull request.

    Issue analysis requires the complete repository issue-comment stream. Pull
    request analysis additionally requires the complete inline review-comment
    stream. Formal submitted reviews are intentionally outside this metric.
    """

    if window_days <= 0:
        raise ValueError("window_days must be positive")
    _validate_snapshot(index, issue_comments, review_comments)
    resolved_policy = policy or CommentResponsePolicy()
    streams = [issue_comments]
    if review_comments is not None:
        streams.append(review_comments)
    cutoff = min(index.fetched_at, *(stream.fetched_at for stream in streams))
    followup_days = _elapsed_days(accepted_at, cutoff)
    comments_by_parent: dict[int, list[InteractionRecord]] = defaultdict(list)
    for stream in streams:
        for comment in stream.records:
            comments_by_parent[comment.parent_number].append(comment)

    entity_type: Literal["issue", "pull_request"] = (
        "issue" if index.entity_type == "issues" else "pull_request"
    )
    for item in index.records:
        qualifying = sorted(
            (
                comment
                for comment in comments_by_parent[item.number]
                if _is_qualifying_comment(
                    comment,
                    item=item,
                    cutoff=cutoff,
                    policy=resolved_policy,
                )
            ),
            key=lambda comment: (comment.created_at, comment.id),
        )
        first = qualifying[0] if qualifying else None
        observation_end = first.created_at if first else _observation_end(item, cutoff)
        days_from_acceptance = _elapsed_days(accepted_at, item.created_at)
        yield {
            "repository": index.repository,
            "package": package or index.repository.rsplit("/", 1)[-1],
            "entity_type": entity_type,
            "number": item.number,
            "title": item.title,
            "url": item.url,
            "author_login": item.author_login or "",
            "created_at": item.created_at.isoformat(),
            "closed_at": _optional_datetime(item.closed_at),
            "accepted_at": accepted_at.isoformat(),
            "observation_cutoff": cutoff.isoformat(),
            "analysis_window_days": window_days,
            "post_acceptance_observation_days": followup_days,
            "eligible_followup": followup_days >= window_days,
            "period": (
                "after_acceptance"
                if item.created_at > accepted_at
                else "before_acceptance"
            ),
            "days_from_acceptance": days_from_acceptance,
            "within_window": abs(days_from_acceptance) <= window_days,
            "first_maintainer_comment_at": (
                "" if first is None else first.created_at.isoformat()
            ),
            "comment_response_days": (
                None
                if first is None
                else _elapsed_days(item.created_at, first.created_at)
            ),
            "comment_response_observation_days": _elapsed_days(
                item.created_at,
                observation_end,
            ),
            "comment_response_censored": first is None,
            "has_maintainer_comment": first is not None,
            "first_comment_kind": "" if first is None else first.kind,
            "first_comment_author_login": (
                "" if first is None else first.author_login or ""
            ),
            "first_comment_author_association": (
                "" if first is None else first.author_association or ""
            ),
            "qualifying_maintainer_comments": len(qualifying),
        }


def write_comment_response_csv(
    rows: Iterable[Mapping[str, Any]],
    path: str | Path,
) -> Path:
    """Write deterministic Tier 2 response rows."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(
        rows,
        key=lambda row: (str(row["repository"]).casefold(), int(row["number"])),
    )
    with destination.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=TIER2_RESPONSE_COLUMNS)
        writer.writeheader()
        writer.writerows(ordered)
    return destination


def cumulative_response_curve(
    durations: Sequence[float],
    responded: Sequence[bool],
    *,
    horizon_days: int = 30,
) -> tuple[CumulativeResponsePoint, ...]:
    """Estimate cumulative response with the Kaplan-Meier complement."""

    if horizon_days <= 0:
        raise ValueError("horizon_days must be positive")
    if len(durations) != len(responded):
        raise ValueError("durations and responded must have equal lengths")
    observations = sorted(
        (max(0.0, float(duration)), bool(event))
        for duration, event in zip(durations, responded, strict=True)
    )
    event_times = sorted({duration for duration, event in observations if event})
    survival = 1.0
    event_index = 0
    points = []
    for day in range(horizon_days + 1):
        while event_index < len(event_times) and event_times[event_index] <= day:
            event_time = event_times[event_index]
            at_risk = sum(duration >= event_time for duration, _ in observations)
            events = sum(
                event and duration == event_time for duration, event in observations
            )
            if at_risk:
                survival *= 1 - events / at_risk
            event_index += 1
        points.append(
            CumulativeResponsePoint(
                day=day,
                cumulative_response=1 - survival,
                at_risk=sum(duration >= day for duration, _ in observations),
            )
        )
    return tuple(points)


def _validate_snapshot(index, issue_comments, review_comments):
    if index.entity_type not in {"issues", "pull_requests"}:
        raise ValueError(f"Unsupported Tier 1 entity type: {index.entity_type}")
    if not index.complete:
        raise ValueError(f"Tier 1 snapshot is incomplete for {index.repository}")
    required = [(issue_comments, "issue_comments")]
    if index.entity_type == "pull_requests":
        if review_comments is None:
            raise ValueError("Pull-request response analysis requires review comments")
        required.append((review_comments, "review_comments"))
    elif review_comments is not None:
        raise ValueError("Issue response analysis does not use review comments")
    for snapshot, expected_type in required:
        if snapshot.repository.casefold() != index.repository.casefold():
            raise ValueError("Interaction and Tier 1 repositories do not match")
        if snapshot.interaction_type != expected_type:
            raise ValueError(f"Expected {expected_type} interaction snapshot")
        if not snapshot.complete:
            raise ValueError(
                f"{expected_type} snapshot is incomplete for {index.repository}"
            )


def _is_qualifying_comment(comment, *, item, cutoff, policy):
    association = (comment.author_association or "").upper()
    if association not in policy.maintainer_associations:
        return False
    if comment.created_at < item.created_at or comment.created_at > cutoff:
        return False
    if (
        policy.ignore_comments_after_close
        and item.closed_at is not None
        and comment.created_at > item.closed_at
    ):
        return False
    login = comment.author_login
    if policy.exclude_bots and login is not None and login.casefold().endswith("[bot]"):
        return False
    return not (
        policy.exclude_item_author
        and login is not None
        and item.author_login is not None
        and login.casefold() == item.author_login.casefold()
    )


def _observation_end(item, cutoff):
    return min(item.closed_at, cutoff) if item.closed_at is not None else cutoff


def _optional_datetime(value: datetime | None) -> str:
    return "" if value is None else value.isoformat()


def _elapsed_days(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / 86_400
