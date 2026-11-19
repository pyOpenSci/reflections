"""Get citation, view, and download counts for DOIs associated with pyOS"""

import requests

from ._doi_scraper import get_package_dois
from ._openalex import get_openalex_stats
from ._zenodo import get_zenodo_stats


class CitationCount:

    def __init__(
            self,
            zenodo_doi: str | None = None,
            joss_doi: str | None = None,
            other_dois: list[str] | None = None
            ):
        self.zenodo_doi = zenodo_doi
        self.joss_doi = joss_doi
        self.other_dois = other_dois
        self.stats = {}

    def get_stats(self):
        """Download stats from Zenodo and OpenAlex based on provided DOIs"""
        if self.zenodo_doi:
            zenodo_stats = get_zenodo_stats(self.zenodo_doi)
            self.stats['zenodo_views'] = zenodo_stats['views']
            self.stats['zenodo_downloads'] = zenodo_stats['downloads']
            zenodo_openalex_stats = get_openalex_stats(self.zenodo_doi)
            self.stats['zenodo_citations'] = zenodo_openalex_stats['citations']
            self.stats['zenodo_fwci'] = zenodo_openalex_stats['fwci']

        if self.joss_doi:
            joss_stats = get_openalex_stats(self.joss_doi)
            self.stats['joss_citations'] = joss_stats['citations']
            self.stats['joss_fwci'] = joss_stats['fwci']

        if self.other_dois:
            other_stats = [get_openalex_stats(doi) for doi in self.other_dois]
            citations = [s['citations'] for s in other_stats if s['citations'] is not None]
            fwcis = [s['fwci'] for s in other_stats if s['fwci'] is not None]
            self.stats['other_citations'] = sum(citations) if citations else None
            self.stats['other_fwci'] = sum(fwcis) / len(fwcis) if fwcis else None


def get_all_citations() -> list[dict]:
    """Download pyOpenSci's package list and get citation stats for every package"""
    return _get_citations(get_package_dois())


def _get_citations(package_list: list[dict]) -> list[dict]:
    """Get citation stats for each package in a list from get_package_dois()

    A package whose lookup fails keeps whatever stats were collected before
    the failure, with the error message under "error".
    """
    citation_counts = []
    for pkg in package_list:
        citation_count = CitationCount(
            zenodo_doi=pkg.get("zenodo_doi"),
            joss_doi=pkg.get("joss_doi"),
            other_dois=pkg.get("other_dois")
        )
        error = None
        try:
            citation_count.get_stats()
        except (requests.RequestException, LookupError) as e:
            error = f"{type(e).__name__}: {e}"
        citation_counts.append({
            "package_name": pkg["package_name"],
            "zenodo_doi": pkg.get("zenodo_doi"),
            "joss_doi": pkg.get("joss_doi"),
            "stats": citation_count.stats,
            "error": error,
        })
    return citation_counts
