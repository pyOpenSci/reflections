"""Build censoring-aware Tier 2 maintainer-comment response figures."""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from reflections.analysis.plotting import (
    AFTER_COLOR,
    BEFORE_COLOR,
    apply_plot_style,
    plot_change_distribution,
    plot_paged_dumbbells,
    plot_period_distribution,
    save_figure,
)
from reflections.analysis.tier2_tables import cumulative_response_curve

REQUIRED_RESPONSE_COLUMNS = {
    "repository",
    "entity_type",
    "analysis_window_days",
    "period",
    "within_window",
    "eligible_followup",
    "comment_response_days",
    "comment_response_observation_days",
    "has_maintainer_comment",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--issues",
        type=Path,
        default=Path("data/derived/tier2_issue_comment_responses.csv"),
    )
    parser.add_argument(
        "--pull-requests",
        type=Path,
        default=Path("data/derived/tier2_pr_comment_responses.csv"),
    )
    parser.add_argument(
        "--coverage",
        type=Path,
        default=Path("data/derived/tier2_response_coverage.csv"),
    )
    parser.add_argument(
        "--cohort-output", type=Path, default=Path("figures/cohort/tier2_90_days")
    )
    parser.add_argument(
        "--issue-output", type=Path, default=Path("figures/issues/tier2_90_days")
    )
    parser.add_argument(
        "--pr-output",
        type=Path,
        default=Path("figures/pull_requests/tier2_90_days"),
    )
    parser.add_argument("--response-horizon", type=int, default=30)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.response_horizon <= 0:
        raise SystemExit("--response-horizon must be positive")
    apply_plot_style()
    issues = pd.read_csv(args.issues)
    pull_requests = pd.read_csv(args.pull_requests)
    coverage = pd.read_csv(args.coverage)
    _validate(issues, "issue")
    _validate(pull_requests, "pull-request")
    window_days = _window_days(issues, pull_requests)
    for path in (args.cohort_output, args.issue_output, args.pr_output):
        path.mkdir(parents=True, exist_ok=True)

    issue_count = _build_domain(
        issues,
        coverage,
        window_days,
        args.response_horizon,
        entity="issue",
        ready_column="issue_analysis_ready",
        eligible_column="issue_eligible_followup",
        cohort_output=args.cohort_output,
        domain_output=args.issue_output,
    )
    pr_count = _build_domain(
        pull_requests,
        coverage,
        window_days,
        args.response_horizon,
        entity="pull_request",
        ready_column="pull_request_analysis_ready",
        eligible_column="pull_request_eligible_followup",
        cohort_output=args.cohort_output,
        domain_output=args.pr_output,
    )
    print(
        f"Wrote 8 Tier 2 cohort figures for {issue_count} issue repositories and "
        f"{pr_count} pull-request repositories using matched ±{window_days}-day windows"
    )
    return 0


def _build_domain(
    data,
    coverage,
    window_days,
    horizon,
    *,
    entity,
    ready_column,
    eligible_column,
    cohort_output,
    domain_output,
):
    repositories = set(
        coverage.loc[
            _boolean_column(coverage[ready_column])
            & _boolean_column(coverage[eligible_column]),
            "repository",
        ]
    )
    matched = data.loc[
        _boolean_column(data["within_window"])
        & _boolean_column(data["eligible_followup"])
        & data["repository"].isin(repositories)
    ].copy()
    matched["has_maintainer_comment"] = _boolean_column(
        matched["has_maintainer_comment"]
    )
    label = "issues" if entity == "issue" else "pull requests"
    stem = "issues" if entity == "issue" else "pull_requests"
    summary = _repository_summary(matched, repositories, horizon)
    summary.to_csv(domain_output / "tier2_response_summary.csv", index=False)
    matched.to_csv(domain_output / "tier2_matched_responses.csv", index=False)

    plot_period_distribution(
        summary,
        value=f"response_rate_{horizon}_days",
        path=cohort_output / f"{stem}_comment_response_rate_{horizon}_days.png",
        title=f"{horizon}-day maintainer-comment response rate for {label}",
        ylabel=f"Share of assessable {label}",
    )
    plot_change_distribution(
        summary,
        value=f"response_rate_{horizon}_days",
        path=cohort_output
        / f"{stem}_comment_response_rate_{horizon}_days_change.png",
        title=f"Change in {horizon}-day comment-response rate for {label}",
        xlabel="Change in share (after − before; higher is more responses)",
    )
    plot_change_distribution(
        summary,
        value="median_comment_response_days",
        path=cohort_output / f"{stem}_median_comment_response_change.png",
        title=f"Change in median observed comment-response time for {label}",
        xlabel="Change in days (after − before; lower is faster)",
    )
    _plot_cumulative_response(
        matched,
        cohort_output / f"{stem}_cumulative_comment_response.png",
        horizon_days=horizon,
        label=label,
    )
    plot_paged_dumbbells(
        summary,
        value=f"response_rate_{horizon}_days",
        output_dir=domain_output / "appendix",
        stem=f"response_rate_{horizon}_days",
        title=f"{horizon}-day maintainer-comment response rate for {label}",
        xlabel="Share of assessable items",
    )
    return len(repositories)


def _repository_summary(events, repositories, horizon):
    rows = []
    for repository in sorted(repositories, key=str.casefold):
        for period in ("before_acceptance", "after_acceptance"):
            group = events.loc[
                (events["repository"] == repository) & (events["period"] == period)
            ]
            response_days = pd.to_numeric(
                group["comment_response_days"], errors="coerce"
            )
            observation_days = pd.to_numeric(
                group["comment_response_observation_days"], errors="coerce"
            )
            responded = group["has_maintainer_comment"]
            within_horizon = responded & response_days.le(horizon)
            assessable = within_horizon | observation_days.ge(horizon)
            assessable_count = int(assessable.sum())
            rows.append(
                {
                    "repository": repository,
                    "period": period,
                    "items": len(group),
                    "observed_maintainer_comments": int(responded.sum()),
                    f"assessable_{horizon}_days": assessable_count,
                    f"responses_{horizon}_days": int(within_horizon.sum()),
                    f"response_rate_{horizon}_days": (
                        float(within_horizon.sum() / assessable_count)
                        if assessable_count
                        else float("nan")
                    ),
                    "median_comment_response_days": response_days.loc[responded].median(),
                    "mean_comment_response_days": response_days.loc[responded].mean(),
                }
            )
    return pd.DataFrame(rows)


def _plot_cumulative_response(events, path, *, horizon_days, label):
    fig, ax = plt.subplots()
    descriptions = []
    for period, color, linestyle in (
        ("before_acceptance", BEFORE_COLOR, "--"),
        ("after_acceptance", AFTER_COLOR, "-"),
    ):
        group = events.loc[events["period"] == period]
        if group.empty:
            continue
        curve = cumulative_response_curve(
            pd.to_numeric(group["comment_response_observation_days"]).tolist(),
            group["has_maintainer_comment"].tolist(),
            horizon_days=horizon_days,
        )
        ax.step(
            [point.day for point in curve],
            [point.cumulative_response for point in curve],
            where="post",
            color=color,
            linestyle=linestyle,
            label=period.replace("_", " "),
        )
        descriptions.append(
            f"{period.replace('_', ' ')}: n={len(group)}, "
            f"estimated response by day {horizon_days}="
            f"{curve[-1].cumulative_response:.1%}"
        )
    ax.set(
        title=f"Cumulative maintainer-comment response for {label}",
        xlabel=f"Days after {label.rstrip('s')} opened",
        ylabel="Estimated cumulative response",
        xlim=(0, horizon_days),
        ylim=(0, 1),
    )
    ax.legend()
    fig.tight_layout()
    save_figure(
        fig,
        path,
        f"Censoring-aware cumulative incidence of a qualifying maintainer comment "
        f"within {horizon_days} days. " + "; ".join(descriptions) + ".",
    )


def _window_days(issues, pull_requests):
    values = set(issues["analysis_window_days"].dropna().astype(int)) | set(
        pull_requests["analysis_window_days"].dropna().astype(int)
    )
    if len(values) != 1:
        raise SystemExit("Tier 2 response tables do not share one analysis window")
    return values.pop()


def _validate(data, label):
    missing = sorted(REQUIRED_RESPONSE_COLUMNS - set(data.columns))
    if missing:
        raise SystemExit(f"The {label} response table is missing: {', '.join(missing)}")


def _boolean_column(values):
    if pd.api.types.is_bool_dtype(values):
        return values
    return values.astype(str).str.casefold().map({"true": True, "false": False})


if __name__ == "__main__":
    raise SystemExit(main())
