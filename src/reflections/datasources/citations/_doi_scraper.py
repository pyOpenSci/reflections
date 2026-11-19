"""Load pyOpenSci package metadata to find DOIs for citation lookups"""

import requests
import yaml

PACKAGES_URL = (
    "https://raw.githubusercontent.com/pyOpenSci/"
    "pyopensci.github.io/main/data/packages.yml"
)


def load_packages(url: str = PACKAGES_URL) -> list[dict]:
    """Download and parse the pyOpenSci packages.yml into a list of dicts"""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return yaml.safe_load(resp.text)
