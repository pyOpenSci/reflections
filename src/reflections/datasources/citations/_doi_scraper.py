"""Load pyOpenSci package metadata to find DOIs for citation lookups"""

import re

import requests
import yaml

from ._doi import bare_doi

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


def get_package_dois(packages: list[dict] | None = None) -> list[dict]:
    """Return package name, Zenodo DOI and JOSS DOI for each pyOpenSci package

    Values that are missing, or that aren't a recognizable Zenodo or JOSS
    link, come back as None. If "archive" has no Zenodo DOI, a Zenodo link
    in the "joss" field is used instead, since some entries put it there.
    """
    if packages is None:
        packages = load_packages()
    return [
        {
            "package_name": pkg["package_name"],
            "zenodo_doi": (
                _zenodo_doi(pkg.get("archive")) or _zenodo_doi(pkg.get("joss"))
            ),
            "joss_doi": _joss_doi(pkg.get("joss")),
        }
        for pkg in packages
    ]
