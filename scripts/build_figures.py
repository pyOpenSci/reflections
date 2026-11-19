"""Build matched-window figures from the local PR-level CSV."""

import argparse
import math
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import pandas as pd

REQUIRED_COLUMNS = {
    "repository",
    "period",
    "days_from_acceptance",
    "within_window",
    "response_days",
    "has_response",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/derived/pull_requests.csv"),
        help="PR-level CSV (default: data/derived/pull_requests.csv)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("figures"),
        help="figure directory (default: figures)",
    )
    parser.add_argument(
        "--response-horizon",
        type=int,
        default=30,
        help="days shown in the cumulative-response figure (default: 30)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.response_horizon <= 0:
        raise SystemExit("--response-horizon must be positive")

    pull_requests = pd.read_csv(args.input)
    _validate_columns(pull_requests)
    pull_requests["within_window"] = _boolean_column(pull_requests["within_window"])
    pull_requests["has_response"] = _boolean_column(pull_requests["has_response"])
    matched = pull_requests.loc[pull_requests["within_window"]].copy()
    if matched.empty:
        raise SystemExit("The CSV has no pull requests inside the matched window")

    args.output.mkdir(parents=True, exist_ok=True)
    summary = _package_summary(matched)
    summary.to_csv(args.output / "package_summary.csv", index=False)
    _plot_cohort_coverage(matched, args.output / "cohort_coverage.png")
    _plot_median_response(summary, args.output / "median_response_dumbbell.png")
    _plot_cumulative_response(
        matched,
        args.output / "cumulative_response.png",
        horizon_days=args.response_horizon,
    )
    _plot_activity(matched, args.output / "pull_request_activity.png")
    print(f"Wrote package_summary.csv and 4 figures to {args.output}")
    return 0


def _package_summary(pull_requests: pd.DataFrame) -> pd.DataFrame:
    summary = (
        pull_requests.groupby(["repository", "period"], sort=True)
        .agg(
            pull_requests=("repository", "size"),
            responses=("has_response", "sum"),
            response_rate=("has_response", "mean"),
            median_response_days=("response_days", "median"),
            mean_response_days=("response_days", "mean"),
        )
        .reset_index()
    )
    return summary


def _plot_cohort_coverage(pull_requests: pd.DataFrame, path: Path) -> None:
    counts = (
        pull_requests.groupby(["repository", "period"])
        .size()
        .unstack(fill_value=0)
        .sort_index()
    )
    before = counts.get("before_acceptance", pd.Series(0, index=counts.index))
    after = counts.get("after_acceptance", pd.Series(0, index=counts.index))
    height = min(30, max(6, 0.28 * len(counts)))
    fig, ax = plt.subplots(figsize=(10, height))
    positions = range(len(counts))
    ax.barh(positions, -before, label="before acceptance")
    ax.barh(positions, after, label="after acceptance")
    ax.set_yticks(list(positions), labels=counts.index, fontsize=8)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set(
        title="Pull-request coverage in matched windows",
        xlabel="PRs before acceptance  ←   →  PRs after acceptance",
        ylabel="Repository",
    )
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{abs(value):g}"))
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_median_response(summary: pd.DataFrame, path: Path) -> None:
    medians = summary.pivot(
        index="repository",
        columns="period",
        values="median_response_days",
    ).dropna(subset=["before_acceptance", "after_acceptance"], how="any")
    medians = medians.sort_values("before_acceptance")
    height = min(30, max(5, 0.35 * len(medians)))
    fig, ax = plt.subplots(figsize=(10, height))
    if medians.empty:
        ax.text(
            0.5,
            0.5,
            "No package has observed responses in both periods",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.set_axis_off()
    else:
        for position, (_, values) in enumerate(medians.iterrows()):
            ax.plot(
                [values["before_acceptance"], values["after_acceptance"]],
                [position, position],
                color="0.75",
                zorder=1,
            )
        positions = range(len(medians))
        ax.scatter(
            medians["before_acceptance"],
            positions,
            label="before acceptance",
            zorder=2,
        )
        ax.scatter(
            medians["after_acceptance"],
            positions,
            label="after acceptance",
            zorder=2,
        )
        ax.set_yticks(list(positions), labels=medians.index, fontsize=8)
        ax.set(
            title="Median time to first observed maintainer response",
            xlabel="Days",
            ylabel="Repository",
        )
        ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_cumulative_response(
    pull_requests: pd.DataFrame,
    path: Path,
    *,
    horizon_days: int,
) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    days = list(range(horizon_days + 1))
    for period in ("before_acceptance", "after_acceptance"):
        group = pull_requests.loc[pull_requests["period"] == period]
        if group.empty:
            continue
        cumulative_share = [
            group["response_days"].le(day).fillna(False).mean() for day in days
        ]
        ax.step(
            days,
            cumulative_share,
            where="post",
            label=period.replace("_", " "),
        )
    ax.set(
        title="Cumulative share with an observed maintainer response",
        xlabel="Days after PR opened",
        ylabel="Share of all PRs",
        xlim=(0, horizon_days),
        ylim=(0, 1),
    )
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_activity(pull_requests: pd.DataFrame, path: Path) -> None:
    activity = pull_requests.copy()
    activity["relative_month"] = activity["days_from_acceptance"].map(
        lambda value: math.floor(value / 30.4375)
    )
    repository_count = activity["repository"].nunique()
    monthly = activity.groupby("relative_month").size() / repository_count
    monthly = monthly.reindex(
        range(int(monthly.index.min()), int(monthly.index.max()) + 1),
        fill_value=0,
    )
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(monthly.index, monthly.values, marker="o", markersize=3)
    ax.axvline(0, color="black", linestyle="--", label="acceptance")
    ax.set(
        title="Mean monthly pull requests per observed repository",
        xlabel="Month relative to acceptance",
        ylabel="Mean PRs per repository",
    )
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _validate_columns(dataframe: pd.DataFrame) -> None:
    missing = sorted(REQUIRED_COLUMNS - set(dataframe.columns))
    if missing:
        raise SystemExit(f"The PR-level CSV is missing columns: {', '.join(missing)}")


def _boolean_column(values: pd.Series) -> pd.Series:
    return values.astype(str).str.casefold().eq("true")


if __name__ == "__main__":
    raise SystemExit(main())
