"""Find DOIs listed in a GitHub repository's CITATION.cff"""

import re

import requests
import yaml

from ._doi import bare_doi

_GITHUB_REPO_RE = re.compile(r"github\.com/([^/\s]+/[^/\s#?]+)")
_DOI_RE = re.compile(r"10\.\d{4,9}/\S+")


def _load_cff(repository_link: str | None) -> dict | None:
    """Download and parse CITATION.cff from a GitHub repo's default branch

    Returns None if the repo isn't on GitHub, has no CITATION.cff, or the
    file isn't valid YAML.
    """
    m = _GITHUB_REPO_RE.search(repository_link or "")
    if not m:
        return None
    repo = m.group(1).removesuffix(".git")
    # raw.githubusercontent.com doesn't count against the GitHub API rate limit
    resp = requests.get(
        f"https://raw.githubusercontent.com/{repo}/HEAD/CITATION.cff", timeout=30
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    try:
        cff = yaml.safe_load(resp.text)
    except yaml.YAMLError:
        return None
    return cff if isinstance(cff, dict) else None


def _dois_in(entry: dict) -> list:
    """Return the raw DOI values from a CFF entry's "doi" and "identifiers" fields"""
    values = [entry.get("doi")]
    for ident in entry.get("identifiers") or []:
        if isinstance(ident, dict) and ident.get("type") == "doi":
            values.append(ident.get("value"))
    return values


def get_cff_dois(repository_link: str | None) -> list[str]:
    """Return the bare DOIs a repo's CITATION.cff lists for the package itself

    Checks the top-level "doi" and "identifiers" fields and the same fields
    under "preferred-citation". "references" is skipped, since it usually
    lists dependencies or background papers.
    """
    cff = _load_cff(repository_link)
    if cff is None:
        return []
    values = _dois_in(cff)
    if isinstance(cff.get("preferred-citation"), dict):
        values += _dois_in(cff["preferred-citation"])

    dois = []
    for value in values:
        if not isinstance(value, str):
            continue
        doi = bare_doi(value)
        if _DOI_RE.fullmatch(doi) and doi not in dois:
            dois.append(doi)
    return dois
