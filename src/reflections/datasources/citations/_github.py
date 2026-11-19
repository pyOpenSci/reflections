"""Download files from a GitHub repository's default branch"""

import re

import requests

_GITHUB_REPO_RE = re.compile(r"github\.com/([^/\s]+/[^/\s#?]+)")


def fetch_raw_file(
    repository_link: str | None, filenames: list[str]
) -> tuple[str, str] | None:
    """Return (filename, text) for the first of filenames that exists in the repo

    Returns None if the repo isn't on GitHub or none of the files exist.
    Uses raw.githubusercontent.com, which doesn't need a token and doesn't
    count against the GitHub API rate limit.
    """
    m = _GITHUB_REPO_RE.search(repository_link or "")
    if not m:
        return None
    repo = m.group(1).removesuffix(".git")
    for name in filenames:
        resp = requests.get(
            f"https://raw.githubusercontent.com/{repo}/HEAD/{name}", timeout=30
        )
        if resp.status_code == 404:
            continue
        resp.raise_for_status()
        return name, resp.text
    return None
