"""Get citation count for a DOI with OpenAlex"""

import re

from pyalex import Works


def get_openalex_stats(doi: str) -> dict:
    """Download citation stats from OpenAlex for a DOI"""
    https_doi = re.sub(r'^(?:http://)?(?!https://)', 'https://', doi.strip().lower())
    work = Works()[https_doi]
    return {
        "queried_doi": doi,
        "openalex_id": work["id"],
        "title": work["title"],
        "citations": work["cited_by_count"],
        "fwci": work["fwci"],
    }

