"""Get citation, view, and download counts for DOIs associated with pyOS"""

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
            self.stats['other_citations'] = 0
            self.stats['other_fwci'] = 0
            for doi in self.other_dois:
                doi_stats = get_openalex_stats(doi)
                self.stats['other_citations'] += doi_stats['citations']
                self.stats['other_fwci'] += doi_stats['fwci']
