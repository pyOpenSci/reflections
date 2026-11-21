"""Collect unwindowed issue and PR indexes for the local accepted cohort."""

import argparse
from pathlib import Path

from reflections import collect_history_index, load_history_index, save_history_index
from reflections._cli import github_token
from reflections.analysis.history_index_manifest import write_history_index_manifest
from reflections.datasources.github import create_github
from reflections.workflows import read_repositories, run_cohort_collection


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
        "--output", type=Path, default=Path("data/github/history_indexes")
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
    try:
        repositories = read_repositories(args.cohort)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    entities = (
        ("issues", "pull_requests") if args.entity == "both" else (args.entity,)
    )
    return run_cohort_collection(
        repositories,
        entities,
        client=create_github(token=github_token()),
        output=args.output,
        manifest=args.manifest,
        request_budget=args.request_budget,
        quota_floor=args.quota_floor,
        retry_failures=args.retry_failures,
        collector=collect_history_index,
        loader=load_history_index,
        saver=save_history_index,
        manifest_writer=write_history_index_manifest,
        error_entity_field="entity_type",
    )


if __name__ == "__main__":
    raise SystemExit(main())
