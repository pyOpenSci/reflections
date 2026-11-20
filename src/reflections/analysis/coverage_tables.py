"""Build repository-level data coverage and exclusion audits."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

METRICS = {
    "pull_requests": ("github", "pull_requests", "pull_requests.csv"),
    "issues": ("github/issues", "issues", "issues.csv"),
    "commits": ("github/commits", "commits", "commits.csv"),
    "stars": ("github/stars", "weeks", "stars.csv"),
}


def build_coverage_tables(
    cohort_path: Path,
    data_directory: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return metric summaries and repository-level audit details."""

    cohort = pd.read_csv(cohort_path)
    required = {"repository", "accepted_at", "snapshot_fetched_at"}
    missing = required - set(cohort.columns)
    if missing:
        missing_columns = ", ".join(sorted(missing))
        raise ValueError(f"Cohort table is missing columns: {missing_columns}")

    reference_at = pd.to_datetime(cohort["snapshot_fetched_at"], utc=True).max()
    details = []
    for metric, (snapshot_name, event_key, derived_name) in METRICS.items():
        snapshots = _snapshot_records(data_directory / snapshot_name, event_key)
        derived = _derived_counts(data_directory / "derived" / derived_name)
        for row in cohort.itertuples(index=False):
            key = row.repository.casefold()
            snapshot = snapshots.get(key, {})
            eligible = metric != "commits" or (
                reference_at - pd.to_datetime(row.accepted_at, utc=True)
            ).days >= 90
            matched_events = derived.get(key, 0)
            status = snapshot.get("status", "missing")
            included = eligible and status == "complete" and matched_events > 0
            details.append(
                {
                    "repository": row.repository,
                    "metric": metric,
                    "eligible": eligible,
                    "snapshot_status": status,
                    "snapshot_fetched_at": snapshot.get("fetched_at"),
                    "snapshot_window_days": snapshot.get("window_days"),
                    "snapshot_events": snapshot.get("events", 0),
                    "matched_events": matched_events,
                    "analysis_included": included,
                    "exclusion_reason": _exclusion_reason(
                        eligible, status, matched_events
                    ),
                }
            )

    details.extend(_maintainer_rows(cohort, data_directory))
    detail = pd.DataFrame(details).sort_values(["metric", "repository"])
    summary = (
        detail.groupby("metric", sort=False)
        .agg(
            cohort_repositories=("repository", "size"),
            eligible_repositories=("eligible", "sum"),
            complete_snapshots=(
                "snapshot_status",
                lambda values: values.eq("complete").sum(),
            ),
            partial_snapshots=(
                "snapshot_status",
                lambda values: values.eq("partial").sum(),
            ),
            missing_snapshots=(
                "snapshot_status",
                lambda values: values.eq("missing").sum(),
            ),
            analysis_repositories=("analysis_included", "sum"),
        )
        .reset_index()
    )
    return summary, detail


def write_coverage_tables(
    cohort_path: Path,
    data_directory: Path,
    output_directory: Path,
) -> tuple[Path, Path]:
    """Write summary and repository-level coverage CSVs."""

    summary, detail = build_coverage_tables(cohort_path, data_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    summary_path = output_directory / "coverage_summary.csv"
    detail_path = output_directory / "coverage_details.csv"
    summary.to_csv(summary_path, index=False)
    detail.to_csv(detail_path, index=False)
    return summary_path, detail_path


def write_coverage_report(
    summary: pd.DataFrame,
    detail: pd.DataFrame,
    path: Path,
) -> Path:
    """Write a human-readable summary of coverage and exclusions."""

    lines = [
        "# Data coverage audit",
        "",
        "This report is generated from the local cohort, snapshots, and "
        "derived tables.",
        "Regenerate it with `uv run python scripts/build_coverage_audit.py` after "
        "rebuilding the derived datasets.",
        "",
        "| Metric | Cohort | Eligible | Complete | Partial | Missing | Included |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary.itertuples(index=False):
        lines.append(
            f"| {row.metric.replace('_', ' ').title()} | "
            f"{row.cohort_repositories} | {row.eligible_repositories} | "
            f"{row.complete_snapshots} | {row.partial_snapshots} | "
            f"{row.missing_snapshots} | {row.analysis_repositories} |"
        )
    lines.extend(
        [
            "",
            "‘Included’ means that a repository is eligible, has usable local data, "
            "and contributes at least one observation to the current analysis table.",
            "",
            "## Exclusions requiring attention",
            "",
        ]
    )
    attention = detail.loc[
        detail["exclusion_reason"].isin({"missing_snapshot", "partial_snapshot"})
    ]
    if attention.empty:
        lines.append("No missing or partial snapshots were found.")
    else:
        for row in attention.itertuples(index=False):
            lines.append(
                f"- `{row.repository}` — {row.metric.replace('_', ' ')}: "
                f"{row.exclusion_reason.replace('_', ' ')}"
            )
    lines.extend(
        [
            "",
            "## Other exclusions",
            "",
            "Repositories marked `not_eligible` do not satisfy a metric-specific "
            "follow-up or data requirement. Repositories marked "
            "`no_events_in_analysis_window` have a usable snapshot but no events in "
            "the current analysis window. Full details are available in "
            "`data/derived/coverage_details.csv`.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))
    return path


def _snapshot_records(directory: Path, event_key: str) -> dict[str, dict]:
    records: dict[str, dict] = {}
    for path in sorted(directory.glob("*.json")):
        payload = json.loads(path.read_text())
        repository = payload["repository"].casefold()
        partial = path.name.endswith(".partial.json") or not payload.get(
            "complete", True
        )
        status = "partial" if partial else "complete"
        existing = records.get(repository)
        if existing and existing["status"] == "complete" and partial:
            continue
        records[repository] = {
            "status": status,
            "fetched_at": payload.get("fetched_at"),
            "window_days": payload.get("window_days"),
            "events": len(payload.get(event_key, [])),
        }
    return records


def _derived_counts(path: Path) -> dict[str, int]:
    if not path.exists():
        return {}
    data = pd.read_csv(path)
    if data.empty:
        return {}
    within = data["within_window"].astype(str).str.casefold().eq("true")
    return {
        repository.casefold(): int(count)
        for repository, count in data.loc[within].groupby("repository").size().items()
    }


def _maintainer_rows(cohort: pd.DataFrame, data_directory: Path) -> list[dict]:
    rosters = pd.read_csv(data_directory / "derived/maintainer_rosters.csv")
    activity = pd.read_csv(data_directory / "derived/maintainer_activity.csv")
    roster_by_repository = rosters.set_index(rosters["repository"].str.casefold())
    activity["snapshot_available"] = (
        activity["snapshot_available"].astype(str).str.casefold().eq("true")
    )
    grouped = activity.groupby(activity["repository"].str.casefold())
    rows = []
    for row in cohort.itertuples(index=False):
        key = row.repository.casefold()
        roster = (
            roster_by_repository.loc[key]
            if key in roster_by_repository.index
            else None
        )
        group = grouped.get_group(key) if key in grouped.groups else pd.DataFrame()
        eligible = roster is not None and (
            str(roster["has_maintainer_roster"]).casefold() == "true"
        )
        available = int(group["snapshot_available"].sum()) if not group.empty else 0
        requested = len(group)
        status = (
            "missing"
            if requested == 0
            else "complete"
            if available == requested
            else "partial"
        )
        included = eligible and available > 0
        rows.append(
            {
                "repository": row.repository,
                "metric": "maintainers",
                "eligible": eligible,
                "snapshot_status": status,
                "snapshot_fetched_at": None,
                "snapshot_window_days": 365,
                "snapshot_events": available,
                "matched_events": available,
                "analysis_included": included,
                "exclusion_reason": _exclusion_reason(
                    eligible, status, available, allow_partial=True
                ),
            }
        )
    return rows


def _exclusion_reason(
    eligible: bool,
    status: str,
    matched_events: int,
    *,
    allow_partial: bool = False,
) -> str:
    if not eligible:
        return "not_eligible"
    if status == "missing":
        return "missing_snapshot"
    if status == "partial" and (not allow_partial or matched_events == 0):
        return "partial_snapshot"
    if matched_events == 0:
        return "no_events_in_analysis_window"
    return "included"
