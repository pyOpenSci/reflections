"""Build star-history figures from the daily aggregate CSV."""

import argparse
import math
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    stars = pd.read_csv(args.input)
    _validate_columns(stars)
    stars["within_window"] = _boolean_column(stars["within_window"])
    matched = stars.loc[stars["within_window"]].copy()
    if matched.empty:
        raise SystemExit("The CSV has no star history inside the matched window")

    args.output.mkdir(parents=True, exist_ok=True)
    summary = _star_summary(matched)
    summary.to_csv(args.output / "star_summary.csv", index=False)
    _plot_acquisition_dumbbell(summary, args.output / "star_acquisition_dumbbell.png")
    _plot_monthly_acquisitions(
        matched,
        args.output / "monthly_star_acquisitions.png",
    )
    _plot_current_stars(stars, args.output / "current_stargazers.png")
    print(f"Wrote star_summary.csv and 3 figures to {args.output}")
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
    counts = (
        stars.groupby("repository")["current_stargazers"]
        .max()
        .sort_values()
    )
    height = min(30, max(5, 0.28 * len(counts)))
    fig, ax = plt.subplots(figsize=(9, height))
    ax.barh(counts.index, counts.values)
    ax.set(
        title="Current repository stars at snapshot time",
        xlabel="Current stars",
        ylabel="Repository",
    )
    ax.tick_params(axis="y", labelsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _validate_columns(dataframe: pd.DataFrame) -> None:
    missing = sorted(REQUIRED_COLUMNS - set(dataframe.columns))
    if missing:
        raise SystemExit(f"The daily star CSV is missing: {', '.join(missing)}")


def _boolean_column(values: pd.Series) -> pd.Series:
    return values.astype(str).str.casefold().eq("true")


if __name__ == "__main__":
    raise SystemExit(main())
