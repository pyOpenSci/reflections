"""Build Tier 1 issue and PR figures from full-history derived tables."""

import argparse
from pathlib import Path

import pandas as pd

from reflections.analysis.plotting import (
    apply_plot_style,
    plot_change_distribution,
    plot_monthly_distribution,
    plot_paged_dumbbells,
    plot_period_distribution,
)

REQUIRED_COLUMNS = {
    "repository",
    "snapshot_fetched_at",
    "accepted_at",
    "analysis_window_days",
    "period",
    "within_window",
    "eligible_followup",
    "days_from_acceptance",
    "time_to_close_days",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--issues",
        type=Path,
        default=Path("data/derived/tier1_issues.csv"),
    )
    parser.add_argument(
        "--pull-requests",
        type=Path,
        default=Path("data/derived/tier1_pull_requests.csv"),
    )
    parser.add_argument("--cohort", type=Path, default=Path("data/derived/cohort.csv"))
    parser.add_argument(
        "--cohort-output",
        type=Path,
        default=Path("figures/cohort"),
    )
    parser.add_argument(
        "--issue-output",
        type=Path,
        default=Path("figures/issues"),
    )
    parser.add_argument(
        "--pr-output",
        type=Path,
        default=Path("figures/pull_requests"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    apply_plot_style()
    issues = pd.read_csv(args.issues)
    pull_requests = pd.read_csv(args.pull_requests)
    _validate(issues, "issue")
    _validate(pull_requests, "pull-request")
    window_days = _window_days(issues, pull_requests)
    eligible = _eligible_repositories(
        pd.read_csv(args.cohort),
        issues,
        pull_requests,
        window_days,
    )
    matched_issues = _matched(issues, eligible)
    matched_pull_requests = _matched(pull_requests, eligible)
    issue_summary = _summary(matched_issues, eligible, "issues")
    pr_summary = _summary(matched_pull_requests, eligible, "pull_requests")

    args.cohort_output.mkdir(parents=True, exist_ok=True)
    args.issue_output.mkdir(parents=True, exist_ok=True)
    args.pr_output.mkdir(parents=True, exist_ok=True)
    issue_summary.to_csv(args.issue_output / "tier1_issue_summary.csv", index=False)
    pr_summary.to_csv(args.pr_output / "tier1_package_summary.csv", index=False)

    _build_domain_figures(
        matched_issues,
        issue_summary,
        eligible,
        window_days,
        count_column="issues",
        label="issues",
        coverage_path=args.cohort_output / "issues_coverage.png",
        monthly_path=args.cohort_output / "issues_monthly_activity.png",
        close_path=args.cohort_output / "issues_median_close_change.png",
        appendix=args.issue_output / "appendix",
    )
    _build_domain_figures(
        matched_pull_requests,
        pr_summary,
        eligible,
        window_days,
        count_column="pull_requests",
        label="pull requests",
        coverage_path=args.cohort_output / "pull_requests_coverage.png",
        monthly_path=args.cohort_output / "pull_requests_monthly_activity.png",
        close_path=args.cohort_output / "pull_requests_median_close_change.png",
        appendix=args.pr_output / "appendix",
    )
    print(
        f"Wrote 6 Tier 1 cohort figures for {len(eligible)} repositories "
        f"using matched ±{window_days}-day windows"
    )
    print(
        f"Matched events: {len(matched_issues):,} issues and "
        f"{len(matched_pull_requests):,} pull requests"
    )
    return 0


def _build_domain_figures(
    events,
    summary,
    eligible,
    window_days,
    *,
    count_column,
    label,
    coverage_path,
    monthly_path,
    close_path,
    appendix,
):
    title_label = label.capitalize()
    plot_period_distribution(
        summary,
        value=count_column,
        path=coverage_path,
        title=f"Distribution of {label} in matched windows",
        ylabel=f"{title_label} per repository",
        fill_missing=True,
    )
    plot_monthly_distribution(
        events,
        path=monthly_path,
        title=f"Monthly {label} activity",
        ylabel=f"{title_label} per repository",
        repositories=eligible,
        window_days=window_days,
    )
    plot_change_distribution(
        summary,
        value="median_close_days",
        path=close_path,
        title=f"Change in median {label.rstrip('s')} close time",
        xlabel="Change in days (after − before; lower is faster)",
    )
    plot_paged_dumbbells(
        summary,
        value="median_close_days",
        output_dir=appendix,
        stem="median_close",
        title=f"Median {label.rstrip('s')} close time",
        xlabel="Days",
    )


def _summary(events, repositories, count_column):
    index = pd.MultiIndex.from_product(
        [sorted(repositories), ("before_acceptance", "after_acceptance")],
        names=["repository", "period"],
    )
    counts = events.groupby(["repository", "period"]).size().reindex(index, fill_value=0)
    close_days = (
        events.groupby(["repository", "period"])["time_to_close_days"]
        .median()
        .reindex(index)
    )
    return pd.DataFrame(
        {
            count_column: counts,
            "median_close_days": close_days,
        }
    ).reset_index()


def _matched(data, eligible):
    within = _boolean_column(data["within_window"])
    return data.loc[within & data["repository"].isin(eligible)].copy()


def _eligible_repositories(cohort, issues, pull_requests, window_days):
    if not {"repository", "accepted_at"} <= set(cohort.columns):
        raise SystemExit("The cohort CSV is missing repository or accepted_at")
    observed_at = min(
        pd.to_datetime(issues["snapshot_fetched_at"], utc=True).min(),
        pd.to_datetime(pull_requests["snapshot_fetched_at"], utc=True).min(),
    )
    accepted_at = pd.to_datetime(cohort["accepted_at"], utc=True)
    followup_days = (observed_at - accepted_at).dt.total_seconds() / 86_400
    return set(cohort.loc[followup_days >= window_days, "repository"])


def _window_days(issues, pull_requests):
    values = set(issues["analysis_window_days"].dropna().astype(int)) | set(
        pull_requests["analysis_window_days"].dropna().astype(int)
    )
    if len(values) != 1:
        raise SystemExit("Tier 1 tables do not share one analysis window")
    return values.pop()


def _validate(data, label):
    missing = sorted(REQUIRED_COLUMNS - set(data.columns))
    if missing:
        raise SystemExit(f"The {label} table is missing: {', '.join(missing)}")


def _boolean_column(values):
    if pd.api.types.is_bool_dtype(values):
        return values
    return values.astype(str).str.casefold().map({"true": True, "false": False})


if __name__ == "__main__":
    raise SystemExit(main())
