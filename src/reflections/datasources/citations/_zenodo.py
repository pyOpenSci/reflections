"""Get downloads and views from a zenodo DOI"""

import functools
import re

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ._doi import bare_doi

ZENODO_API = "https://zenodo.org/api/records"

# Zenodo occasionally returns 502s and rate-limit 429s, so retry those with backoff
_session = requests.Session()
_session.mount("https://", HTTPAdapter(max_retries=Retry(
    total=4, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504]
)))


@functools.cache
def get_zenodo_concept_doi(doi: str) -> str | None:
    """Return the concept DOI (the one covering all versions) for a Zenodo DOI

    Returns None if it isn't a 10.5281/zenodo.N DOI or Zenodo has no record
    for it. A record without versions is its own concept.
    """
    m = re.fullmatch(r"10\.5281/zenodo\.(\d+)", bare_doi(doi))
    if not m:
        return None
    r = _session.get(f"{ZENODO_API}/{m.group(1)}", timeout=30)
    if r.status_code in (404, 410):
        return None
    r.raise_for_status()
    rec = r.json()
    return bare_doi(rec.get("conceptdoi") or rec["doi"])


def get_zenodo_stats(doi: str) -> dict:
    """Return Zenodo usage stats for a Zenodo DOI (concept or single)."""
    doi = bare_doi(doi)
    m = re.fullmatch(r"10\.5281/zenodo\.(\d+)", doi)

    if m:
        # Record ID is the DOI suffix. concept IDs redirect to the latest version.
        r = _session.get(f"{ZENODO_API}/{m.group(1)}", timeout=30)
        r.raise_for_status()
        rec = r.json()
    else:
        # Non-Zenodo-prefix DOI hosted on Zenodo: fall back to search.
        r = _session.get(ZENODO_API, params={"q": f'doi:"{doi}"'}, timeout=30)
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
