"""Get citation count for a DOI with OpenAlex"""

import requests
from pyalex import Works

from ._doi_utils import doi_url


def get_openalex_stats(doi: str) -> dict:
    """Download citation stats from OpenAlex for a DOI

    If OpenAlex hasn't indexed the DOI, the returned stats are all None.
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
        "citations": work.get("cited_by_count"),
        "fwci": work.get("fwci"),
    }
