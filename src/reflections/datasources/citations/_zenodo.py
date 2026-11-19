"""Get downloads and views from a zenodo DOI"""

import re

import requests

from ._doi import bare_doi

ZENODO_API = "https://zenodo.org/api/records"

def get_zenodo_stats(doi: str) -> dict:
    """Return Zenodo usage stats for a Zenodo DOI (concept or single)."""
    doi = bare_doi(doi)
    m = re.fullmatch(r"10\.5281/zenodo\.(\d+)", doi)

    if m:
        # Record ID is the DOI suffix. concept IDs redirect to the latest version.
        r = requests.get(f"{ZENODO_API}/{m.group(1)}", timeout=30)
        r.raise_for_status()
        rec = r.json()
    else:
        # Non-Zenodo-prefix DOI hosted on Zenodo: fall back to search.
        r = requests.get(ZENODO_API, params={"q": f'doi:"{doi}"'}, timeout=30)
        r.raise_for_status()
        hits = r.json()["hits"]["hits"]
        if not hits:
            raise LookupError(f"No Zenodo record for {doi}")
        rec = hits[0]

    s = rec["stats"]
    return {
        "queried_doi": doi,
        "record_doi": rec["doi"],
        "concept_doi": rec.get("conceptdoi"),
        "title": rec["metadata"]["title"],
        "views": s["views"],
        "unique_views": s["unique_views"],
        "downloads": s["downloads"],
        "unique_downloads": s["unique_downloads"],
    }
