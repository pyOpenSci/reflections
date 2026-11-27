"""DOI helpers: convert between bare and URL forms, and load curated DOIs"""

import re
from importlib.resources import files

import yaml

_PREFIX_RE = re.compile(r"^(?:doi:\s*|(?:https?://)?(?:dx\.)?doi\.org/)", re.IGNORECASE)


def bare_doi(doi: str) -> str:
    """Return a DOI as a lowercase bare identifier, e.g. 10.5281/zenodo.123"""
    return _PREFIX_RE.sub("", doi.strip()).lower()


def doi_url(doi: str) -> str:
    """Return a DOI as a resolver URL, e.g. https://doi.org/10.5281/zenodo.123"""
    return f"https://doi.org/{bare_doi(doi)}"


def load_extra_dois() -> dict[str, list[str]]:
    """Return {package_name: [bare DOIs]} from data/extra_dois.yml

    Includes each package's zenodo_doi and joss_doi, then its other_dois,
    leaving out entries marked "use: false".
    """
    text = (files(__package__) / "data" / "extra_dois.yml").read_text()
    extra = {}
    for package_name, entry in (yaml.safe_load(text) or {}).items():
        dois = [entry[k] for k in ("zenodo_doi", "joss_doi") if entry.get(k)]
        dois += [
            other["doi"] for other in entry.get("other_dois") or []
            if other.get("use", True)
        ]
        extra[package_name] = [bare_doi(str(doi)) for doi in dois]
    return extra
