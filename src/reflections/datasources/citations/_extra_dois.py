"""Load the hand-curated DOIs in data/extra_dois.yml"""

from importlib.resources import files

import yaml

from ._doi import bare_doi


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
