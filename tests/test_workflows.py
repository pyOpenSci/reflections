from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from reflections.workflows import (
    SnapshotPaths,
    collect_one_stream,
    load_cohort,
    repository_cache_key,
)


def test_load_cohort_validates_and_parses_shared_fields(tmp_path):
    path = tmp_path / "cohort.csv"
    path.write_text(
        "repository,package,accepted_at\n"
        "Org/Project,example,2025-01-01T00:00:00+00:00\n",
        encoding="utf-8",
    )

    cohort = load_cohort(path)

    assert cohort[0].repository == "Org/Project"
    assert cohort[0].package == "example"
    assert cohort[0].accepted_at == datetime(2025, 1, 1, tzinfo=UTC)


def test_load_cohort_rejects_duplicate_repositories(tmp_path):
    path = tmp_path / "cohort.csv"
    path.write_text(
        "repository,package,accepted_at\n"
        "Org/Project,one,2025-01-01T00:00:00+00:00\n"
        "org/project,two,2025-01-02T00:00:00+00:00\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Duplicate repositories"):
        load_cohort(path)


def test_repository_cache_key_and_paths():
    assert repository_cache_key("Org/Project") == "org--project"
    paths = SnapshotPaths.for_stream(Path("cache"), "Org/Project", "issues")
    assert paths.final == Path("cache/issues/org--project.json")
    assert paths.partial == Path("cache/issues/org--project.partial.json")
    assert paths.error == Path("cache/errors/issues/org--project.json")
    with pytest.raises(ValueError, match="owner/name"):
        repository_cache_key("project")


def test_collect_one_stream_reuses_complete_snapshot(tmp_path):
    paths = SnapshotPaths.for_stream(tmp_path, "org/project", "issues")
    paths.final.parent.mkdir(parents=True)
    paths.final.write_text("cached", encoding="utf-8")
    snapshot = SimpleNamespace(complete=True, requests_used=4)

    result, used = collect_one_stream(
        "org/project",
        "issues",
        client=object(),
        output=tmp_path,
        request_budget=10,
        quota_floor=1,
        rate_remaining=100,
        collector=lambda *args, **kwargs: pytest.fail("collector was called"),
        loader=lambda path: snapshot,
        saver=lambda item, path: path,
    )

    assert result is snapshot
    assert used == 0
