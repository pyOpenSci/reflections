"""Summarize Tier 1 results across multiple matched-window lengths."""

import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--windows", type=int, nargs="+", default=(90, 180, 365))
    parser.add_argument(
        "--issue-figures",
        type=Path,
        default=Path("figures/issues"),
    )
    parser.add_argument(
        "--pr-figures",
        type=Path,
        default=Path("figures/pull_requests"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/derived/tier1/window_comparison.csv"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.windows or any(window <= 0 for window in args.windows):
        raise SystemExit("--windows must contain positive integers")
    rows = [
        _window_row(window, args.issue_figures, args.pr_figures)
        for window in args.windows
    ]
    output = args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output, index=False)
    print(f"Wrote {len(rows)} window comparisons to {output}")
    return 0


def _window_row(window, issue_directory, pr_directory):
    issues = pd.read_csv(
        issue_directory / f"tier1_{window}_days/tier1_issue_summary.csv"
    )
    pull_requests = pd.read_csv(
        pr_directory / f"tier1_{window}_days/tier1_package_summary.csv"
    )
    issue_values = _domain_values(issues, "issues", "issue")
    pr_values = _domain_values(pull_requests, "pull_requests", "pr")
    if issue_values["eligible_repositories"] != pr_values["eligible_repositories"]:
        raise ValueError(f"Issue and PR eligibility differ for the {window}-day window")
    return {
        "window_days": window,
        "eligible_repositories": issue_values.pop("eligible_repositories"),
        **issue_values,
        **pr_values,
    }


def _domain_values(summary, count_column, prefix):
    counts = summary.pivot(
        index="repository",
        columns="period",
        values=count_column,
    )
    close = summary.pivot(
        index="repository",
        columns="period",
        values="median_close_days",
    )
    paired_close = close.dropna(
        subset=["before_acceptance", "after_acceptance"],
        how="any",
    )
    return {
        "eligible_repositories": len(counts),
        f"matched_{prefix}_events": int(counts.to_numpy().sum()),
        f"repositories_with_{prefix}_events": int((counts.sum(axis=1) > 0).sum()),
        f"median_{prefix}_count_before": counts["before_acceptance"].median(),
        f"median_{prefix}_count_after": counts["after_acceptance"].median(),
        f"median_{prefix}_count_change": (
            counts["after_acceptance"] - counts["before_acceptance"]
        ).median(),
        f"paired_{prefix}_close_repositories": len(paired_close),
        f"median_{prefix}_close_change_days": (
            paired_close["after_acceptance"]
            - paired_close["before_acceptance"]
        ).median(),
    }


if __name__ == "__main__":
    raise SystemExit(main())
