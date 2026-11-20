"""Get citation count for a DOI with OpenAlex"""

import os

import pyalex
import requests
from pyalex import Works

from ._doi_utils import doi_url

# Optional: an API key raises OpenAlex's rate limits. Not needed for single-work
# lookups, which are free within the anonymous daily limit.
if os.environ.get("OPENALEX_API_KEY"):
    pyalex.config.api_key = os.environ["OPENALEX_API_KEY"]


def get_openalex_stats(doi: str) -> dict:
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
        "citations": work.get("cited_by_count"),
        "citations_by_year": dict(sorted(
            (c["year"], c["cited_by_count"]) for c in work.get("counts_by_year") or []
        )),
        "fwci": work.get("fwci"),
    }
