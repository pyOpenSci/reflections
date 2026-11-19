"""Collect each pyOpenSci package's DOIs for citation lookups

DOIs come from pyOpenSci's packages.yml, the repo's CITATION.cff and the
hand-curated data/extra_dois.yml. README citation sections are collected
separately as candidates for manual review.
"""

import csv
import re
import warnings

import requests
import yaml

from ._doi import bare_doi
from ._extra_dois import load_extra_dois
from ._github import get_cff_dois, get_readme_citation_dois
from ._zenodo import get_zenodo_concept_doi

PACKAGES_URL = (
    "https://raw.githubusercontent.com/pyOpenSci/"
    "pyopensci.github.io/main/data/packages.yml"
)

# Matches zenodo.org/doi/10.5281/zenodo.N, zenodo.org/record/N, zenodo.org/records/N.
# A Zenodo record ID is the same number as its DOI suffix.
_ZENODO_RE = re.compile(r"zenodo\.org/(?:doi/10\.5281/zenodo\.|records?/)(\d+)")
_JOSS_RE = re.compile(r"10\.21105/joss\.\d+")
# zenodo.org/badge/latestdoi/N links use a GitHub repo ID, not a Zenodo record ID.
# They redirect to the DOI of the repo's latest Zenodo release.
_ZENODO_BADGE_RE = re.compile(r"zenodo\.org/badge/latestdoi/\d+")
_ZENODO_DOI_RE = re.compile(r"10\.5281/zenodo\.\d+")

REVIEW_COLUMNS = ["package_name", "doi", "kind", "note", "heading", "context"]


def load_packages(url: str = PACKAGES_URL) -> list[dict]:
    """Download and parse the pyOpenSci packages.yml into a list of dicts"""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return yaml.safe_load(resp.text)


def _zenodo_doi(archive: str | None) -> str | None:
    """Pull a Zenodo DOI out of an archive URL, or None if there isn't one"""
    archive = archive or ""
    m = _ZENODO_RE.search(archive)
    if m:
        return f"10.5281/zenodo.{m.group(1)}"
    if _ZENODO_BADGE_RE.search(archive):
        return _resolve_zenodo_badge(archive)
    return None


def _resolve_zenodo_badge(badge_url: str) -> str | None:
    """Follow a Zenodo badge link's redirect to get the DOI it points to"""
    resp = requests.head(badge_url.strip(), allow_redirects=False, timeout=30)
    resp.raise_for_status()
    doi = bare_doi(resp.headers.get("location", ""))
    return doi if _ZENODO_DOI_RE.fullmatch(doi) else None


def _joss_doi(joss: str | None) -> str | None:
    """Pull a JOSS DOI out of a JOSS paper URL, or None if there isn't one"""
    m = _JOSS_RE.search(joss or "")
    return m.group(0) if m else None


def _same_zenodo_record(doi_a: str, doi_b: str) -> bool:
    """True if two Zenodo DOIs are versions of the same record"""
    if doi_a == doi_b:
        return True
    concept_a = get_zenodo_concept_doi(doi_a)
    return concept_a is not None and concept_a == get_zenodo_concept_doi(doi_b)


def _merge_dois(
    new_dois: list[str],
    zenodo_doi: str | None,
    joss_doi: str | None,
    other_dois: list[str],
) -> tuple[str | None, str | None, list[str]]:
    """Merge new DOIs into a package's Zenodo, JOSS and other DOIs

    A Zenodo or JOSS DOI fills that slot if it's empty. Otherwise it goes in
    the other DOIs, unless it's the same JOSS paper or a version of the same
    Zenodo record already listed. Any other DOI goes in the other DOIs.
    """
    other_dois = list(other_dois)
    for doi in new_dois:
        if _ZENODO_DOI_RE.fullmatch(doi):
            if zenodo_doi is None:
                zenodo_doi = doi
            elif not any(
                _same_zenodo_record(doi, known)
                for known in [zenodo_doi] + other_dois
                if _ZENODO_DOI_RE.fullmatch(known)
            ):
                other_dois.append(doi)
        elif _JOSS_RE.fullmatch(doi):
            if joss_doi is None:
                joss_doi = doi
            elif doi != joss_doi and doi not in other_dois:
                other_dois.append(doi)
        elif doi not in other_dois:
            other_dois.append(doi)
    return zenodo_doi, joss_doi, other_dois


def get_package_dois(packages: list[dict] | None = None) -> list[dict]:
    """Return package name and Zenodo, JOSS and other DOIs for each pyOpenSci package

    Zenodo and JOSS DOIs that are missing, or that aren't a recognizable Zenodo
    or JOSS link, come back as None. If "archive" has no Zenodo DOI, a Zenodo
    link in the "joss" field is used instead, since some entries put it there.

    DOIs from the repo's CITATION.cff, then the hand-curated ones in
    data/extra_dois.yml, are merged in (see _merge_dois): they can fill an
    empty Zenodo or JOSS DOI, and anything new that isn't a version of the
    same Zenodo record goes in "other_dois".
    """
    if packages is None:
        packages = load_packages()
    extra_dois = load_extra_dois()
    unknown = set(extra_dois) - {pkg["package_name"] for pkg in packages}
    if unknown:
        warnings.warn(
            f"extra_dois.yml has packages not in packages.yml: {sorted(unknown)}"
        )
    package_dois = []
    for pkg in packages:
        zenodo_doi = _zenodo_doi(pkg.get("archive")) or _zenodo_doi(pkg.get("joss"))
        joss_doi = _joss_doi(pkg.get("joss"))
        zenodo_doi, joss_doi, other_dois = _merge_dois(
            get_cff_dois(pkg.get("repository_link")), zenodo_doi, joss_doi, []
        )
        zenodo_doi, joss_doi, other_dois = _merge_dois(
            extra_dois.get(pkg["package_name"], []), zenodo_doi, joss_doi, other_dois
        )
        package_dois.append({
            "package_name": pkg["package_name"],
            "zenodo_doi": zenodo_doi,
            "joss_doi": joss_doi,
            "other_dois": other_dois,
        })
    return package_dois


# README citation candidates, for manual review -------------------------


def _kind(doi: str) -> str:
    if _ZENODO_DOI_RE.fullmatch(doi):
        return "zenodo"
    if _JOSS_RE.fullmatch(doi):
        return "joss"
    if doi.startswith("10.48550/arxiv."):
        return "arxiv"
    return "other"


def get_readme_citations() -> list[dict]:
    """Return README citation DOIs not already found for each pyOpenSci package

    Each row has package_name, doi, kind (zenodo/joss/arxiv/other), note,
    heading and context. DOIs already in the package's zenodo_doi, joss_doi
    or other_dois are left out. note flags Zenodo DOIs that are versions of
    the package's existing Zenodo record, and Zenodo/JOSS DOIs for packages
    that have none.
    """
    packages = load_packages()
    rows = []
    for pkg, dois in zip(packages, get_package_dois(packages)):
        known = {dois["zenodo_doi"], dois["joss_doi"], *dois["other_dois"]}
        for found in get_readme_citation_dois(pkg.get("repository_link")):
            doi = found["doi"]
            if doi in known:
                continue
            kind = _kind(doi)
            note = ""
            if kind == "zenodo":
                if dois["zenodo_doi"] is None:
                    note = "fills empty zenodo_doi"
                elif _same_zenodo_record(doi, dois["zenodo_doi"]):
                    note = "same Zenodo record as zenodo_doi"
            elif kind == "joss" and dois["joss_doi"] is None:
                note = "fills empty joss_doi"
            rows.append({"package_name": dois["package_name"], "kind": kind,
                         "note": note, **found})
    return rows


def save_readme_citations(path: str = "readme_citation_candidates.csv") -> list[dict]:
    """Write get_readme_citations() to a CSV for manual review, and return the rows"""
    rows = get_readme_citations()
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REVIEW_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return rows
