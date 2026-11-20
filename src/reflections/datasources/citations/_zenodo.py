"""Get downloads and views from a zenodo DOI"""

import functools
import re

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ._doi_utils import bare_doi

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


@functools.cache
def _get_record(doi: str) -> dict:
    """Return the Zenodo record JSON for a Zenodo DOI (concept or single)"""
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
    return rec


def get_zenodo_stats(doi: str) -> dict:
    """Return Zenodo usage stats for a Zenodo DOI (concept or single)."""
    doi = bare_doi(doi)
    rec = _get_record(doi)
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


def get_zenodo_versions(doi: str) -> list[dict]:
    """Return per-version Zenodo usage stats for every version of a record

    Zenodo's public API has no usage-over-time data, only totals for each
    version. Each entry has the version's doi, version label, created date
    (YYYY-MM-DD, when it was uploaded) and its own views/downloads, oldest
    first.
    """
    rec = _get_record(doi)
    concept_id = rec.get("conceptrecid") or rec["id"]
    hits, page = [], 1
    while True:
        # 25 is the largest page size Zenodo allows without a token
        r = _session.get(ZENODO_API, params={
            "q": f"parent.id:{concept_id}", "allversions": "true",
            "sort": "oldest", "size": 25, "page": page,
        }, timeout=30)
        r.raise_for_status()
        result = r.json()["hits"]
        hits.extend(result["hits"])
        if not result["hits"] or len(hits) >= result["total"]:
            break
        page += 1
    if not hits:  # a record without versions isn't always indexed by parent
        hits = [rec]
    return [{
        "doi": h["doi"],
        "version": h["metadata"].get("version"),
        "created": h["created"][:10],
        "views": h["stats"]["version_views"],
        "unique_views": h["stats"]["version_unique_views"],
        "downloads": h["stats"]["version_downloads"],
        "unique_downloads": h["stats"]["version_unique_downloads"],
    } for h in hits]
