"""Collect bulk issue and review comments for the local accepted cohort."""

import argparse
from pathlib import Path

from reflections import (
    collect_interaction_stream,
    load_interaction_snapshot,
    save_interaction_snapshot,
)
from reflections._cli import github_token
from reflections.analysis.interaction_manifest import write_interaction_manifest
from reflections.datasources.github import create_github
from reflections.workflows import read_repositories, run_cohort_collection


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", type=Path, default=Path("data/derived/cohort.csv"))
    parser.add_argument(
        "--entity",
        choices=("issue_comments", "review_comments", "both"),
        default="both",
    )
    parser.add_argument("--request-budget", type=int, default=100)
    parser.add_argument("--quota-floor", type=int, default=1000)
    parser.add_argument(
        "--retry-failures",
        action="store_true",
        help="retry repository/interaction pairs with a recorded API failure",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("data/github/interactions")
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/derived/interaction_manifest.csv"),
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
        ("issue_comments", "review_comments")
        if args.entity == "both"
        else (args.entity,)
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
        collector=collect_interaction_stream,
        loader=load_interaction_snapshot,
        saver=save_interaction_snapshot,
        manifest_writer=write_interaction_manifest,
        error_entity_field="interaction_type",
    )


if __name__ == "__main__":
    raise SystemExit(main())
