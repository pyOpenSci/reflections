"""Summarize repository-wide interaction collection state."""

import json
from pathlib import Path

import pandas as pd

from reflections.datasources.github import load_interaction_snapshot
from reflections.workflows.github_collection import repository_cache_key

INTERACTION_TYPES = ("issue_comments", "review_comments")


def interaction_manifest(
    repositories: list[str],
    directory: Path,
) -> pd.DataFrame:
    """Return one collection-state row per repository and interaction type."""

    rows = []
    for repository in repositories:
        key = repository_cache_key(repository)
        for interaction_type in INTERACTION_TYPES:
            final_path = directory / interaction_type / f"{key}.json"
            partial_path = final_path.with_suffix(".partial.json")
            error_path = directory / "errors" / interaction_type / f"{key}.json"
            path = final_path if final_path.exists() else partial_path
            error = (
                json.loads(error_path.read_text(encoding="utf-8"))["message"]
                if error_path.exists()
                else None
            )
            if path.exists():
                snapshot = load_interaction_snapshot(path)
                rows.append(
                    {
                        "repository": repository,
                        "interaction_type": interaction_type,
                        "status": "complete" if snapshot.complete else "partial",
                        "records": len(snapshot.records),
                        "next_page": snapshot.next_page,
                        "requests_used": snapshot.requests_used,
                        "rate_remaining": snapshot.rate_remaining,
                        "error": error,
                        "path": str(path),
                    }
                )
            else:
                rows.append(
                    {
                        "repository": repository,
                        "interaction_type": interaction_type,
                        "status": "failed" if error else "missing",
                        "records": 0,
                        "next_page": 1,
                        "requests_used": 0,
                        "rate_remaining": None,
                        "error": error,
                        "path": str(final_path),
                    }
                )
    return pd.DataFrame(rows)


def write_interaction_manifest(
    repositories: list[str],
    directory: Path,
    path: Path,
) -> Path:
    """Write the deterministic interaction collection manifest."""

    manifest = interaction_manifest(repositories, directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(path, index=False)
    return path
