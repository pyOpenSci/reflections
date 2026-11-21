"""Internal cohort figure build command."""

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/derived/cohort.csv"))
    parser.add_argument("--output", type=Path, default=Path("figures/cohort"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cohort = pd.read_csv(args.input)
    required = {"repository", "days_since_last_default_branch_commit"}
    missing = sorted(required - set(cohort.columns))
    if missing:
        raise SystemExit(f"The cohort CSV is missing: {', '.join(missing)}")
    apply_plot_style()
    _plot_commit_recency(cohort, args.output / "cohort_last_commit_recency.png")
    print(f"Wrote cohort profile figure to {args.output}")
    return 0


def _plot_commit_recency(cohort: pd.DataFrame, path: Path) -> None:
    days = cohort["days_since_last_default_branch_commit"]
    observed_months = (days.dropna() / 30.4375).clip(lower=0)
    missing_count = int(days.isna().sum())
    fig, ax = plt.subplots()
    ax.hist(
        observed_months,
        bins="auto",
        color=NEUTRAL_COLOR,
        alpha=0.8,
        edgecolor="white",
    )
    median = float(observed_months.median())
    ax.axvline(
        median,
        color=ACCENT_COLOR,
        linewidth=2.5,
        label=f"median: {median:.1f} months",
    )
    ax.set(
        title="Recency of the latest default-branch commit",
        xlabel="Months since latest commit",
        ylabel="Accepted packages",
    )
    ax.text(
        0.99,
        0.96,
        f"n = {len(observed_months)} repositories"
        + (f"; {missing_count} unavailable" if missing_count else ""),
        transform=ax.transAxes,
        ha="right",
        va="top",
        color="0.35",
    )
    ax.legend()
    fig.tight_layout()
    save_figure(
        fig,
        path,
        "Histogram of the time between the cohort metadata snapshot and the "
        "latest commit on each repository's default branch. The vertical line "
        f"marks the median of {median:.1f} months across {len(observed_months)} "
        f"repositories; {missing_count} repositories had no available timestamp.",
    )


if __name__ == "__main__":
    raise SystemExit(main())
