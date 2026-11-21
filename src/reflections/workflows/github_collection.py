"""Shared resumable orchestration for paginated GitHub collection."""

import json
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from github import GithubException
from requests import RequestException


def repository_cache_key(repository: str) -> str:
    """Return the stable filename stem for an owner/repository name."""

    owner, separator, name = repository.strip().partition("/")
    if not separator or not owner or not name or "/" in name:
        raise ValueError("repository must use the owner/name form")
    return f"{owner}--{name}".casefold()


@dataclass(frozen=True)
class SnapshotPaths:
    """Final, partial, and failure paths for one collection stream."""

    final: Path
    partial: Path
    error: Path

    @classmethod
    def for_stream(
        cls,
        directory: str | Path,
        repository: str,
        entity: str,
    ) -> "SnapshotPaths":
        root = Path(directory)
        key = repository_cache_key(repository)
        final = root / entity / f"{key}.json"
        return cls(
            final=final,
            partial=final.with_suffix(".partial.json"),
            error=root / "errors" / entity / f"{key}.json",
        )

    @property
    def checkpoint(self) -> Path | None:
        """Return the preferred existing checkpoint, if any."""

        if self.final.exists():
            return self.final
        return self.partial if self.partial.exists() else None


class CollectionFailure(Exception):
    """An API failure annotated with the request budget it consumed."""

    def __init__(self, original: GithubException, requests_used: int):
        super().__init__(str(original))
        self.original = original
        self.requests_used = requests_used


def collect_one_stream(
    repository: str,
    entity: str,
    *,
    client: Any,
    output: Path,
    request_budget: int,
    quota_floor: int,
    rate_remaining: int,
    collector: Callable[..., Any],
    loader: Callable[[Path], Any],
    saver: Callable[[Any, Path], Path],
    progress_label: str | None = None,
) -> tuple[Any, int]:
    """Resume and atomically checkpoint one repository/entity stream."""

    paths = SnapshotPaths.for_stream(output, repository, entity)
    checkpoint_path = paths.checkpoint
    checkpoint = loader(checkpoint_path) if checkpoint_path is not None else None
    if checkpoint is not None and checkpoint.complete:
        print(f"{progress_label or repository} {entity}: complete; cached")
        return checkpoint, 0
    before = checkpoint.requests_used if checkpoint is not None else 0

    def progress(snapshot, page, total_pages):
        saver(snapshot, paths.partial)
        total = str(total_pages) if total_pages is not None else "?"
        print(
            f"{progress_label or repository} {entity}: page {page}/{total}; "
            f"{len(snapshot.records):,} records; quota {snapshot.rate_remaining:,}",
            flush=True,
        )

    try:
        snapshot = collector(
            repository,
            entity,
            github=client,
            existing_snapshot=checkpoint,
            request_budget=request_budget,
            quota_floor=quota_floor,
            known_rate_remaining=rate_remaining,
            on_progress=progress,
        )
    except GithubException as error:
        latest = loader(paths.partial) if paths.partial.exists() else checkpoint
        successful = latest.requests_used - before if latest is not None else 0
        raise CollectionFailure(error, successful + 1) from error
    destination = paths.final if snapshot.complete else paths.partial
    saver(snapshot, destination)
    if snapshot.complete:
        paths.partial.unlink(missing_ok=True)
    paths.error.unlink(missing_ok=True)
    used = snapshot.requests_used - before
    state = "complete" if snapshot.complete else f"paused at page {snapshot.next_page}"
    print(f"{progress_label or repository} {entity}: {state}; used {used} page request(s)")
    return snapshot, used


def run_cohort_collection(
    repositories: Iterable[str],
    entities: Iterable[str],
    *,
    client: Any,
    output: Path,
    manifest: Path,
    request_budget: int,
    quota_floor: int,
    retry_failures: bool,
    collector: Callable[..., Any],
    loader: Callable[[Path], Any],
    saver: Callable[[Any, Path], Path],
    manifest_writer: Callable[[list[str], Path, Path], Path],
    error_entity_field: str,
) -> int:
    """Run a bounded cohort collection using one shared request budget."""

    repository_list = list(repositories)
    entity_list = tuple(entities)
    try:
        rate_remaining, rate_limit = client.rate_limiting
    except RequestException as error:
        print(
            f"GitHub is unavailable; no page budget was spent: {error}",
            file=sys.stderr,
        )
        return 1
    print(
        f"Cohort: {len(repository_list)} repositories; quota: "
        f"{rate_remaining:,}/{rate_limit:,}; page budget: {request_budget:,}; "
        f"protected floor: {quota_floor:,}",
        flush=True,
    )
    budget = request_budget
    exit_code = 0
    try:
        for repository in repository_list:
            for entity in entity_list:
                if budget == 0 or rate_remaining <= quota_floor:
                    print("Collection paused cleanly at the configured budget boundary")
                    return 0
                paths = SnapshotPaths.for_stream(output, repository, entity)
                if paths.error.exists() and not retry_failures:
                    print(f"{repository} {entity}: failed previously; cached")
                    continue
                try:
                    snapshot, used = collect_one_stream(
                        repository,
                        entity,
                        client=client,
                        output=output,
                        request_budget=budget,
                        quota_floor=quota_floor,
                        rate_remaining=rate_remaining,
                        collector=collector,
                        loader=loader,
                        saver=saver,
                    )
                except CollectionFailure as error:
                    budget = max(0, budget - error.requests_used)
                    rate_remaining = max(0, rate_remaining - error.requests_used)
                    _write_error(
                        paths.error,
                        repository,
                        error_entity_field,
                        entity,
                        error.original,
                    )
                    print(
                        f"{repository} {entity}: failed; recorded for audit: {error}",
                        file=sys.stderr,
                    )
                    continue
                budget -= used
                if snapshot.rate_remaining is not None:
                    rate_remaining = snapshot.rate_remaining
    except RequestException as error:
        print(f"GitHub connection failed; rerun to resume: {error}", file=sys.stderr)
        exit_code = 1
    finally:
        path = manifest_writer(repository_list, output, manifest)
        print(f"Wrote collection manifest to {path}")
    return exit_code


def _write_error(path, repository, entity_field, entity, error):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "repository": repository,
                entity_field: entity,
                "failed_at": datetime.now(UTC).isoformat(),
                "message": str(error),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
