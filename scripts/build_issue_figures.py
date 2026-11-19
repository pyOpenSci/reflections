"""Build before/after figures from the local issue-level CSV."""

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
    "is_closed",
    "has_acknowledgement",
    "has_been_addressed",
    "acknowledgement_days",
    "addressed_days",
    "time_to_close_days",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/derived/issues.csv"),
        help="issue-level CSV (default: data/derived/issues.csv)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("figures/issues"),
        help="figure directory (default: figures/issues)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    issues = pd.read_csv(args.input)
    _validate_columns(issues)
    for column in (
        "within_window",
        "is_closed",
        "has_acknowledgement",
        "has_been_addressed",
    ):
        issues[column] = _boolean_column(issues[column])
    matched = issues.loc[issues["within_window"]].copy()
    if matched.empty:
        raise SystemExit("The CSV has no issues inside the matched window")

    args.output.mkdir(parents=True, exist_ok=True)
    summary = _issue_summary(matched)
    summary.to_csv(args.output / "issue_summary.csv", index=False)
    _plot_coverage(matched, args.output / "issue_coverage.png")
    _plot_metric_dumbbell(
        summary,
        value="median_addressed_days",
        title="Median time until an issue was first addressed",
        empty_message="No package has addressed issues in both periods",
        path=args.output / "median_addressed_dumbbell.png",
    )
    _plot_metric_dumbbell(
        summary,
        value="median_close_days",
        title="Median time to close among closed issues",
        empty_message="No package has closed issues in both periods",
        path=args.output / "median_close_dumbbell.png",
    )
    _plot_activity(matched, args.output / "monthly_issue_activity.png")
    print(f"Wrote issue_summary.csv and 4 figures to {args.output}")
    return 0


def _issue_summary(issues: pd.DataFrame) -> pd.DataFrame:
    return (
        issues.groupby(["repository", "period"], sort=True)
        .agg(
            issues=("repository", "size"),
            acknowledgements=("has_acknowledgement", "sum"),
            acknowledgement_rate=("has_acknowledgement", "mean"),
            addressed=("has_been_addressed", "sum"),
            addressed_rate=("has_been_addressed", "mean"),
            closed=("is_closed", "sum"),
            close_rate=("is_closed", "mean"),
            mean_acknowledgement_days=("acknowledgement_days", "mean"),
            median_acknowledgement_days=("acknowledgement_days", "median"),
            mean_addressed_days=("addressed_days", "mean"),
            median_addressed_days=("addressed_days", "median"),
            mean_close_days=("time_to_close_days", "mean"),
            median_close_days=("time_to_close_days", "median"),
        )
        .reset_index()
    )


def _plot_coverage(issues: pd.DataFrame, path: Path) -> None:
    counts = (
        issues.groupby(["repository", "period"])
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
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{abs(value):g}"))
    ax.set(
        title="Issue coverage in matched windows",
        xlabel="Issues before acceptance  ←   →  Issues after acceptance",
        ylabel="Repository",
    )
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_metric_dumbbell(
    summary: pd.DataFrame,
    *,
    value: str,
    title: str,
    empty_message: str,
    path: Path,
) -> None:
    values = summary.pivot(
        index="repository",
        columns="period",
        values=value,
    ).dropna(subset=["before_acceptance", "after_acceptance"], how="any")
    values = values.sort_values("before_acceptance")
    height = min(30, max(5, 0.35 * len(values)))
    fig, ax = plt.subplots(figsize=(10, height))
    if values.empty:
        ax.text(
            0.5,
            0.5,
            empty_message,
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.set_axis_off()
    else:
        positions = range(len(values))
        for position, (_, row) in enumerate(values.iterrows()):
            ax.plot(
                [row["before_acceptance"], row["after_acceptance"]],
                [position, position],
                color="0.75",
                zorder=1,
            )
        ax.scatter(
            values["before_acceptance"],
            positions,
            label="before acceptance",
            zorder=2,
        )
        ax.scatter(
            values["after_acceptance"],
            positions,
            label="after acceptance",
            zorder=2,
        )
        ax.set_yticks(list(positions), labels=values.index, fontsize=8)
        ax.set(title=title, xlabel="Days", ylabel="Repository")
        ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_activity(issues: pd.DataFrame, path: Path) -> None:
    activity = issues.copy()
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
        title="Mean monthly issues per observed repository",
        xlabel="Month relative to acceptance",
        ylabel="Mean issues per repository",
    )
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _validate_columns(dataframe: pd.DataFrame) -> None:
    missing = sorted(REQUIRED_COLUMNS - set(dataframe.columns))
    if missing:
        raise SystemExit(f"The issue-level CSV is missing: {', '.join(missing)}")


def _boolean_column(values: pd.Series) -> pd.Series:
    return values.astype(str).str.casefold().eq("true")


if __name__ == "__main__":
    raise SystemExit(main())
