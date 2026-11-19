"""Get citation count for a DOI with OpenAlex"""

from pyalex import Works

from ._doi import doi_url


def get_openalex_stats(doi: str) -> dict:
    """Download citation stats from OpenAlex for a DOI"""
    work = Works()[doi_url(doi)]
    return {
        "queried_doi": doi,
        "openalex_id": work["id"],
        "title": work["title"],
        "citations": work["cited_by_count"],
        "fwci": work["fwci"],
    }

