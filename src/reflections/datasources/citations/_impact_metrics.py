"""Journal-style impact metrics for pyOpenSci, computed from get_all_citations()"""

import datetime

from ._citations import _sum_by_year


def _indexed_works(pkg: dict, kinds: tuple[str, ...]) -> dict[str, dict]:
    """Return {openalex_id: work} for a package's works of the given kinds

    Leaves out works OpenAlex hasn't indexed or that have no publication year.
    """
    works = {}
    for work in pkg["stats"].get("works", []):
        if (work["kind"] in kinds and work["openalex_id"] is not None
                and work["publication_year"] is not None):
            works.setdefault(work["openalex_id"], work)
    return works


def impact_factors(
        citations: list[dict],
        kinds: tuple[str, ...] = ("joss", "zenodo", "other"),
        window: int = 2,
        by_package: bool = False,
        ) -> dict[int, dict]:
    """Return a journal-impact-factor-style score for pyOpenSci for each year

    Treats pyOpenSci like a journal. For year Y:

        IF(Y) = citations in Y to items published in Y-window .. Y-1
                / number of items published in Y-window .. Y-1

    Note:
        By default an "item" is an OpenAlex work in get_all_citations() output.
        With by_package=True an item is a package instead: its citations are
        the total across all its works, and its publication year is the year
        pyOpenSci accepted it (date_accepted), or the year of its earliest
        work if that's missing.

        Works OpenAlex hasn't indexed, or that have no publication year, are left
        out, as are packages with no such works.

    Args:
        citations: output of get_all_citations()
        kinds: which works count: any of "joss", "zenodo", "other"
        window: how many earlier publication years count (2 for the standard
            impact factor, 5 for the five-year one)
        by_package: count packages rather than works as items

    Returns:
        {year: {"impact_factor": float, "citations": int, "items": int}}, for
        every year with at least one item, up to the current year.
    """
    # Each item is (publication_year, {year: citations})
    if by_package:
        items = []
        for pkg in citations:
            works = _indexed_works(pkg, kinds).values()
            if works:
                accepted = pkg.get("date_accepted")
                items.append((
                    int(str(accepted)[:4]) if accepted
                    else min(w["publication_year"] for w in works),
                    _sum_by_year([w["citations_by_year"] for w in works]),
                ))
    else:
        works = {}
        for pkg in citations:
            for work_id, work in _indexed_works(pkg, kinds).items():
                works.setdefault(work_id, work)
        items = [(w["publication_year"], w["citations_by_year"]) for w in works.values()]
    if not items:
        return {}

    first_year = min(pub_year for pub_year, _ in items) + 1
    this_year = datetime.date.today().year
    result = {}
    for year in range(first_year, this_year + 1):
        in_window = [by_year for pub_year, by_year in items
                     if year - window <= pub_year < year]
        if not in_window:
            continue
        cites = sum(by_year.get(year, 0) for by_year in in_window)
        result[year] = {
            "impact_factor": cites / len(in_window),
            "citations": cites,
            "items": len(in_window),
        }
    return result
