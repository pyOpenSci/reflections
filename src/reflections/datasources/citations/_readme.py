"""Find DOIs in the citation sections of package READMEs, for manual review

Only sections under a heading like "Citation", "How to cite" or "Citing X" are
scanned, since the rest of a README often cites background papers or papers
that use the package. Even so, some of what's found isn't about the package
itself, so these DOIs are never added to the citation counts automatically.
"""

import csv
import re
from urllib.parse import unquote

from ._doi import bare_doi
from ._doi_scraper import (
    _JOSS_RE,
    _ZENODO_DOI_RE,
    _same_zenodo_record,
    get_package_dois,
    load_packages,
)
from ._github import fetch_raw_file

README_FILENAMES = ["README.md", "README.rst", "readme.md", "README"]

_CITATION_HEADING_RE = re.compile(r"\bcit(e|es|ed|ing|ation|ations)\b", re.I)

# Headings
_MD_ATX_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
_MD_SETEXT_RE = re.compile(r"^\s{0,3}(={2,}|-{2,})\s*$")
_MD_FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
_HTML_HEADING_RE = re.compile(r"^\s*<h([1-6])[^>]*>(.*?)</h\1>", re.I)
_RST_ADORNMENT_RE = re.compile(r"^([=\-~^*+#\"'`:.])\1{2,}\s*$")

# IDs. Parentheses are allowed in DOIs (some have them) and unbalanced
# closing ones are trimmed afterwards, e.g. from Markdown links.
_DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"'<>\[\]{},;`|]+", re.I)
_ARXIV_RE = re.compile(
    r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})|arxiv:\s?(\d{4}\.\d{4,5})", re.I
)
_SHIELDS_BADGE_BEFORE_RE = re.compile(r"shields\.io/badge/[^\s/]*-$")
_ARXIV_DOI_VERSION_RE = re.compile(r"^(10\.48550/arxiv\.\d{4}\.\d{4,5})v\d+$")

REVIEW_COLUMNS = ["package_name", "doi", "kind", "note", "heading", "context"]


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
    ids = [_clean_doi(m.group(0), line[:m.start()]) for m in _DOI_RE.finditer(line)]
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
