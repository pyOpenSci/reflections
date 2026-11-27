# citations

Download citation counts and Zenodo impact stats for pyOpenSci packages.

## Example usage

```python
import reflections

impact_list = reflections.datasources.citations.fetch_all_citations()

# Also write the results to a JSON file
impact_list = reflections.datasources.citations.fetch_all_citations(save_to="citations.json")
```

`fetch_citations(package_list, save_to=None)` does the same for a list of
packages from `fetch_package_dois()`, e.g. to refresh a few without
re-downloading all of them. In the JSON file, `{year: count}` keys are strings,
since JSON keys can't be numbers.

Returns a list of dicts, one per package, with these keys:
- `package_name`
- `date_accepted`: when pyOpenSci accepted the package (YYYY-MM-DD), from
    packages.yml.
- `version_accepted`: the version pyOpenSci accepted, as written in
    packages.yml (formats vary, e.g. `0.8.0`, `v0.19.0`, a markdown link).
- `retrieved_on`: the date the stats were downloaded (end of the "after" period).
- `zenodo_doi`, `joss_doi`: bare DOIs (e.g. `10.21105/joss.10581`), or None.
- `other_dois`: any other DOIs.

DOIs come from packages.yml, the repo's CITATION.cff, and the hand-curated
`data/extra_dois.yml`.
- `stats`: dict of stats (see below).
- `error`: None, or an error message if a lookup failed. Any stats collected
    before the failure are kept.

`stats` only includes the keys for DOIs the package has:
- `zenodo_views`, `zenodo_downloads`: views and downloads across *all versions*
    of the Zenodo record.
- `zenodo_citations`, `zenodo_fwci`: from the OpenAlex record for the Zenodo
    DOI.
- `joss_citations`, `joss_fwci`: from the OpenAlex record for the JOSS DOI.
- `other_citations`, `other_fwci`: total citations and mean FWCI across
    `other_dois`.

- `zenodo_citations_by_year`, `joss_citations_by_year`,
    `other_citations_by_year`: `{year: citations}` for the same works, or `{}`
    if none are indexed.

Each OpenAlex work is counted once per package. OpenAlex sometimes merges
several DOIs into one work, e.g. a Zenodo DOI into its JOSS paper. The DOIs are
looked up in the order JOSS, Zenodo, other, and a work goes to the first kind
that finds it. So `zenodo_citations` is None when the Zenodo DOI resolves to the
JOSS paper (e.g. automata, XGI).
- `works`: one entry per OpenAlex work counted for the package, with `kind`
    (zenodo/joss/other), `doi`, `openalex_id`, `publication_year` and
    `citations_by_year`. `impact_factors()` uses these.

Citations and FWCI are None if OpenAlex hasn't indexed the DOI. FWCI can also
be None for an indexed work.

## Before vs after pyOpenSci acceptance

For packages with a `date_accepted`, `stats` also has:
- `zenodo_{views,downloads,unique_views,unique_downloads}_{before,after}`
- `{zenodo,joss,other}_citations_{before,after}`
- `zenodo_versions`: one entry per Zenodo version, oldest first, with `doi`,
    `version`, `created` and that version's own `views`, `downloads`,
    `unique_views`, `unique_downloads`.
- `zenodo_first_version_date`: the start of the "before" period for Zenodo
    stats.
- Each entry in `works` also gets `publication_date`, `citations_before` and
    `citations_after`, so the "before" period for a work's citations starts at
    its `publication_date`.

"Before" means before `date_accepted`, "after" means on or after it, up to
`retrieved_on`. The two periods have different lengths, so compare rates, not
raw counts.

Notes:
- **Citations** are split by the citing work's publication date, using
  OpenAlex's date filters. Publication lags the actual citing, and the two
  counts can add up to a bit less than the total citations.
- JOSS papers are usually published after pyOpenSci acceptance, so
  `joss_citations_before` is nearly always 0.
- **Zenodo** has no usage-over-time data in its public API, only totals per
  version. A version counts as "before" if it was uploaded (`created`) before
  `date_accepted`. Old versions keep getting views and downloads after
  acceptance.

## Impact factor

A journal-impact-factor-style score for pyOpenSci as a whole: citations in
year Y to works published in the previous `window` years (default 2), divided
by the number of those works.

```python
from reflections.datasources.citations import impact_factors

impact_factors(impact_list)                   # all works
impact_factors(impact_list, kinds=("joss",))  # JOSS papers only
impact_factors(impact_list, window=5)         # five-year impact factor
impact_factors(impact_list, by_package=True)  # packages as items
```

With `by_package=True` each package counts as one item instead of each work.
Its publication year is the year pyOpenSci accepted it (`date_accepted`).

Returns `{year: {"impact_factor", "citations", "items"}}`. Notes:

## README citation candidates

DOIs from README sections with "cite"/"citation" headings, for manual review.
They aren't automatically added to the counts above.

```python
from reflections.datasources.citations import save_readme_citations

rows = save_readme_citations("readme_citation_candidates.csv")
```

Columns: `package_name`, `doi`, `kind` (zenodo/joss/arxiv/other), `note`,
`heading`, `context`. DOIs the package already has are left out, and `note`
flags Zenodo versions of an existing record (usually safe to skip).
