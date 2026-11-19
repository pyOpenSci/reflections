"""Load pyOpenSci package metadata to find DOIs for citation lookups"""

import re

import requests
import yaml

PACKAGES_URL = (
    "https://raw.githubusercontent.com/pyOpenSci/"
    "pyopensci.github.io/main/data/packages.yml"
)

# Matches zenodo.org/doi/10.5281/zenodo.N, zenodo.org/record/N, zenodo.org/records/N.
# A Zenodo record ID is the same number as its DOI suffix.
_ZENODO_RE = re.compile(r"zenodo\.org/(?:doi/10\.5281/zenodo\.|records?/)(\d+)")
_JOSS_RE = re.compile(r"10\.21105/joss\.\d+")


def load_packages(url: str = PACKAGES_URL) -> list[dict]:
    """Download and parse the pyOpenSci packages.yml into a list of dicts"""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return yaml.safe_load(resp.text)


def _zenodo_doi(archive: str | None) -> str | None:
    """Pull a Zenodo DOI out of an archive URL, or None if there isn't one"""
    m = _ZENODO_RE.search(archive or "")
    return f"10.5281/zenodo.{m.group(1)}" if m else None


def _joss_doi(joss: str | None) -> str | None:
    """Pull a JOSS DOI out of a JOSS paper URL, or None if there isn't one"""
    m = _JOSS_RE.search(joss or "")
    return m.group(0) if m else None


def get_package_dois(packages: list[dict] | None = None) -> list[dict]:
    """Return package name, Zenodo DOI and JOSS DOI for each pyOpenSci package

    Values that are missing, or that aren't a recognizable Zenodo or JOSS
    link, come back as None.
    """
    if packages is None:
        packages = load_packages()
    return [
        {
            "package_name": pkg["package_name"],
            "zenodo_doi": _zenodo_doi(pkg.get("archive")),
            "joss_doi": _joss_doi(pkg.get("joss")),
        }
        for pkg in packages
    ]
