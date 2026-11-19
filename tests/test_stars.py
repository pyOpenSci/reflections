from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from reflections.datasources.github import (
    StarHistoryWeek,
    StarSnapshot,
    collect_star_snapshot,
    load_star_snapshot,
    save_star_snapshot,
)


ACCEPTED_AT = datetime(2025, 1, 10, tzinfo=UTC)


def week(epoch: int, value: int = 1):
    return {"week": epoch, "total": value, "days": [value, 0, 0, 0, 0, 0, 0]}


class FakeRequester:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def requestJsonAndCheck(self, method, url, *, parameters):
        page = parameters["page"]
        self.calls.append((method, url, parameters))
        data = self.pages[page]
        last_page = max(self.pages)
        headers = {
            "link": (
                f'<https://api.github.com/example?page={last_page}>; rel="last"'
                if last_page > 1
                else ""
            )
        }
        return headers, data


class StarCollectionTests(unittest.TestCase):
    def test_collects_paginated_aggregate_history(self):
        requester = FakeRequester(
            {
                1: [week(1_735_689_600 + offset * 604_800) for offset in range(30)],
                2: [week(1_753_833_600)],
            }
        )
        repository = SimpleNamespace(
            url="https://api.github.com/repos/example/project",
            stargazers_count=42,
            _requester=requester,
        )
        github = SimpleNamespace(get_repo=lambda name: repository)
        progress = []

        snapshot = collect_star_snapshot(
            "example/project",
            accepted_at=ACCEPTED_AT,
            github=github,
            on_progress=lambda snapshot, page, total, complete: progress.append(
                (page, total, complete)
            ),
        )

        self.assertTrue(snapshot.complete)
        self.assertEqual(snapshot.current_stargazers, 42)
        self.assertEqual(len(snapshot.weeks), 31)
        self.assertEqual(snapshot.pages_collected, 2)
        self.assertEqual(progress, [(1, 2, False), (2, 2, True)])

    def test_resumes_from_the_next_page(self):
        start = 1_735_689_600
        cached_weeks = tuple(
            StarHistoryWeek(
                week_started_at=datetime.fromtimestamp(start + offset * 604_800, UTC),
                total=1,
                days=(1, 0, 0, 0, 0, 0, 0),
            )
            for offset in range(30)
        )
        checkpoint = StarSnapshot(
            repository="example/project",
            accepted_at=ACCEPTED_AT,
            fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
            current_stargazers=40,
            weeks=cached_weeks,
            pages_collected=1,
            total_pages=2,
            complete=False,
        )
        requester = FakeRequester({2: [week(1_753_833_600)]})
        repository = SimpleNamespace(
            url="https://api.github.com/repos/example/project",
            stargazers_count=42,
            _requester=requester,
        )
        github = SimpleNamespace(get_repo=lambda name: repository)

        snapshot = collect_star_snapshot(
            "example/project",
            accepted_at=ACCEPTED_AT,
            github=github,
            existing_snapshot=checkpoint,
        )

        self.assertEqual([call[2]["page"] for call in requester.calls], [2])
        self.assertEqual(snapshot.current_stargazers, 40)
        self.assertTrue(snapshot.complete)

    def test_snapshot_round_trip(self):
        snapshot = StarSnapshot(
            repository="example/project",
            accepted_at=ACCEPTED_AT,
            fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
            current_stargazers=12,
            weeks=(
                StarHistoryWeek(
                    week_started_at=datetime(2025, 1, 5, tzinfo=UTC),
                    total=3,
                    days=(0, 1, 0, 2, 0, 0, 0),
                ),
            ),
            pages_collected=1,
            total_pages=1,
            complete=True,
        )
        with TemporaryDirectory() as directory:
            path = Path(directory) / "stars.json"
            save_star_snapshot(snapshot, path)
            loaded = load_star_snapshot(path)

        self.assertEqual(loaded, snapshot)

    def test_week_total_must_match_daily_counts(self):
        requester = FakeRequester(
            {1: [{"week": 1_735_689_600, "total": 2, "days": [1] * 7}]}
        )
        repository = SimpleNamespace(
            url="https://api.github.com/repos/example/project",
            stargazers_count=42,
            _requester=requester,
        )
        github = SimpleNamespace(get_repo=lambda name: repository)

        with self.assertRaisesRegex(ValueError, "weekly total"):
            collect_star_snapshot(
                "example/project",
                accepted_at=ACCEPTED_AT,
                github=github,
            )
