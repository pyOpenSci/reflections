"""Build star-history figures from the daily aggregate CSV."""

import argparse
import math
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from reflections.analysis.plotting import (
    NEUTRAL_COLOR,
    apply_plot_style,
    plot_change_distribution,
    plot_monthly_distribution,
    plot_paged_dumbbells,
    save_figure,
)

REQUIRED_COLUMNS = {
    "repository",
    "current_stargazers",
    "new_stars",
    "period",
    "days_from_acceptance",
    "within_window",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/derived/stars.csv"),
        help="daily star CSV (default: data/derived/stars.csv)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("figures/stars"),
        help="figure directory (default: figures/stars)",
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
    stars = pd.read_csv(args.input)
    _validate_columns(stars)
    stars["within_window"] = _boolean_column(stars["within_window"])
    matched = stars.loc[stars["within_window"]].copy()
    if matched.empty:
        raise SystemExit("The CSV has no star history inside the matched window")

    args.output.mkdir(parents=True, exist_ok=True)
    args.cohort_output.mkdir(parents=True, exist_ok=True)
    summary = _star_summary(matched)
    summary.to_csv(args.output / "star_summary.csv", index=False)
    plot_change_distribution(
        summary,
        value="new_stars",
        path=args.cohort_output / "stars_acquisition_change.png",
        title="Change in new stars after acceptance",
        xlabel="Change in acquired stars (after − before)",
    )
    plot_monthly_distribution(
        matched,
        path=args.cohort_output / "stars_monthly_acquisitions.png",
        title="Monthly star acquisitions",
        ylabel="New stars per repository",
        value_column="new_stars",
    )
    _plot_current_stars(stars, args.cohort_output / "stars_current_stargazers.png")
    plot_paged_dumbbells(
        summary,
        value="new_stars",
        output_dir=args.output / "appendix",
        stem="star_acquisitions",
        title="New stars in matched windows around acceptance",
        xlabel="Star acquisitions",
    )
    print(
        f"Wrote star_summary.csv, 3 cohort figures, and appendix pages to {args.output}"
    )
    return 0


def _star_summary(stars: pd.DataFrame) -> pd.DataFrame:
    return (
        stars.groupby(["repository", "period"], sort=True)
        .agg(
            new_stars=("new_stars", "sum"),
            active_star_days=("new_stars", lambda values: values.gt(0).sum()),
            current_stargazers=("current_stargazers", "max"),
        )
        .reset_index()
    )


def _plot_acquisition_dumbbell(summary: pd.DataFrame, path: Path) -> None:
    counts = summary.pivot(
        index="repository",
        columns="period",
        values="new_stars",
    ).fillna(0)
    counts = counts.sort_values("before_acceptance")
    height = min(30, max(5, 0.35 * len(counts)))
    fig, ax = plt.subplots(figsize=(10, height))
    positions = range(len(counts))
    for position, (_, values) in enumerate(counts.iterrows()):
        ax.plot(
            [values.get("before_acceptance", 0), values.get("after_acceptance", 0)],
            [position, position],
            color="0.75",
            zorder=1,
        )
    ax.scatter(
        counts.get("before_acceptance", pd.Series(0, index=counts.index)),
        positions,
        label="before acceptance",
        zorder=2,
    )
    ax.scatter(
        counts.get("after_acceptance", pd.Series(0, index=counts.index)),
        positions,
        label="after acceptance",
        zorder=2,
    )
    ax.set_yticks(list(positions), labels=counts.index, fontsize=8)
    ax.set(
        title="New stars in matched windows around acceptance",
        xlabel="Star acquisitions",
        ylabel="Repository",
    )
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_monthly_acquisitions(stars: pd.DataFrame, path: Path) -> None:
    activity = stars.copy()
    activity["relative_month"] = activity["days_from_acceptance"].map(
        lambda value: math.floor(value / 30.4375)
    )
    monthly = (
        activity.groupby(["repository", "relative_month"])["new_stars"]
        .sum()
        .groupby("relative_month")
        .mean()
    )
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(monthly.index, monthly.values, marker="o", markersize=3)
    ax.axvline(0, color="black", linestyle="--", label="acceptance")
    ax.set(
        title="Mean monthly star acquisitions per repository",
        xlabel="Month relative to acceptance",
        ylabel="Mean new stars",
    )
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_current_stars(stars: pd.DataFrame, path: Path) -> None:
    counts = stars.groupby("repository")["current_stargazers"].max().sort_values()
    fig, (distribution, ranking) = plt.subplots(1, 2, figsize=(11, 5.5))
    positive = counts.loc[counts > 0]
    distribution.hist(positive, bins=18, color=NEUTRAL_COLOR, alpha=0.8)
    distribution.set_xscale("log")
    distribution.set(
        title="Cohort distribution",
        xlabel="Current stars (log scale)",
        ylabel="Repositories",
    )
    top = counts.tail(15)
    ranking.barh(top.index, top.values, color=NEUTRAL_COLOR)
    ranking.set(title="15 most-starred repositories", xlabel="Current stars")
    ranking.tick_params(axis="y", labelsize=8)
    fig.suptitle("Current repository stars at snapshot time")
    fig.tight_layout()
    save_figure(
        fig,
        path,
        "Current repository stars at snapshot time. The left panel shows the cohort distribution on a logarithmic star axis and the right panel shows the 15 most-starred repositories.",
    )


def _validate_columns(dataframe: pd.DataFrame) -> None:
    missing = sorted(REQUIRED_COLUMNS - set(dataframe.columns))
    if missing:
        raise SystemExit(f"The daily star CSV is missing: {', '.join(missing)}")


def _boolean_column(values: pd.Series) -> pd.Series:
    return values.astype(str).str.casefold().eq("true")


if __name__ == "__main__":
    raise SystemExit(main())
