"""Summarize Tier 2 comment-response results across matched windows."""

import argparse
from pathlib import Path

import pandas as pd

from reflections.analysis.tier2_tables import cumulative_response_curve


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--windows", type=int, nargs="+", default=(90, 180, 365))
    parser.add_argument(
        "--issue-figures", type=Path, default=Path("figures/issues")
    )
    parser.add_argument(
        "--pr-figures", type=Path, default=Path("figures/pull_requests")
    )
    parser.add_argument("--response-horizon", type=int, default=30)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/derived/tier2/window_comparison.csv"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.windows or any(window <= 0 for window in args.windows):
        raise SystemExit("--windows must contain positive integers")
    if args.response_horizon <= 0:
        raise SystemExit("--response-horizon must be positive")
    rows = []
    for window in args.windows:
        rows.extend(
            (
                _window_row(
                    window,
                    "issue",
                    args.issue_figures / f"tier2_{window}_days",
                    args.response_horizon,
                ),
                _window_row(
                    window,
                    "pull_request",
                    args.pr_figures / f"tier2_{window}_days",
                    args.response_horizon,
                ),
            )
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(args.output, index=False)
    print(f"Wrote {len(rows)} Tier 2 window comparisons to {args.output}")
    return 0


def _window_row(window, entity_type, directory, horizon):
    summary_path = directory / "tier2_response_summary.csv"
    matched_path = directory / "tier2_matched_responses.csv"
    if not summary_path.exists() or not matched_path.exists():
        raise SystemExit(f"Missing Tier 2 outputs under {directory}")
    summary = pd.read_csv(summary_path)
    matched = pd.read_csv(matched_path)
    response_column = f"response_rate_{horizon}_days"
    assessable_column = f"assessable_{horizon}_days"
    responses_column = f"responses_{horizon}_days"
    rates = summary.pivot(index="repository", columns="period", values=response_column)
    paired_rates = rates.dropna(
        subset=["before_acceptance", "after_acceptance"], how="any"
    )
    medians = summary.pivot(
        index="repository",
        columns="period",
        values="median_comment_response_days",
    ).dropna(subset=["before_acceptance", "after_acceptance"], how="any")
    return {
        "window_days": window,
        "entity_type": entity_type,
        "eligible_repositories": summary["repository"].nunique(),
        "matched_items": int(summary["items"].sum()),
        f"assessable_{horizon}_days": int(summary[assessable_column].sum()),
        f"responses_{horizon}_days": int(summary[responses_column].sum()),
        f"cohort_cumulative_response_before_{horizon}_days": _cohort_response(
            matched, "before_acceptance", horizon
        ),
        f"cohort_cumulative_response_after_{horizon}_days": _cohort_response(
            matched, "after_acceptance", horizon
        ),
        "paired_response_rate_repositories": len(paired_rates),
        f"median_repository_response_rate_before_{horizon}_days": paired_rates[
            "before_acceptance"
        ].median(),
        f"median_repository_response_rate_after_{horizon}_days": paired_rates[
            "after_acceptance"
        ].median(),
        f"median_repository_response_rate_change_{horizon}_days": (
            paired_rates["after_acceptance"] - paired_rates["before_acceptance"]
        ).median(),
        "paired_median_response_repositories": len(medians),
        "median_within_repository_response_days_change": (
            medians["after_acceptance"] - medians["before_acceptance"]
        ).median(),
    }


def _cohort_response(matched, period, horizon):
    group = matched.loc[matched["period"] == period]
    if group.empty:
        return float("nan")
    curve = cumulative_response_curve(
        pd.to_numeric(group["comment_response_observation_days"]).tolist(),
        _boolean_column(group["has_maintainer_comment"]).tolist(),
        horizon_days=horizon,
    )
    return curve[-1].cumulative_response


def _boolean_column(values):
    if pd.api.types.is_bool_dtype(values):
        return values
    return values.astype(str).str.casefold().map({"true": True, "false": False})


if __name__ == "__main__":
    raise SystemExit(main())
