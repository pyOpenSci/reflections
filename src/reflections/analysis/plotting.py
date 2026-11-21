"""Shared, accessible plotting helpers for cohort analyses."""

from collections.abc import Iterable
from pathlib import Path

import cmcrameri.cm as cmc
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BEFORE_COLOR = cmc.acton(0.15)
AFTER_COLOR = cmc.acton(0.50)
NEUTRAL_COLOR = cmc.acton(0.38)
ACCENT_COLOR = cmc.acton(0.03)
PLOT_COLORS = (
    BEFORE_COLOR,
    AFTER_COLOR,
    cmc.acton(0.28),
    cmc.acton(0.62),
)


def apply_plot_style() -> None:
    """Apply consistent defaults that remain legible in print and slides."""

    mpl.rcParams.update(
        {
            "figure.figsize": (8.5, 5.25),
            "figure.dpi": 110,
            "font.size": 11,
            "axes.titlesize": 14,
            "axes.labelsize": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": False,
            "axes.prop_cycle": mpl.cycler(color=PLOT_COLORS),
            "legend.frameon": False,
            "savefig.bbox": "tight",
            "svg.fonttype": "none",
        }
    )


def save_figure(fig: mpl.figure.Figure, path: Path, description: str) -> None:
    """Save a figure as PNG and SVG with a plain-text description."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200, facecolor="white")
    fig.savefig(path.with_suffix(".svg"), facecolor="white")
    path.with_suffix(".txt").write_text(description.strip() + "\n")
    plt.close(fig)
    if path.parent.name == "cohort":
        _write_cohort_index(path.parent)


def _write_cohort_index(directory: Path) -> None:
    """Build a browsable index from cohort figure descriptions."""

    sections = [
        "# Cohort figures",
        "",
        "Primary cohort-level figures. Package-level details are in the domain-specific appendix folders.",
        "",
    ]
    for png in sorted(directory.glob("*.png")):
        description_path = png.with_suffix(".txt")
        description = (
            description_path.read_text().strip() if description_path.exists() else ""
        )
        title = png.stem.replace("_", " ").title()
        sections.extend(
            [f"## {title}", "", f"![{description}]({png.name})", "", description, ""]
        )
    (directory / "README.md").write_text("\n".join(sections))


def paired_values(
    summary: pd.DataFrame, value: str, *, fill_missing: bool = False
) -> pd.DataFrame:
    """Return repositories with observed before and after values."""

    values = summary.pivot(index="repository", columns="period", values=value)
    for period in ("before_acceptance", "after_acceptance"):
        if period not in values:
            values[period] = np.nan
    return (
        values.fillna(0)
        if fill_missing
        else values.dropna(subset=["before_acceptance", "after_acceptance"], how="any")
    )


def plot_change_distribution(
    summary: pd.DataFrame,
    *,
    value: str,
    path: Path,
    title: str,
    xlabel: str,
    fill_missing: bool = False,
) -> None:
    """Plot the distribution of within-repository after-minus-before changes."""

    paired = paired_values(summary, value, fill_missing=fill_missing)
    changes = (paired["after_acceptance"] - paired["before_acceptance"]).sort_values()
    fig, ax = plt.subplots()
    if changes.empty:
        ax.text(
            0.5,
            0.5,
            "No repositories have observations in both periods",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.set_axis_off()
        description = f"{title}. No repositories had observations in both periods."
    else:
        y = np.random.default_rng(42).uniform(-0.09, 0.09, len(changes))
        ax.scatter(
            changes,
            y,
            color=NEUTRAL_COLOR,
            alpha=0.72,
            s=34,
            edgecolor="white",
            linewidth=0.4,
        )
        median = float(changes.median())
        ax.axvline(0, color="0.25", linestyle="--", linewidth=1.2)
        ax.axvline(
            median, color=ACCENT_COLOR, linewidth=2.5, label=f"median: {median:,.1f}"
        )
        ax.set_ylim(-0.18, 0.18)
        ax.set_yticks([])
        ax.set(title=title, xlabel=xlabel)
        ax.legend(loc="upper right")
        ax.text(
            0.01,
            0.96,
            f"n = {len(changes)} repositories",
            transform=ax.transAxes,
            va="top",
            color="0.35",
        )
        description = (
            f"{title}. Each point is one repository. Values are after acceptance minus "
            f"before acceptance; zero indicates no change. The median change is {median:,.1f} "
            f"across {len(changes)} repositories."
        )
    fig.tight_layout()
    save_figure(fig, path, description)


def plot_period_distribution(
    summary: pd.DataFrame,
    *,
    value: str,
    path: Path,
    title: str,
    ylabel: str,
    fill_missing: bool = False,
    colors: tuple[object, object] | None = None,
) -> None:
    """Compare repository-level distributions before and after acceptance."""

    paired = paired_values(summary, value, fill_missing=fill_missing)
    fig, ax = plt.subplots()
    series = [paired["before_acceptance"], paired["after_acceptance"]]
    period_colors = list(colors) if colors is not None else [BEFORE_COLOR, AFTER_COLOR]
    labels = ["Before acceptance", "After acceptance"]
    box = ax.boxplot(
        series, tick_labels=labels, widths=0.5, patch_artist=True, showfliers=False
    )
    for median in box["medians"]:
        median.set_color(ACCENT_COLOR)
        median.set_linewidth(1.8)
    for patch, color in zip(box["boxes"], period_colors, strict=True):
        patch.set_facecolor(color)
        patch.set_alpha(0.35)
    for index, (values, color) in enumerate(
        zip(series, period_colors, strict=True), start=1
    ):
        jitter = np.random.default_rng(index).uniform(-0.11, 0.11, len(values))
        ax.scatter(
            jitter + index,
            values,
            color=color,
            alpha=0.55,
            s=25,
            edgecolor="white",
            linewidth=0.3,
        )
    ax.set(title=title, ylabel=ylabel)
    sample_label = (
        f"n = {len(paired)} included repositories"
        if fill_missing
        else f"n = {len(paired)} paired repositories"
    )
    ax.text(
        0.01,
        0.96,
        sample_label,
        transform=ax.transAxes,
        va="top",
        color="0.35",
    )
    fig.tight_layout()
    inclusion = (
        "Repositories without events in a period are represented by zero."
        if fill_missing
        else "Only repositories with observations in both periods are included."
    )
    save_figure(
        fig,
        path,
        f"{title}. Box plots show the median and quartiles; points are individual "
        f"repositories. {len(paired)} repositories are included. {inclusion}",
    )


def monthly_repository_counts(
    data: pd.DataFrame,
    value_column: str | None = None,
    *,
    repositories: Iterable[str] | None = None,
    window_days: int | None = None,
) -> pd.DataFrame:
    """Count events per repository-month, including zero-event months."""

    activity = data.copy()
    activity["relative_month"] = np.floor(
        activity["days_from_acceptance"] / 30.4375
    ).astype(int)
    indices = []
    if repositories is not None:
        if window_days is None or window_days <= 0:
            raise ValueError("window_days must be positive when repositories are given")
        month_limit = max(0, int(np.floor(window_days / 30.4375)))
        indices.extend(
            (repository, month)
            for repository in repositories
            for month in range(-month_limit, month_limit + 1)
        )
    else:
        for repository, group in activity.groupby("repository"):
            requested_window = (
                float(group["analysis_window_days"].iloc[0])
                if "analysis_window_days" in group
                else float(group["snapshot_window_days"].iloc[0])
                if "snapshot_window_days" in group
                else 365.0
            )
            if {"snapshot_fetched_at", "accepted_at"} <= set(group.columns):
                post_days = (
                    pd.to_datetime(group["snapshot_fetched_at"].iloc[0], utc=True)
                    - pd.to_datetime(group["accepted_at"].iloc[0], utc=True)
                ).total_seconds() / 86_400
                observed_window = min(post_days, requested_window)
            else:
                observed_window = min(
                    requested_window,
                    float(group["days_from_acceptance"].abs().max()),
                )
            month_limit = max(0, int(np.floor(observed_window / 30.4375)))
            indices.extend(
                (repository, month)
                for month in range(-month_limit, month_limit + 1)
            )
    index = pd.MultiIndex.from_tuples(indices, names=["repository", "relative_month"])
    grouped = (
        activity.groupby(["repository", "relative_month"])[value_column].sum()
        if value_column
        else activity.groupby(["repository", "relative_month"]).size()
    )
    return grouped.reindex(index, fill_value=0).rename("events").reset_index()


def plot_monthly_distribution(
    data: pd.DataFrame,
    *,
    path: Path,
    title: str,
    ylabel: str,
    value_column: str | None = None,
    repositories: Iterable[str] | None = None,
    window_days: int | None = None,
) -> None:
    """Plot monthly cohort medians and interquartile ranges."""

    counts = monthly_repository_counts(
        data,
        value_column,
        repositories=repositories,
        window_days=window_days,
    )
    monthly = counts.groupby("relative_month")["events"].agg(
        median="median",
        lower=lambda x: x.quantile(0.25),
        upper=lambda x: x.quantile(0.75),
        repositories="size",
    )
    fig, ax = plt.subplots()
    ax.fill_between(
        monthly.index,
        monthly["lower"],
        monthly["upper"],
        color=NEUTRAL_COLOR,
        alpha=0.25,
        label="interquartile range",
    )
    ax.plot(
        monthly.index,
        monthly["median"],
        color=NEUTRAL_COLOR,
        marker="o",
        markersize=3.5,
        label="median",
    )
    ax.axvline(0, color="0.25", linestyle="--", linewidth=1.2, label="acceptance")
    ax.set(title=title, xlabel="Month relative to acceptance", ylabel=ylabel)
    minimum_n = int(monthly["repositories"].min())
    maximum_n = int(monthly["repositories"].max())
    ax.text(
        0.01,
        0.96,
        f"n = {minimum_n}–{maximum_n} repositories by month",
        transform=ax.transAxes,
        va="top",
        color="0.35",
    )
    ax.legend()
    fig.tight_layout()
    save_figure(
        fig,
        path,
        f"{title}. The line is the repository median and the shaded area spans "
        "the 25th to 75th percentiles. The dashed line marks acceptance. "
        f"Monthly sample sizes range from {minimum_n} to {maximum_n} repositories.",
    )


def plot_paged_dumbbells(
    summary: pd.DataFrame,
    *,
    value: str,
    output_dir: Path,
    stem: str,
    title: str,
    xlabel: str,
    page_size: int = 18,
    fill_missing: bool = False,
) -> None:
    """Write readable package-level before/after plots in fixed-size pages."""

    paired = paired_values(summary, value, fill_missing=fill_missing).sort_values(
        "before_acceptance", ascending=False
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    for page, start in enumerate(range(0, len(paired), page_size), start=1):
        values = paired.iloc[start : start + page_size].sort_values("before_acceptance")
        fig, ax = plt.subplots(figsize=(9, max(4.5, 0.38 * len(values))))
        positions = np.arange(len(values))
        for position, (_, row) in enumerate(values.iterrows()):
            ax.plot(
                [row["before_acceptance"], row["after_acceptance"]],
                [position, position],
                color="0.78",
                zorder=1,
            )
        ax.scatter(
            values["before_acceptance"],
            positions,
            color=BEFORE_COLOR,
            marker="o",
            label="before acceptance",
            zorder=2,
        )
        ax.scatter(
            values["after_acceptance"],
            positions,
            color=AFTER_COLOR,
            marker="D",
            label="after acceptance",
            zorder=2,
        )
        ax.set_yticks(positions, labels=values.index, fontsize=9)
        ax.set(title=f"{title} — page {page}", xlabel=xlabel)
        ax.legend()
        fig.tight_layout()
        save_figure(
            fig,
            output_dir / f"{stem}_{page:02d}.png",
            f"{title}, package-level appendix page {page}. Circles show before acceptance and diamonds show after acceptance.",
        )
