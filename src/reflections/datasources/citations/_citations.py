"""Get citation, view, and download counts for DOIs associated with pyOS"""

import datetime

import requests

from ._doi_scraper import get_package_dois
from ._openalex import get_citations_before_after, get_openalex_stats
from ._zenodo import get_zenodo_stats, get_zenodo_versions

ZENODO_METRICS = ("views", "downloads", "unique_views", "unique_downloads")


def _openalex_work(kind: str, stats: dict) -> dict:
    """Summarize one OpenAlex lookup for CitationCount.stats["works"]"""
    return {
        "kind": kind,
        "doi": stats["queried_doi"],
        "openalex_id": stats["openalex_id"],
        "publication_year": stats["publication_year"],
        "publication_date": stats["publication_date"],
        "citations_by_year": stats["citations_by_year"],
        "citations_before": stats.get("citations_before"),
        "citations_after": stats.get("citations_after"),
    }


def _sum_or_none(values: list) -> int | None:
    """Sum the values that aren't None, or None if they all are"""
    values = [v for v in values if v is not None]
    return sum(values) if values else None


def _sum_by_year(by_year_dicts: list[dict]) -> dict[int, int]:
    """Merge {year: count} dicts by adding up counts for each year"""
    total = {}
    for by_year in by_year_dicts:
        for year, count in by_year.items():
            total[year] = total.get(year, 0) + count
    return dict(sorted(total.items()))


class CitationCount:

    def __init__(
            self,
            zenodo_doi: str | None = None,
            joss_doi: str | None = None,
            other_dois: list[str] | None = None,
            date_accepted: str | None = None,
            ):
        """date_accepted (YYYY-MM-DD) turns on the before/after-acceptance stats"""
        self.zenodo_doi = zenodo_doi
        self.joss_doi = joss_doi
        self.other_dois = other_dois
        self.date_accepted = date_accepted
        self.stats = {"works": []}

    def _get_openalex_stats(self, doi: str) -> dict:
        """get_openalex_stats(), plus citations before/after acceptance"""
        stats = get_openalex_stats(doi)
        if self.date_accepted and stats["openalex_id"] is not None:
            split = get_citations_before_after(stats["openalex_id"], self.date_accepted)
            stats["citations_before"] = split["before"]
            stats["citations_after"] = split["after"]
        elif self.date_accepted:
            stats["citations_before"] = stats["citations_after"] = None
        return stats

    def _get_zenodo_before_after(self):
        """Split Zenodo views/downloads by whether each version predates acceptance"""
        versions = get_zenodo_versions(self.zenodo_doi)
        self.stats['zenodo_versions'] = versions
        self.stats['zenodo_first_version_date'] = versions[0]['created'] if versions else None
        before = [v for v in versions if v['created'] < self.date_accepted]
        after = [v for v in versions if v['created'] >= self.date_accepted]
        for metric in ZENODO_METRICS:
            self.stats[f'zenodo_{metric}_before'] = sum(v[metric] for v in before)
            self.stats[f'zenodo_{metric}_after'] = sum(v[metric] for v in after)

    def get_stats(self):
        """Download stats from Zenodo and OpenAlex based on provided DOIs"""
        # OpenAlex works already counted, so the same work isn't counted twice
        counted_works = set()

        if self.zenodo_doi:
            zenodo_stats = get_zenodo_stats(self.zenodo_doi)
            self.stats['zenodo_views'] = zenodo_stats['views']
            self.stats['zenodo_downloads'] = zenodo_stats['downloads']
            self.stats['zenodo_unique_views'] = zenodo_stats['unique_views']
            self.stats['zenodo_unique_downloads'] = zenodo_stats['unique_downloads']
            if self.date_accepted:
                self._get_zenodo_before_after()
            zenodo_openalex_stats = self._get_openalex_stats(self.zenodo_doi)
            self.stats['zenodo_citations'] = zenodo_openalex_stats['citations']
            self.stats['zenodo_citations_by_year'] = zenodo_openalex_stats['citations_by_year']
            self.stats['zenodo_fwci'] = zenodo_openalex_stats['fwci']
            if self.date_accepted:
                self.stats['zenodo_citations_before'] = zenodo_openalex_stats['citations_before']
                self.stats['zenodo_citations_after'] = zenodo_openalex_stats['citations_after']
            self.stats['works'].append(_openalex_work('zenodo', zenodo_openalex_stats))
            counted_works.add(zenodo_openalex_stats['openalex_id'])

        if self.joss_doi:
            joss_stats = self._get_openalex_stats(self.joss_doi)
            self.stats['joss_citations'] = joss_stats['citations']
            self.stats['joss_citations_by_year'] = joss_stats['citations_by_year']
            self.stats['joss_fwci'] = joss_stats['fwci']
            if self.date_accepted:
                self.stats['joss_citations_before'] = joss_stats['citations_before']
                self.stats['joss_citations_after'] = joss_stats['citations_after']
            self.stats['works'].append(_openalex_work('joss', joss_stats))
            counted_works.add(joss_stats['openalex_id'])

        if self.other_dois:
            # OpenAlex merges different DOIs for the same work (e.g. an arXiv
            # preprint and its journal version), so skip works already counted.
            # Unindexed DOIs have no OpenAlex ID and are never skipped.
            other_stats = []
            for doi in self.other_dois:
                doi_stats = self._get_openalex_stats(doi)
                work = doi_stats['openalex_id']
                if work is None or work not in counted_works:
                    other_stats.append(doi_stats)
                    self.stats['works'].append(_openalex_work('other', doi_stats))
                    counted_works.add(work)
            citations = [s['citations'] for s in other_stats if s['citations'] is not None]
            fwcis = [s['fwci'] for s in other_stats if s['fwci'] is not None]
            self.stats['other_citations'] = sum(citations) if citations else None
            self.stats['other_citations_by_year'] = (
                _sum_by_year([s['citations_by_year'] for s in other_stats])
                if citations else None
            )
            self.stats['other_fwci'] = sum(fwcis) / len(fwcis) if fwcis else None
            if self.date_accepted:
                self.stats['other_citations_before'] = _sum_or_none(
                    [s['citations_before'] for s in other_stats])
                self.stats['other_citations_after'] = _sum_or_none(
                    [s['citations_after'] for s in other_stats])


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
            other_dois=pkg.get("other_dois"),
            date_accepted=pkg.get("date_accepted"),
        )
        error = None
        try:
            citation_count.get_stats()
        except (requests.RequestException, LookupError) as e:
            error = f"{type(e).__name__}: {e}"
        citation_counts.append({
            "package_name": pkg["package_name"],
            "date_accepted": pkg.get("date_accepted"),
            "version_accepted": pkg.get("version_accepted"),
            "retrieved_on": datetime.date.today().isoformat(),
            "zenodo_doi": pkg.get("zenodo_doi"),
            "joss_doi": pkg.get("joss_doi"),
            "other_dois": pkg.get("other_dois"),
            "stats": citation_count.stats,
            "error": error,
        })
    return citation_counts
