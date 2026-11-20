"""Build before/after commit-activity figures from the commit-level CSV."""

import argparse
import math
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter

from reflections.analysis.plotting import (
    apply_plot_style,
    plot_change_distribution,
    plot_monthly_distribution,
    plot_paged_dumbbells,
    plot_period_distribution,
)

REQUIRED_COLUMNS = {
    "repository",
    "committed_at",
    "period",
    "days_from_acceptance",
    "within_window",
    "analysis_window_days",
    "author_identity",
    "is_merge",
    "author_is_bot",
    "committer_is_bot",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/derived/commits.csv"),
        help="commit-level CSV (default: data/derived/commits.csv)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("figures/commits"),
        help="output directory (default: figures/commits)",
    )
    parser.add_argument(
        "--cohort-output",
        type=Path,
        default=Path("figures/cohort"),
        help="shared cohort figure directory (default: figures/cohort)",
    )
    parser.add_argument(
        "--exclude-merges",
        action="store_true",
        help="exclude commits with multiple parents",
    )
    parser.add_argument(
        "--exclude-bots",
        action="store_true",
        help="exclude commits authored or committed by a bot account",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    apply_plot_style()
    commits = pd.read_csv(args.input)
    _validate_columns(commits)
    for column in (
        "within_window",
        "is_merge",
        "author_is_bot",
        "committer_is_bot",
    ):
        commits[column] = _boolean_column(commits[column])
    commits["is_bot_commit"] = commits["author_is_bot"] | commits["committer_is_bot"]

    commits = commits.loc[commits["within_window"]].copy()
    if args.exclude_merges:
        commits = commits.loc[~commits["is_merge"]]
    if args.exclude_bots:
        commits = commits.loc[~commits["is_bot_commit"]]
    if commits.empty:
        raise SystemExit("No commits remain after applying the requested filters")

    args.output.mkdir(parents=True, exist_ok=True)
    args.cohort_output.mkdir(parents=True, exist_ok=True)
    summary = _commit_summary(commits)
    summary.to_csv(args.output / "commit_summary.csv", index=False)
    plot_period_distribution(
        summary,
        value="commits",
        path=args.cohort_output / "commits_coverage.png",
        title="Distribution of default-branch commits in matched windows",
        ylabel="Commits per repository",
        fill_missing=True,
    )
    plot_change_distribution(
        summary,
        value="commits",
        path=args.cohort_output / "commits_change.png",
        title="Change in default-branch commits after acceptance",
        xlabel="Change in commits (after − before)",
        fill_missing=True,
    )
    plot_monthly_distribution(
        commits,
        path=args.cohort_output / "commits_monthly_activity.png",
        title="Monthly default-branch commit activity",
        ylabel="Commits per repository",
    )
    plot_paged_dumbbells(
        summary,
        value="commits",
        output_dir=args.output / "appendix",
        stem="commit_counts",
        title="Default-branch commits before and after acceptance",
        xlabel="Commits in matched window",
        fill_missing=True,
    )
    print(
        f"Wrote commit_summary.csv, 3 cohort figures, and appendix pages to {args.output}"
    )
    return 0


def _commit_summary(commits: pd.DataFrame) -> pd.DataFrame:
    return (
        commits.groupby(["repository", "period"], sort=True)
        .agg(
            commits=("repository", "size"),
            unique_authors=("author_identity", "nunique"),
            merge_commits=("is_merge", "sum"),
            bot_commits=("is_bot_commit", "sum"),
        )
        .reset_index()
    )


def _plot_coverage(commits: pd.DataFrame, path: Path) -> None:
    counts = (
        commits.groupby(["repository", "period"])
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
        title="Default-branch commit coverage in matched windows",
        xlabel="Commits before acceptance  ←   →  Commits after acceptance",
        ylabel="Repository",
    )
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_count_dumbbell(summary: pd.DataFrame, path: Path) -> None:
    counts = summary.pivot(
        index="repository",
        columns="period",
        values="commits",
    ).dropna(subset=["before_acceptance", "after_acceptance"], how="any")
    counts = counts.sort_values("before_acceptance")
    height = min(30, max(5, 0.35 * len(counts)))
    fig, ax = plt.subplots(figsize=(10, height))
    if counts.empty:
        ax.text(
            0.5,
            0.5,
            "No repository has commits in both periods",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.set_axis_off()
    else:
        positions = range(len(counts))
        for position, (_, values) in enumerate(counts.iterrows()):
            ax.plot(
                [values["before_acceptance"], values["after_acceptance"]],
                [position, position],
                color="0.75",
                zorder=1,
            )
        ax.scatter(
            counts["before_acceptance"],
            positions,
            label="before acceptance",
            zorder=2,
        )
        ax.scatter(
            counts["after_acceptance"],
            positions,
            label="after acceptance",
            zorder=2,
        )
        ax.set_yticks(list(positions), labels=counts.index, fontsize=8)
        ax.set(
            title="Default-branch commits before and after acceptance",
            xlabel="Commits in matched window",
            ylabel="Repository",
        )
        ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_monthly_activity(commits: pd.DataFrame, path: Path) -> None:
    activity = commits.copy()
    activity["relative_month"] = activity["days_from_acceptance"].map(
        lambda value: math.floor(value / 30.4375)
    )
    repositories = sorted(activity["repository"].unique())
    window_days = int(activity["analysis_window_days"].min())
    month_limit = math.ceil(window_days / 30.4375)
    months = range(-month_limit, month_limit + 1)
    complete_index = pd.MultiIndex.from_product(
        [repositories, months],
        names=["repository", "relative_month"],
    )
    counts = (
        activity.groupby(["repository", "relative_month"])
        .size()
        .reindex(complete_index, fill_value=0)
        .groupby("relative_month")
        .mean()
    )
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(counts.index, counts.values, marker="o", markersize=3)
    ax.axvline(0, color="black", linestyle="--", label="acceptance")
    ax.set(
        title="Mean monthly default-branch commits per repository",
        xlabel="Month relative to acceptance",
        ylabel="Mean commits per repository",
    )
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _validate_columns(dataframe: pd.DataFrame) -> None:
    missing = sorted(REQUIRED_COLUMNS - set(dataframe.columns))
    if missing:
        raise SystemExit(
            f"The commit-level CSV is missing columns: {', '.join(missing)}"
        )


def _boolean_column(values: pd.Series) -> pd.Series:
    return values.astype(str).str.casefold().eq("true")


if __name__ == "__main__":
    raise SystemExit(main())
