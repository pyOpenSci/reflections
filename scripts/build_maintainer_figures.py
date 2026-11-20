"""Build figures from maintainer activity and roster-coverage CSVs."""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from reflections.analysis.plotting import (
    ACCENT_COLOR,
    NEUTRAL_COLOR,
    apply_plot_style,
    save_figure,
)

ACTIVITY_COLUMNS = {
    "repository",
    "requested_login",
    "snapshot_available",
    "user_exists",
    "has_public_activity",
    "days_since_last_activity",
    "total_observed_public_activity",
    "has_restricted_contributions",
    "package_activity_exact",
    "package_activity_share",
}
ROSTER_COLUMNS = {
    "repository",
    "maintainer_count",
    "has_maintainer_roster",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--activity",
        type=Path,
        default=Path("data/derived/maintainer_activity.csv"),
    )
    parser.add_argument(
        "--rosters",
        type=Path,
        default=Path("data/derived/maintainer_rosters.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("figures/maintainers"),
    )
    parser.add_argument(
        "--cohort-output",
        type=Path,
        default=Path("figures/cohort"),
        help="shared cohort figure directory (default: figures/cohort)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    apply_plot_style()
    activity = pd.read_csv(args.activity)
    rosters = pd.read_csv(args.rosters)
    _validate_columns(activity, ACTIVITY_COLUMNS, "activity")
    _validate_columns(rosters, ROSTER_COLUMNS, "roster")
    for column in (
        "snapshot_available",
        "user_exists",
        "has_public_activity",
        "has_restricted_contributions",
        "package_activity_exact",
    ):
        activity[column] = _boolean_column(activity[column])
    rosters["has_maintainer_roster"] = _boolean_column(rosters["has_maintainer_roster"])

    args.output.mkdir(parents=True, exist_ok=True)
    args.cohort_output.mkdir(parents=True, exist_ok=True)
    summary = _package_summary(activity, rosters)
    summary.to_csv(args.output / "maintainer_summary.csv", index=False)
    _plot_active_share(summary, args.cohort_output / "maintainers_active_share.png")
    _plot_package_focus(activity, args.cohort_output / "maintainers_package_focus.png")
    _plot_recency(activity, args.cohort_output / "maintainers_activity_recency.png")
    print(f"Wrote maintainer_summary.csv and 3 figures to {args.output}")
    return 0


def _package_summary(
    activity: pd.DataFrame,
    rosters: pd.DataFrame,
) -> pd.DataFrame:
    observed = (
        activity.groupby("repository", sort=True)
        .agg(
            activity_rows_collected=("snapshot_available", "sum"),
            existing_accounts=("user_exists", "sum"),
            active_maintainers=("has_public_activity", "sum"),
            maintainers_with_restricted_activity=(
                "has_restricted_contributions",
                "sum",
            ),
            exact_package_shares=("package_activity_exact", "sum"),
            median_package_activity_share=("package_activity_share", "median"),
            median_total_public_activity=(
                "total_observed_public_activity",
                "median",
            ),
            median_days_since_last_activity=(
                "days_since_last_activity",
                "median",
            ),
        )
        .reset_index()
    )
    summary = rosters.merge(observed, on="repository", how="left")
    summary["active_maintainer_share"] = (
        summary["active_maintainers"] / summary["maintainer_count"]
    )
    return summary


def _plot_active_share(summary: pd.DataFrame, path: Path) -> None:
    values = summary.loc[summary["maintainer_count"] > 0].copy()
    fig, ax = plt.subplots()
    bins = [0, 0.25, 0.5, 0.75, 1.0001]
    ax.hist(
        values["active_maintainer_share"].dropna(),
        bins=bins,
        color=NEUTRAL_COLOR,
        alpha=0.8,
        edgecolor="white",
    )
    ax.set(
        title="Package-level share of maintainers with public activity",
        xlabel="Active share in the 365-day observation window",
        ylabel="Repositories",
        xlim=(0, 1),
    )
    ax.text(
        0.01,
        0.96,
        f"n = {len(values)} repositories",
        transform=ax.transAxes,
        va="top",
        color="0.35",
    )
    fig.tight_layout()
    save_figure(
        fig,
        path,
        "Distribution of the package-level share of listed maintainers with observed public GitHub activity during the 365-day window.",
    )


def _plot_package_focus(activity: pd.DataFrame, path: Path) -> None:
    exact = activity.loc[
        activity["package_activity_exact"] & activity["package_activity_share"].notna()
    ].copy()
    fig, ax = plt.subplots()
    if exact.empty:
        ax.text(0.5, 0.5, "No exact package shares", ha="center", va="center")
        ax.set_axis_off()
    else:
        ax.hist(
            exact["package_activity_share"],
            bins=20,
            range=(0, 1),
            color=NEUTRAL_COLOR,
            alpha=0.8,
            edgecolor="white",
        )
        median = exact["package_activity_share"].median()
        ax.axvline(
            median, color=ACCENT_COLOR, linewidth=2.5, label=f"median: {median:.1%}"
        )
        ax.set(
            title="Maintainer activity attributable to the accepted package",
            xlabel="Package share of observed public contributions",
            ylabel="Maintainers",
            xlim=(0, 1),
        )
        ax.legend()
    fig.tight_layout()
    save_figure(
        fig,
        path,
        "Distribution of each maintainer's share of observed public contributions attributable to the accepted package. Only exact shares are included.",
    )


def _plot_recency(activity: pd.DataFrame, path: Path) -> None:
    days = activity["days_since_last_activity"]
    categories = (
        pd.cut(
            days,
            bins=[-1, 29, 89, 179, 364, float("inf")],
            labels=[
                "<30 days",
                "30–89 days",
                "90–179 days",
                "180–364 days",
                "365+ days",
            ],
        )
        .astype("object")
        .fillna("No observed activity")
    )
    order = [
        "<30 days",
        "30–89 days",
        "90–179 days",
        "180–364 days",
        "365+ days",
        "No observed activity",
    ]
    counts = categories.value_counts().reindex(order, fill_value=0)
    fig, ax = plt.subplots()
    ax.barh(counts.index[::-1], counts.values[::-1], color=NEUTRAL_COLOR)
    ax.set(
        title="Recency of listed maintainer public GitHub activity",
        xlabel="Listed maintainers",
        ylabel="Time since last observed contribution",
    )
    fig.tight_layout()
    save_figure(
        fig,
        path,
        "Listed maintainers grouped by the number of days since their last observed public GitHub contribution. Missing activity is shown as a separate category.",
    )


def _validate_columns(dataframe, required, label) -> None:
    missing = sorted(required - set(dataframe.columns))
    if missing:
        raise SystemExit(f"The {label} CSV is missing: {', '.join(missing)}")


def _boolean_column(values: pd.Series) -> pd.Series:
    return values.astype(str).str.casefold().eq("true")


if __name__ == "__main__":
    raise SystemExit(main())
