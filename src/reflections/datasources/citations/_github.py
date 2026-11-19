"""Find DOIs in a GitHub repo's CITATION.cff and README

CITATION.cff DOIs are used in the citation counts. README DOIs are only
collected for manual review: just the sections under a heading like
"Citation", "How to cite" or "Citing X" are scanned, since the rest of a
README often cites background papers or papers that use the package, and
even those sections can include papers that aren't about the package itself.
"""

import re
from urllib.parse import unquote

import requests
import yaml

from ._doi import bare_doi

_GITHUB_REPO_RE = re.compile(r"github\.com/([^/\s]+/[^/\s#?]+)")

# CITATION.cff
_CFF_DOI_RE = re.compile(r"10\.\d{4,9}/\S+")

# README
README_FILENAMES = ["README.md", "README.rst", "readme.md", "README"]

_CITATION_HEADING_RE = re.compile(r"\bcit(e|es|ed|ing|ation|ations)\b",
                                  re.IGNORECASE)

# Headings
_MD_ATX_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
_MD_SETEXT_RE = re.compile(r"^\s{0,3}(={2,}|-{2,})\s*$")
_MD_FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
_HTML_HEADING_RE = re.compile(r"^\s*<h([1-6])[^>]*>(.*?)</h\1>", re.IGNORECASE)
_RST_ADORNMENT_RE = re.compile(r"^([=\-~^*+#\"'`:.])\1{2,}\s*$")

# IDs. Parentheses are allowed in DOIs (some have them) and unbalanced
# closing ones are trimmed afterwards, e.g. from Markdown links.
_README_DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"'<>\[\]{},;`|]+",
                            re.IGNORECASE)
_ARXIV_RE = re.compile(
    r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})|arxiv:\s?(\d{4}\.\d{4,5})",
    re.IGNORECASE
)
_SHIELDS_BADGE_BEFORE_RE = re.compile(r"shields\.io/badge/[^\s/]*-$")
_ARXIV_DOI_VERSION_RE = re.compile(r"^(10\.48550/arxiv\.\d{4}\.\d{4,5})v\d+$")


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


# CITATION.cff ---------------------------------------------------------------


def _load_cff(repository_link: str | None) -> dict | None:
    """Download and parse CITATION.cff from a GitHub repo's default branch

    Returns None if the repo isn't on GitHub, has no CITATION.cff, or the
    file isn't valid YAML.
    """
    fetched = fetch_raw_file(repository_link, ["CITATION.cff"])
    if fetched is None:
        return None
    try:
        cff = yaml.safe_load(fetched[1])
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
        if _CFF_DOI_RE.fullmatch(doi) and doi not in dois:
            dois.append(doi)
    return dois


# README ---------------------------------------------------------------------


def _headings(lines: list[str], is_rst: bool) -> list[tuple[int, int, str]]:
    """Return (start line, level, title) for each heading, lower level = bigger

    Markdown uses # headings and ===/--- underlines, skipping fenced code
    blocks. reStructuredText levels follow the order its underline/overline
    styles first appear. HTML <h1>-<h6> headings count in both.
    """
    headings = []
    rst_styles = []
    fence = None
    i = 0
    while i < len(lines):
        line = lines[i]
        nxt = lines[i + 1] if i + 1 < len(lines) else ""

        if not is_rst:
            m = _MD_FENCE_RE.match(line)
            if m:
                marker = m.group(1)[0]
                if fence is None:
                    fence = marker
                elif fence == marker:
                    fence = None
                i += 1
                continue
            if fence:
                i += 1
                continue

        m = _HTML_HEADING_RE.match(line)
        if m:
            headings.append((i, int(m.group(1)), re.sub(r"<[^>]+>", "", m.group(2))))
            i += 1
            continue

        if not is_rst:
            m = _MD_ATX_RE.match(line)
            if m:
                headings.append((i, len(m.group(1)), m.group(2)))
                i += 1
                continue
            if (
                line.strip()
                and not line.lstrip().startswith(("-", "*", "+", ">", "|"))
                and _MD_SETEXT_RE.match(nxt)
            ):
                level = 1 if nxt.strip()[0] == "=" else 2
                headings.append((i, level, line.strip()))
                i += 2
                continue
        else:
            after = lines[i + 2] if i + 2 < len(lines) else ""
            if (
                _RST_ADORNMENT_RE.match(line)
                and nxt.strip()
                and _RST_ADORNMENT_RE.match(after)
                and after[0] == line[0]
            ):
                style = ("over", line[0])
                title, step = nxt.strip(), 3
            elif (
                line.strip()
                and not line[0].isspace()
                and not _RST_ADORNMENT_RE.match(line)
                and _RST_ADORNMENT_RE.match(nxt)
            ):
                style = ("under", nxt[0])
                title, step = line.strip(), 2
            else:
                i += 1
                continue
            if style not in rst_styles:
                rst_styles.append(style)
            headings.append((i, rst_styles.index(style) + 1, title))
            i += step
            continue
        i += 1
    return headings


def _citation_sections(text: str, is_rst: bool) -> list[tuple[str, list[str]]]:
    """Return (heading, body lines) for each section under a citation heading

    A section runs until the next heading at the same or a higher level, so
    subsections are included.
    """
    lines = text.splitlines()
    headings = _headings(lines, is_rst)
    sections = []
    for j, (start, level, title) in enumerate(headings):
        if not _CITATION_HEADING_RE.search(title):
            continue
        end = next(
            (s for s, lvl, _ in headings[j + 1:] if lvl <= level), len(lines)
        )
        sections.append((title.strip(), lines[start + 1:end]))
    return sections


def _clean_doi(doi: str, before: str) -> str:
    """Strip link and badge leftovers from a DOI matched in README text

    before is the text on the line just before the match, used to spot
    shields.io badge URLs like .../badge/DOI-10.5281/zenodo.123-blue?style=flat
    """
    if _SHIELDS_BADGE_BEFORE_RE.search(before):
        doi = doi.split("?", 1)[0].removesuffix(".svg")
        if "-" in doi:
            doi = doi.rsplit("-", 1)[0]
    doi = bare_doi(doi)
    # Strip trailing punctuation and unbalanced ")" until neither is left,
    # e.g. "...joss.05627)." from "[article](https://doi.org/...05627)."
    while True:
        trimmed = doi.rstrip(".#*_:")
        if trimmed.endswith(")") and trimmed.count("(") < trimmed.count(")"):
            trimmed = trimmed[:-1]
        if trimmed == doi:
            break
        doi = trimmed
    for suffix in ("/status.svg", "/status", "/pdf"):
        doi = doi.removesuffix(suffix)
    m = _ARXIV_DOI_VERSION_RE.match(doi)
    return m.group(1) if m else doi


def _ids_in_line(line: str) -> list[str]:
    """Return cleaned DOIs, and arXiv IDs as 10.48550/arxiv.N DOIs, in a line"""
    line = unquote(line)
    ids = [_clean_doi(m.group(0), line[:m.start()]) for m in _README_DOI_RE.finditer(line)]
    ids += [f"10.48550/arxiv.{a or b}" for a, b in _ARXIV_RE.findall(line)]
    return ids


def get_readme_citation_dois(repository_link: str | None) -> list[dict]:
    """Return DOIs found under citation headings in a GitHub repo's README

    One dict per unique DOI with "doi", "heading" (the section it was found
    in) and "context" (the line it was on, trimmed). Returns [] if the repo
    isn't on GitHub or has no README.
    """
    fetched = fetch_raw_file(repository_link, README_FILENAMES)
    if fetched is None:
        return []
    filename, text = fetched
    found = {}
    for heading, body in _citation_sections(text, filename.lower().endswith(".rst")):
        for line in body:
            for doi in _ids_in_line(line):
                if doi not in found:
                    found[doi] = {
                        "doi": doi,
                        "heading": heading,
                        "context": line.strip()[:200],
                    }
    return list(found.values())
