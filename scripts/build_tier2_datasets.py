"""Build issue- and PR-level comment-response tables from local Tier 2 data."""

import argparse
import csv
import json
from pathlib import Path

from reflections import (
    load_history_index,
    load_interaction_snapshot,
    write_comment_response_csv,
)
from reflections.analysis.tier2_tables import comment_response_rows
from reflections.workflows import load_cohort, repository_cache_key

COVERAGE_COLUMNS = (
    "repository",
    "package",
    "issue_comments_status",
    "review_comments_status",
    "issue_analysis_ready",
    "pull_request_analysis_ready",
    "indexed_issues",
    "indexed_pull_requests",
    "issue_comments",
    "issue_comments_mapped_to_issues",
    "issue_comments_mapped_to_pull_requests",
    "unmapped_issue_comments",
    "review_comments",
    "review_comments_mapped_to_pull_requests",
    "unmapped_review_comments",
    "issue_observation_cutoff",
    "pull_request_observation_cutoff",
    "issue_eligible_followup",
    "pull_request_eligible_followup",
    "issue_comments_error",
    "review_comments_error",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", type=Path, default=Path("data/derived/cohort.csv"))
    parser.add_argument(
        "--indexes", type=Path, default=Path("data/github/history_indexes")
    )
    parser.add_argument(
        "--interactions", type=Path, default=Path("data/github/interactions")
    )
    parser.add_argument(
        "--issue-output",
        type=Path,
        default=Path("data/derived/tier2_issue_comment_responses.csv"),
    )
    parser.add_argument(
        "--pr-output",
        type=Path,
        default=Path("data/derived/tier2_pr_comment_responses.csv"),
    )
    parser.add_argument(
        "--coverage-output",
        type=Path,
        default=Path("data/derived/tier2_response_coverage.csv"),
    )
    parser.add_argument("--window-days", type=int, default=90)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.window_days <= 0:
        raise SystemExit("--window-days must be positive")
    try:
        cohort = load_cohort(args.cohort)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    issue_rows = []
    pr_rows = []
    coverage_rows = []
    for cohort_row in cohort:
        repository = cohort_row.repository
        package = cohort_row.package
        acceptance = cohort_row.accepted_at
        key = repository_cache_key(repository)
        issues = _index(args.indexes, "issues", key)
        pull_requests = _index(args.indexes, "pull_requests", key)
        issue_comments, issue_status, issue_error = _interaction(
            args.interactions, "issue_comments", key
        )
        review_comments, review_status, review_error = _interaction(
            args.interactions, "review_comments", key
        )
        issue_ready = issue_status == "complete"
        pr_ready = issue_ready and review_status == "complete"
        if issue_ready:
            issue_rows.extend(
                comment_response_rows(
                    issues,
                    issue_comments,
                    accepted_at=acceptance,
                    package=package,
                    window_days=args.window_days,
                )
            )
        if pr_ready:
            pr_rows.extend(
                comment_response_rows(
                    pull_requests,
                    issue_comments,
                    review_comments=review_comments,
                    accepted_at=acceptance,
                    package=package,
                    window_days=args.window_days,
                )
            )
        coverage_rows.append(
            _coverage_row(
                repository,
                package,
                acceptance,
                args.window_days,
                issues,
                pull_requests,
                issue_comments,
                review_comments,
                issue_status,
                review_status,
                issue_error,
                review_error,
            )
        )

    issue_path = write_comment_response_csv(issue_rows, args.issue_output)
    pr_path = write_comment_response_csv(pr_rows, args.pr_output)
    _write_csv(coverage_rows, COVERAGE_COLUMNS, args.coverage_output)
    issue_ready_count = sum(row["issue_analysis_ready"] for row in coverage_rows)
    pr_ready_count = sum(row["pull_request_analysis_ready"] for row in coverage_rows)
    print(f"Wrote {len(issue_rows):,} issue rows to {issue_path}")
    print(f"Wrote {len(pr_rows):,} pull-request rows to {pr_path}")
    print(
        f"Analysis-ready repositories: {issue_ready_count}/{len(cohort)} issues; "
        f"{pr_ready_count}/{len(cohort)} pull requests"
    )
    print(f"Wrote coverage audit to {args.coverage_output}")
    return 0


def _index(directory, entity, key):
    path = directory / entity / f"{key}.json"
    if not path.exists():
        raise SystemExit(f"Missing Tier 1 index: {path}")
    snapshot = load_history_index(path)
    if not snapshot.complete:
        raise SystemExit(f"Incomplete Tier 1 index: {path}")
    return snapshot


def _interaction(directory, interaction_type, key):
    final_path = directory / interaction_type / f"{key}.json"
    partial_path = final_path.with_suffix(".partial.json")
    error_path = directory / "errors" / interaction_type / f"{key}.json"
    error = ""
    if error_path.exists():
        error = json.loads(error_path.read_text(encoding="utf-8")).get("message", "")
    if final_path.exists():
        snapshot = load_interaction_snapshot(final_path)
        return snapshot, "complete" if snapshot.complete else "partial", error
    if partial_path.exists():
        return load_interaction_snapshot(partial_path), "partial", error
    return None, "failed" if error else "missing", error


def _coverage_row(
    repository,
    package,
    acceptance,
    window_days,
    issues,
    pull_requests,
    issue_comments,
    review_comments,
    issue_status,
    review_status,
    issue_error,
    review_error,
):
    issue_numbers = {item.number for item in issues.records}
    pr_numbers = {item.number for item in pull_requests.records}
    issue_records = () if issue_comments is None else issue_comments.records
    review_records = () if review_comments is None else review_comments.records
    issue_ready = issue_status == "complete"
    pr_ready = issue_ready and review_status == "complete"
    issue_cutoff = (
        min(issues.fetched_at, issue_comments.fetched_at) if issue_ready else None
    )
    pr_cutoff = (
        min(
            pull_requests.fetched_at,
            issue_comments.fetched_at,
            review_comments.fetched_at,
        )
        if pr_ready
        else None
    )
    return {
        "repository": repository,
        "package": package,
        "issue_comments_status": issue_status,
        "review_comments_status": review_status,
        "issue_analysis_ready": issue_ready,
        "pull_request_analysis_ready": pr_ready,
        "indexed_issues": len(issue_numbers),
        "indexed_pull_requests": len(pr_numbers),
        "issue_comments": len(issue_records),
        "issue_comments_mapped_to_issues": sum(
            record.parent_number in issue_numbers for record in issue_records
        ),
        "issue_comments_mapped_to_pull_requests": sum(
            record.parent_number in pr_numbers for record in issue_records
        ),
        "unmapped_issue_comments": sum(
            record.parent_number not in issue_numbers | pr_numbers
            for record in issue_records
        ),
        "review_comments": len(review_records),
        "review_comments_mapped_to_pull_requests": sum(
            record.parent_number in pr_numbers for record in review_records
        ),
        "unmapped_review_comments": sum(
            record.parent_number not in pr_numbers for record in review_records
        ),
        "issue_observation_cutoff": "" if issue_cutoff is None else issue_cutoff.isoformat(),
        "pull_request_observation_cutoff": (
            "" if pr_cutoff is None else pr_cutoff.isoformat()
        ),
        "issue_eligible_followup": (
            False
            if issue_cutoff is None
            else (issue_cutoff - acceptance).total_seconds() / 86_400 >= window_days
        ),
        "pull_request_eligible_followup": (
            False
            if pr_cutoff is None
            else (pr_cutoff - acceptance).total_seconds() / 86_400 >= window_days
        ),
        "issue_comments_error": issue_error,
        "review_comments_error": review_error,
    }


def _write_csv(rows, columns, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
