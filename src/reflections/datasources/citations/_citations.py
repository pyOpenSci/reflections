"""Get citation, view, and download counts for DOIs associated with pyOS"""

import datetime
import json
from pathlib import Path

import requests

from ._doi_scraper import fetch_package_dois
from ._openalex import fetch_citations_before_after, fetch_openalex_stats
from ._zenodo import fetch_zenodo_stats, fetch_zenodo_versions

ZENODO_METRICS = ("views", "downloads", "unique_views", "unique_downloads")


def _openalex_work(kind: str, stats: dict) -> dict:
    """Summarize one OpenAlex lookup for a package's stats["works"]"""
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


def _fetch_openalex_stats(doi: str, date_accepted: str | None) -> dict:
    """fetch_openalex_stats(), plus citations before/after acceptance"""
    stats = fetch_openalex_stats(doi)
    if date_accepted and stats["openalex_id"] is not None:
        split = fetch_citations_before_after(stats["openalex_id"], date_accepted)
        stats["citations_before"] = split["before"]
        stats["citations_after"] = split["after"]
    elif date_accepted:
        stats["citations_before"] = stats["citations_after"] = None
    return stats


def _add_zenodo_before_after(stats: dict, zenodo_doi: str, date_accepted: str):
    """Split Zenodo views/downloads by whether each version predates acceptance"""
    versions = fetch_zenodo_versions(zenodo_doi)
    stats['zenodo_versions'] = versions
    stats['zenodo_first_version_date'] = versions[0]['created'] if versions else None
    before = [v for v in versions if v['created'] < date_accepted]
    after = [v for v in versions if v['created'] >= date_accepted]
    for metric in ZENODO_METRICS:
        stats[f'zenodo_{metric}_before'] = sum(v[metric] for v in before)
        stats[f'zenodo_{metric}_after'] = sum(v[metric] for v in after)


def _add_openalex_stats(
        stats: dict,
        kind: str,
        dois: list[str],
        date_accepted: str | None,
        counted_works: set[str],
        ):
    """Add {kind}_citations, _citations_by_year, _fwci (and _before/_after) to stats

    Citations are summed and FWCI averaged across dois. OpenAlex merges
    different DOIs for the same work (e.g. an arXiv preprint and its journal
    version, or a Zenodo DOI and its JOSS paper), so works already in
    counted_works are skipped. Unindexed DOIs have no OpenAlex ID and are
    never skipped.
    """
    counted = []
    for doi in dois:
        doi_stats = _fetch_openalex_stats(doi, date_accepted)
        work = doi_stats['openalex_id']
        if work is not None:
            if work in counted_works:
                continue
            counted_works.add(work)
        counted.append(doi_stats)
        stats['works'].append(_openalex_work(kind, doi_stats))

    citations = [s['citations'] for s in counted if s['citations'] is not None]
    fwcis = [s['fwci'] for s in counted if s['fwci'] is not None]
    stats[f'{kind}_citations'] = sum(citations) if citations else None
    stats[f'{kind}_citations_by_year'] = _sum_by_year(
        [s['citations_by_year'] for s in counted])
    stats[f'{kind}_fwci'] = sum(fwcis) / len(fwcis) if fwcis else None
    if date_accepted:
        for period in ('before', 'after'):
            stats[f'{kind}_citations_{period}'] = _sum_or_none(
                [s[f'citations_{period}'] for s in counted])


def _add_package_stats(
        stats: dict,
        zenodo_doi: str | None = None,
        joss_doi: str | None = None,
        other_dois: list[str] | None = None,
        date_accepted: str | None = None,
        ):
    """Download stats from Zenodo and OpenAlex for one package's DOIs into stats

    Fills stats in place, so if a lookup fails partway the caller still has
    what was collected before it. date_accepted (YYYY-MM-DD) turns on the
    before/after-acceptance stats.
    """
    stats.setdefault('works', [])

    if zenodo_doi:
        zenodo_stats = fetch_zenodo_stats(zenodo_doi)
        for metric in ZENODO_METRICS:
            stats[f'zenodo_{metric}'] = zenodo_stats[metric]
        if date_accepted:
            _add_zenodo_before_after(stats, zenodo_doi, date_accepted)

    # JOSS first: when OpenAlex merges a Zenodo DOI into its JOSS paper, the
    # citations are credited to JOSS
    counted_works = set()
    for kind, dois in (
            ('joss', [joss_doi] if joss_doi else []),
            ('zenodo', [zenodo_doi] if zenodo_doi else []),
            ('other', other_dois or []),
            ):
        if dois:
            _add_openalex_stats(stats, kind, dois, date_accepted, counted_works)


def _save_json(citations: list[dict], path: str | Path):
    """Write citation results to a JSON file (year keys become strings)"""
    Path(path).write_text(json.dumps(citations, indent=1, default=str))


def fetch_all_citations(save_to: str | Path | None = None) -> list[dict]:
    """Download pyOpenSci's package list and get citation stats for every package

    Args:
        save_to: if given, also write the results to this JSON file
    """
    return fetch_citations(fetch_package_dois(), save_to=save_to)


def fetch_citations(
        package_list: list[dict], save_to: str | Path | None = None
        ) -> list[dict]:
    """Get citation stats for each package in a list from fetch_package_dois()

    Useful for refreshing a few packages without re-downloading all of them.
    A package whose lookup fails keeps whatever stats were collected before
    the failure, with the error message under "error".

    Args:
        package_list: dicts with "package_name" and optionally "zenodo_doi",
            "joss_doi", "other_dois", "date_accepted", "version_accepted"
        save_to: if given, also write the results to this JSON file
    """
    citation_counts = []
    for pkg in package_list:
        stats = {"works": []}
        error = None
        try:
            _add_package_stats(
                stats,
                zenodo_doi=pkg.get("zenodo_doi"),
                joss_doi=pkg.get("joss_doi"),
                other_dois=pkg.get("other_dois"),
                date_accepted=pkg.get("date_accepted"),
            )
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
            "stats": stats,
            "error": error,
        })
    if save_to is not None:
        _save_json(citation_counts, save_to)
    return citation_counts
