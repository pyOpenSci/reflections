"""Collect an unwindowed issue or pull-request index for one repository."""

import argparse
import sys
from pathlib import Path

from requests import RequestException

from reflections import collect_history_index, load_history_index, save_history_index
from reflections._cli import github_token
from reflections.datasources.github import create_github
from reflections.workflows import CollectionFailure, collect_one_stream


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", help="GitHub repository as owner/name")
    parser.add_argument(
        "--entity",
        choices=("issues", "pull_requests", "both"),
        default="both",
    )
    parser.add_argument("--request-budget", type=int, default=25)
    parser.add_argument("--quota-floor", type=int, default=500)
    parser.add_argument(
        "--output", type=Path, default=Path("data/github/history_indexes")
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.request_budget <= 0:
        raise SystemExit("--request-budget must be positive")
    if args.quota_floor < 0:
        raise SystemExit("--quota-floor must not be negative")
    client = create_github(token=github_token())
    try:
        remaining, limit = client.rate_limiting
    except RequestException as error:
        print(
            f"GitHub is unavailable; no page budget was spent: {error}",
            file=sys.stderr,
        )
        return 1
    print(
        f"GitHub quota: {remaining:,}/{limit:,}; hard run budget: "
        f"{args.request_budget:,}; protected floor: {args.quota_floor:,}",
        flush=True,
    )
    entities = (
        ("issues", "pull_requests") if args.entity == "both" else (args.entity,)
    )
    budget = args.request_budget
    for entity in entities:
        if budget == 0:
            print(f"{entity}: skipped because the run budget is exhausted")
            break
        try:
            snapshot, used = collect_one_stream(
                args.repository,
                entity,
                client=client,
                output=args.output,
                request_budget=budget,
                quota_floor=args.quota_floor,
                rate_remaining=remaining,
                collector=collect_history_index,
                loader=load_history_index,
                saver=save_history_index,
            )
        except (CollectionFailure, RequestException) as error:
            print(
                f"{entity}: GitHub collection failed; rerun to resume: {error}",
                file=sys.stderr,
            )
            return 1
        budget -= used
        if snapshot.rate_remaining is not None:
            remaining = snapshot.rate_remaining
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
