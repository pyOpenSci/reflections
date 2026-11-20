"""Build figures from maintainer activity and roster-coverage CSVs."""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
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
    rosters["has_maintainer_roster"] = _boolean_column(
        rosters["has_maintainer_roster"]
    )

    args.output.mkdir(parents=True, exist_ok=True)
    summary = _package_summary(activity, rosters)
    summary.to_csv(args.output / "maintainer_summary.csv", index=False)
    _plot_active_share(summary, args.output / "active_maintainer_share.png")
    _plot_package_focus(activity, args.output / "maintainer_package_focus.png")
    _plot_recency(activity, args.output / "maintainer_activity_recency.png")
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
    values = values.sort_values("active_maintainer_share")
    height = min(30, max(5, 0.3 * len(values)))
    fig, ax = plt.subplots(figsize=(9, height))
    ax.barh(values["repository"], values["active_maintainer_share"])
    ax.set(
        title="Share of listed maintainers with public GitHub activity",
        xlabel="Active share in the 365-day observation window",
        ylabel="Repository",
        xlim=(0, 1),
    )
    ax.tick_params(axis="y", labelsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_package_focus(activity: pd.DataFrame, path: Path) -> None:
    exact = activity.loc[
        activity["package_activity_exact"]
        & activity["package_activity_share"].notna()
    ].copy()
    repositories = sorted(exact["repository"].unique())
    positions = {repository: index for index, repository in enumerate(repositories)}
    height = min(30, max(5, 0.35 * len(repositories)))
    fig, ax = plt.subplots(figsize=(9, height))
    if exact.empty:
        ax.text(0.5, 0.5, "No exact package shares", ha="center", va="center")
        ax.set_axis_off()
    else:
        ax.scatter(
            exact["package_activity_share"],
            exact["repository"].map(positions),
            alpha=0.75,
        )
        ax.set_yticks(range(len(repositories)), labels=repositories, fontsize=8)
        ax.set(
            title="Share of each maintainer's public activity in the package",
            xlabel="Package share of observed public contributions",
            ylabel="Repository",
            xlim=(0, 1),
        )
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_recency(activity: pd.DataFrame, path: Path) -> None:
    observed = activity.loc[activity["days_since_last_activity"].notna()].copy()
    observed = observed.sort_values("days_since_last_activity", ascending=False)
    height = min(30, max(5, 0.25 * len(observed)))
    fig, ax = plt.subplots(figsize=(9, height))
    labels = (
        observed["repository"] + " — @" + observed["requested_login"]
    )
    positions = range(len(observed))
    ax.scatter(observed["days_since_last_activity"], positions)
    ax.set_yticks(list(positions), labels=labels, fontsize=7)
    ax.set(
        title="Recency of listed maintainer public GitHub activity",
        xlabel="Days since last observed contribution",
        ylabel="Package and maintainer",
    )
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _validate_columns(dataframe, required, label) -> None:
    missing = sorted(required - set(dataframe.columns))
    if missing:
        raise SystemExit(f"The {label} CSV is missing: {', '.join(missing)}")


def _boolean_column(values: pd.Series) -> pd.Series:
    return values.astype(str).str.casefold().eq("true")


if __name__ == "__main__":
    raise SystemExit(main())
