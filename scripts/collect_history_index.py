"""Pilot unwindowed issue and pull-request index collection for one repository."""

import argparse
from pathlib import Path
import sys

from requests import RequestException

from reflections import collect_history_index, load_history_index, save_history_index
from reflections._cli import github_token
from reflections.datasources.github import create_github


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
        "--output",
        type=Path,
        default=Path("data/github/history_indexes"),
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
    repository_key = args.repository.replace("/", "--").casefold()
    remaining_budget = args.request_budget
    for entity in entities:
        if remaining_budget == 0:
            print(f"{entity}: skipped because the run budget is exhausted")
            break
        final_path = args.output / entity / f"{repository_key}.json"
        partial_path = final_path.with_suffix(".partial.json")
        checkpoint_path = final_path if final_path.exists() else partial_path
        checkpoint = (
            load_history_index(checkpoint_path)
            if checkpoint_path.exists()
            else None
        )
        if checkpoint is not None and checkpoint.complete:
            print(f"{entity}: complete; using {checkpoint_path}")
            continue
        before = checkpoint.requests_used if checkpoint is not None else 0

        def progress(snapshot, page, total_pages):
            save_history_index(snapshot, partial_path)
            total = str(total_pages) if total_pages is not None else "?"
            print(
                f"{entity}: page {page}/{total}; {len(snapshot.records):,} "
                f"records; quota {snapshot.rate_remaining:,}",
                flush=True,
            )

        try:
            snapshot = collect_history_index(
                args.repository,
                entity,
                github=client,
                existing_snapshot=checkpoint,
                request_budget=remaining_budget,
                quota_floor=args.quota_floor,
                known_rate_remaining=remaining,
                on_progress=progress,
            )
        except RequestException as error:
            print(
                f"{entity}: GitHub connection failed; rerun to resume: {error}",
                file=sys.stderr,
            )
            return 1
        destination = final_path if snapshot.complete else partial_path
        save_history_index(snapshot, destination)
        if snapshot.complete:
            partial_path.unlink(missing_ok=True)
        used = snapshot.requests_used - before
        remaining_budget -= used
        remaining = snapshot.rate_remaining or remaining
        state = (
            "complete"
            if snapshot.complete
            else f"paused at page {snapshot.next_page}"
        )
        print(f"{entity}: {state}; used {used} page request(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
