"""Get citation count for a DOI with OpenAlex"""

import datetime
import os

import pyalex
import requests
from pyalex import Works

from ._doi_utils import doi_url

# Optional: an API key raises OpenAlex's rate limits. Not needed for single-work
# lookups, which are free within the anonymous daily limit.
if os.environ.get("OPENALEX_API_KEY"):
    pyalex.config.api_key = os.environ["OPENALEX_API_KEY"]


def fetch_openalex_stats(doi: str) -> dict:
    """Download citation stats from OpenAlex for a DOI

    If OpenAlex hasn't indexed the DOI, the returned stats are all None
    (citations_by_year is {}).
    """
    try:
        work = Works()[doi_url(doi)]
    except requests.HTTPError as e:
        if e.response is None or e.response.status_code != 404:
            raise
        work = {}
    return {
        "queried_doi": doi,
        "openalex_id": work.get("id"),
        "title": work.get("title"),
        "publication_year": work.get("publication_year"),
        "publication_date": work.get("publication_date"),
        "citations": work.get("cited_by_count"),
        "citations_by_year": dict(sorted(
            (c["year"], c["cited_by_count"]) for c in work.get("counts_by_year") or []
        )),
        "fwci": work.get("fwci"),
    }


def fetch_citations_before_after(openalex_id: str, date: str) -> dict:
    """Count citations to an OpenAlex work published before vs on/after a date

    date is YYYY-MM-DD. Uses the citing work's publication date. The two
    counts can add up to a bit less than cited_by_count, because OpenAlex's
    filtered counts don't fully match its stored total, and citing works
    without a publication date aren't counted.
    """
    day_before = (datetime.date.fromisoformat(date) - datetime.timedelta(days=1)).isoformat()
    return {
        "before": Works().filter(cites=openalex_id, to_publication_date=day_before).count(),
        "after": Works().filter(cites=openalex_id, from_publication_date=date).count(),
    }
