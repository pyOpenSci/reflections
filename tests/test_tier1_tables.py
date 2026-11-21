import csv
from datetime import UTC, datetime

import pandas as pd
import pytest

from reflections.analysis import (
    tier1_issue_rows,
    tier1_pull_request_rows,
    write_tier1_issue_csv,
)
from reflections.analysis.plotting import monthly_repository_counts
from reflections.datasources.github.models import (
    HistoryIndexRecord,
    HistoryIndexSnapshot,
)


def timestamp(month, day):
    return datetime(2025, month, day, tzinfo=UTC)


def record(number, created_at, *, closed_at=None, merged_at=None):
    return HistoryIndexRecord(
        number=number,
        title=f"Item {number}",
        url=f"https://github.com/org/project/issues/{number}",
        author_login="person",
        created_at=created_at,
        updated_at=closed_at or created_at,
        closed_at=closed_at,
        merged_at=merged_at,
        state="closed" if closed_at else "open",
        comment_count=number,
        review_comment_count=None,
        is_draft=False,
    )


def snapshot(entity_type, records, *, fetched_at=None):
    return HistoryIndexSnapshot(
        repository="org/project",
        entity_type=entity_type,
        fetched_at=fetched_at or timestamp(4, 20),
        records=tuple(records),
        complete=True,
    )


def test_tier1_issue_rows_retain_history_and_mark_window_and_followup():
    history = snapshot(
        "issues",
        [
            record(1, timestamp(1, 1), closed_at=timestamp(1, 5)),
            record(2, timestamp(1, 20)),
            record(3, datetime(2024, 9, 1, tzinfo=UTC)),
        ],
    )

    rows = list(
        tier1_issue_rows(
            [history],
            accepted_at={"org/project": timestamp(1, 10)},
            packages={"org/project": "package-name"},
            window_days=90,
        )
    )

    assert len(rows) == 3
    assert rows[0]["package"] == "package-name"
    assert rows[0]["period"] == "before_acceptance"
    assert rows[1]["period"] == "after_acceptance"
    assert rows[0]["time_to_close_days"] == 4
    assert rows[1]["resolution_censored"]
    assert rows[0]["eligible_followup"]
    assert [row["within_window"] for row in rows] == [True, True, False]


def test_tier1_pr_rows_include_merge_outcome():
    history = snapshot(
        "pull_requests",
        [
            record(
                1,
                timestamp(1, 1),
                closed_at=timestamp(1, 5),
                merged_at=timestamp(1, 4),
            )
        ],
    )

    row = next(
        tier1_pull_request_rows(
            [history],
            accepted_at={"org/project": timestamp(1, 10)},
            window_days=90,
        )
    )

    assert row["outcome"] == "merged"
    assert row["is_merged"]
    assert row["time_to_merge_days"] == 3


def test_tier1_rows_mark_insufficient_followup():
    history = snapshot("issues", [record(1, timestamp(1, 20))], fetched_at=timestamp(2, 1))

    row = next(
        tier1_issue_rows(
            [history],
            accepted_at={"org/project": timestamp(1, 10)},
            window_days=90,
        )
    )

    assert not row["eligible_followup"]


def test_tier1_rows_reject_wrong_entity_type():
    history = snapshot("pull_requests", [])

    with pytest.raises(ValueError, match="Expected issues"):
        list(
            tier1_issue_rows(
                [history],
                accepted_at={"org/project": timestamp(1, 10)},
            )
        )


def test_tier1_issue_csv_is_sorted(tmp_path):
    history = snapshot(
        "issues",
        [record(2, timestamp(1, 20)), record(1, timestamp(1, 1))],
    )
    path = write_tier1_issue_csv(
        [history],
        tmp_path / "issues.csv",
        accepted_at={"org/project": timestamp(1, 10)},
    )

    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))

    assert [row["number"] for row in rows] == ["1", "2"]


def test_monthly_counts_include_repositories_without_events():
    events = pd.DataFrame(
        {"repository": ["org/active"], "days_from_acceptance": [0.0]}
    )

    counts = monthly_repository_counts(
        events,
        repositories=["org/active", "org/quiet"],
        window_days=90,
    )

    quiet = counts.loc[counts["repository"] == "org/quiet"]
    assert len(quiet) == 5
    assert quiet["events"].sum() == 0
