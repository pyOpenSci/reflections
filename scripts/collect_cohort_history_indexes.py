"""Collect unwindowed issue and PR indexes for the local accepted cohort."""

import argparse
import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from github import GithubException
from requests import RequestException

from reflections import collect_history_index, load_history_index, save_history_index
from reflections._cli import github_token
from reflections.analysis.history_index_manifest import write_history_index_manifest
from reflections.datasources.github import create_github


class IndexCollectionError(Exception):
    """A repository-level API failure with its consumed request count."""

    def __init__(self, original: GithubException, requests_used: int):
        super().__init__(str(original))
        self.original = original
        self.requests_used = requests_used


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", type=Path, default=Path("data/derived/cohort.csv"))
    parser.add_argument(
        "--entity",
        choices=("issues", "pull_requests", "both"),
        default="both",
    )
    parser.add_argument("--request-budget", type=int, default=100)
    parser.add_argument("--quota-floor", type=int, default=1000)
    parser.add_argument(
        "--retry-failures",
        action="store_true",
        help="retry repository/entity pairs with a recorded API failure",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/github/history_indexes"),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/derived/history_index_manifest.csv"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.request_budget <= 0:
        raise SystemExit("--request-budget must be positive")
    if args.quota_floor < 0:
        raise SystemExit("--quota-floor must not be negative")
    repositories = _repositories(args.cohort)
    entities = (
        ("issues", "pull_requests") if args.entity == "both" else (args.entity,)
    )
    client = create_github(token=github_token())
    try:
        rate_remaining, rate_limit = client.rate_limiting
    except RequestException as error:
        print(
            f"GitHub is unavailable; no page budget was spent: {error}",
            file=sys.stderr,
        )
        return 1
    print(
        f"Cohort: {len(repositories)} repositories; quota: "
        f"{rate_remaining:,}/{rate_limit:,}; page budget: {args.request_budget:,}; "
        f"protected floor: {args.quota_floor:,}",
        flush=True,
    )
    budget = args.request_budget
    exit_code = 0
    try:
        for repository in repositories:
            for entity in entities:
                if budget == 0 or rate_remaining <= args.quota_floor:
                    print("Collection paused cleanly at the configured budget boundary")
                    return 0
                error_path = _error_path(args.output, repository, entity)
                if error_path.exists() and not args.retry_failures:
                    print(f"{repository} {entity}: failed previously; cached")
                    continue
                try:
                    snapshot, used = _collect_one(
                        repository,
                        entity,
                        client=client,
                        output=args.output,
                        request_budget=budget,
                        quota_floor=args.quota_floor,
                        rate_remaining=rate_remaining,
                    )
                except IndexCollectionError as error:
                    budget = max(0, budget - error.requests_used)
                    rate_remaining = max(0, rate_remaining - error.requests_used)
                    _save_error(args.output, repository, entity, error.original)
                    print(
                        f"{repository} {entity}: failed; recorded for audit: {error}",
                        file=sys.stderr,
                    )
                    continue
                budget -= used
                rate_remaining = snapshot.rate_remaining or rate_remaining
    except RequestException as error:
        print(f"GitHub connection failed; rerun to resume: {error}", file=sys.stderr)
        exit_code = 1
    finally:
        path = write_history_index_manifest(
            repositories, args.output, args.manifest
        )
        print(f"Wrote collection manifest to {path}")
    return exit_code


def _collect_one(
    repository,
    entity,
    *,
    client,
    output,
    request_budget,
    quota_floor,
    rate_remaining,
):
    key = repository.replace("/", "--").casefold()
    final_path = output / entity / f"{key}.json"
    partial_path = final_path.with_suffix(".partial.json")
    checkpoint_path = final_path if final_path.exists() else partial_path
    checkpoint = (
        load_history_index(checkpoint_path) if checkpoint_path.exists() else None
    )
    if checkpoint is not None and checkpoint.complete:
        print(f"{repository} {entity}: complete; cached")
        return checkpoint, 0
    before = checkpoint.requests_used if checkpoint is not None else 0

    def progress(snapshot, page, total_pages):
        save_history_index(snapshot, partial_path)
        total = str(total_pages) if total_pages is not None else "?"
        print(
            f"{repository} {entity}: page {page}/{total}; "
            f"{len(snapshot.records):,} records; quota {snapshot.rate_remaining:,}",
            flush=True,
        )

    try:
        snapshot = collect_history_index(
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
        latest = (
            load_history_index(partial_path) if partial_path.exists() else checkpoint
        )
        successful = latest.requests_used - before if latest is not None else 0
        raise IndexCollectionError(error, successful + 1) from error
    destination = final_path if snapshot.complete else partial_path
    save_history_index(snapshot, destination)
    if snapshot.complete:
        partial_path.unlink(missing_ok=True)
    _error_path(output, repository, entity).unlink(missing_ok=True)
    used = snapshot.requests_used - before
    state = "complete" if snapshot.complete else f"paused at page {snapshot.next_page}"
    print(f"{repository} {entity}: {state}; used {used} page request(s)")
    return snapshot, used


def _repositories(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as stream:
        repositories = [row["repository"] for row in csv.DictReader(stream)]
    if not repositories:
        raise SystemExit(f"No repositories found in {path}")
    return repositories


def _save_error(output: Path, repository: str, entity: str, error: Exception) -> None:
    path = _error_path(output, repository, entity)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "repository": repository,
                "entity_type": entity,
                "failed_at": datetime.now(UTC).isoformat(),
                "message": str(error),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _error_path(output: Path, repository: str, entity: str) -> Path:
    key = repository.replace("/", "--").casefold()
    return output / "errors" / entity / f"{key}.json"


if __name__ == "__main__":
    raise SystemExit(main())
