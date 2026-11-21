"""Summarize full-history index collection state."""

import json
from pathlib import Path

import pandas as pd

from reflections.datasources.github import load_history_index
from reflections.workflows.github_collection import repository_cache_key


def history_index_manifest(
    repositories: list[str],
    directory: Path,
) -> pd.DataFrame:
    """Return one collection-state row per repository and entity type."""

    rows = []
    for repository in repositories:
        key = repository_cache_key(repository)
        for entity in ("issues", "pull_requests"):
            final_path = directory / entity / f"{key}.json"
            partial_path = final_path.with_suffix(".partial.json")
            error_path = directory / "errors" / entity / f"{key}.json"
            path = final_path if final_path.exists() else partial_path
            error = (
                json.loads(error_path.read_text(encoding="utf-8"))["message"]
                if error_path.exists()
                else None
            )
            if path.exists():
                snapshot = load_history_index(path)
                status = "complete" if snapshot.complete else "partial"
                rows.append(
                    {
                        "repository": repository,
                        "entity_type": entity,
                        "status": status,
                        "records": len(snapshot.records),
                        "source_endpoint": snapshot.source_endpoint,
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
                        "entity_type": entity,
                        "status": "failed" if error else "missing",
                        "records": 0,
                        "source_endpoint": None,
                        "next_page": 1,
                        "requests_used": 0,
                        "rate_remaining": None,
                        "error": error,
                        "path": str(final_path),
                    }
                )
    return pd.DataFrame(rows)


def write_history_index_manifest(
    repositories: list[str],
    directory: Path,
    path: Path,
) -> Path:
    """Write the deterministic collection-state manifest."""

    manifest = history_index_manifest(repositories, directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(path, index=False)
    return path
