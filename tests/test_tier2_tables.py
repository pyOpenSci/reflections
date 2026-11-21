from datetime import UTC, datetime

import pytest

from reflections.analysis.tier2_tables import (
    comment_response_rows,
    cumulative_response_curve,
)
from reflections.datasources.github.models import (
    HistoryIndexRecord,
    HistoryIndexSnapshot,
    InteractionRecord,
    InteractionSnapshot,
)


def timestamp(day):
    return datetime(2025, 1, day, tzinfo=UTC)


def item(number=1, *, author="author", closed_at=None):
    return HistoryIndexRecord(
        number=number,
        title=f"Item {number}",
        url=f"https://github.com/org/project/issues/{number}",
        author_login=author,
        created_at=timestamp(2),
        updated_at=closed_at or timestamp(2),
        closed_at=closed_at,
        merged_at=None,
        state="closed" if closed_at else "open",
        comment_count=0,
        review_comment_count=0,
        is_draft=False,
    )


def index(entity_type="issues", *, records=None, complete=True):
    return HistoryIndexSnapshot(
        repository="org/project",
        entity_type=entity_type,
        fetched_at=timestamp(20),
        records=tuple(records or [item()]),
        complete=complete,
    )


def comment(
    identifier,
    day,
    *,
    parent=1,
    login="maintainer",
    association="MEMBER",
    kind="issue_comment",
):
    return InteractionRecord(
        id=identifier,
        parent_number=parent,
        kind=kind,
        url=f"https://github.com/org/project/issues/{parent}#comment-{identifier}",
        author_login=login,
        author_association=association,
        created_at=timestamp(day),
        updated_at=timestamp(day),
    )


def interactions(interaction_type="issue_comments", *, records=(), complete=True):
    return InteractionSnapshot(
        repository="org/project",
        interaction_type=interaction_type,
        fetched_at=timestamp(18),
        records=tuple(records),
        complete=complete,
    )


def test_issue_response_filters_outsiders_bots_author_and_comments_after_close():
    issue = item(closed_at=timestamp(10))
    stream = interactions(
        records=(
            comment(1, 3, association="NONE"),
            comment(2, 4, login="dependabot[bot]"),
            comment(3, 5, login="author"),
            comment(4, 7, association="OWNER"),
            comment(5, 11, association="OWNER"),
        )
    )

    row = next(
        comment_response_rows(
            index(records=[issue]),
            stream,
            accepted_at=timestamp(1),
        )
    )

    assert row["has_maintainer_comment"]
    assert row["comment_response_days"] == 5
    assert row["first_comment_author_association"] == "OWNER"
    assert row["qualifying_maintainer_comments"] == 1


def test_pull_request_response_uses_conversation_and_inline_comments():
    issue_stream = interactions(records=(comment(1, 8),))
    review_stream = interactions(
        "review_comments",
        records=(comment(2, 5, kind="review_comment", association="COLLABORATOR"),),
    )

    row = next(
        comment_response_rows(
            index("pull_requests"),
            issue_stream,
            review_comments=review_stream,
            accepted_at=timestamp(1),
        )
    )

    assert row["first_comment_kind"] == "review_comment"
    assert row["comment_response_days"] == 3
    assert row["qualifying_maintainer_comments"] == 2


def test_no_response_is_censored_at_close_or_common_snapshot_cutoff():
    rows = list(
        comment_response_rows(
            index(records=[item(1, closed_at=timestamp(7)), item(2)]),
            interactions(),
            accepted_at=timestamp(1),
        )
    )

    assert rows[0]["comment_response_censored"]
    assert rows[0]["comment_response_observation_days"] == 5
    assert rows[1]["comment_response_observation_days"] == 16
    assert rows[0]["observation_cutoff"] == timestamp(18).isoformat()


def test_pull_request_analysis_requires_complete_review_comments():
    with pytest.raises(ValueError, match="requires review comments"):
        list(
            comment_response_rows(
                index("pull_requests"),
                interactions(),
                accepted_at=timestamp(1),
            )
        )
    with pytest.raises(ValueError, match="incomplete"):
        list(
            comment_response_rows(
                index("pull_requests"),
                interactions(),
                review_comments=interactions("review_comments", complete=False),
                accepted_at=timestamp(1),
            )
        )


def test_cumulative_response_curve_accounts_for_censoring():
    curve = cumulative_response_curve(
        [1, 2, 4],
        [True, False, True],
        horizon_days=4,
    )

    assert curve[1].cumulative_response == pytest.approx(1 / 3)
    assert curve[3].at_risk == 1
    assert curve[4].cumulative_response == pytest.approx(1.0)
