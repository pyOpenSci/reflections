"""Normalize DOIs between bare (10.xxxx/...) and resolver URL forms"""

import re

_PREFIX_RE = re.compile(r"^(?:doi:\s*|(?:https?://)?(?:dx\.)?doi\.org/)", re.IGNORECASE)


def bare_doi(doi: str) -> str:
    """Return a DOI as a lowercase bare identifier, e.g. 10.5281/zenodo.123"""
    return _PREFIX_RE.sub("", doi.strip()).lower()


def doi_url(doi: str) -> str:
    """Return a DOI as a resolver URL, e.g. https://doi.org/10.5281/zenodo.123"""
    return f"https://doi.org/{bare_doi(doi)}"
