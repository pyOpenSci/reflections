from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from reflections.datasources.github import load_snapshot, save_snapshot
from reflections.datasources.github.models import (
    PullRequestRecord,
    RepositorySnapshot,
    ResponseEvent,
)


class SnapshotTests(unittest.TestCase):
    def test_json_snapshot_round_trip(self):
        created_at = datetime(2025, 2, 1, tzinfo=UTC)
        snapshot = RepositorySnapshot(
            repository="example/project",
            accepted_at=datetime(2025, 1, 1, tzinfo=UTC),
            fetched_at=datetime(2025, 3, 1, tzinfo=UTC),
            pull_requests=(
                PullRequestRecord(
                    number=10,
                    title="A change",
                    url="https://github.com/example/project/pull/10",
                    author_login="contributor",
                    created_at=created_at,
                    closed_at=None,
                    merged_at=None,
                    responses=(
                        ResponseEvent(
                            kind="review",
                            created_at=datetime(2025, 2, 2, tzinfo=UTC),
                            author_login="maintainer",
                            author_association="MEMBER",
                        ),
                    ),
                ),
            ),
        )

        with TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "snapshot.json"
            saved_path = save_snapshot(snapshot, path)
            restored = load_snapshot(path)

        self.assertEqual(saved_path, path)
        self.assertEqual(restored, snapshot)

    def test_rejects_unknown_schema_version(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            path.write_text(json.dumps({"schema_version": 100}), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Unsupported snapshot"):
                load_snapshot(path)

    def test_loads_version_one_snapshot_without_a_window(self):
        data = {
            "schema_version": 1,
            "repository": "example/project",
            "accepted_at": "2025-01-01T00:00:00+00:00",
            "fetched_at": "2025-02-01T00:00:00+00:00",
            "pull_requests": [],
        }
        with TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            snapshot = load_snapshot(path)

        self.assertEqual(snapshot.schema_version, 2)
        self.assertIsNone(snapshot.window_days)


if __name__ == "__main__":
    unittest.main()
