# citations

Download citation counts and Zenodo impact stats for pyOpenSci packages.

## Example usage

```python
import reflections

impact_list = reflections.datasources.citations.get_all_citations()
```

Returns a list of dicts, one per package, with these keys:
- `package_name`
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
    `other_dois`, counting each OpenAlex work once.

Citations and FWCI are None if OpenAlex hasn't indexed the DOI. FWCI can also
be None for an indexed work.

## README citation candidates

DOIs from README sections with "cite"/"citation" headings, for manual review.
They aren't added to the counts above.

```python
from reflections.datasources.citations import save_readme_citations

rows = save_readme_citations("readme_citation_candidates.csv")
```

Columns: `package_name`, `doi`, `kind` (zenodo/joss/arxiv/other), `note`,
`heading`, `context`. DOIs the package already has are left out, and `note`
flags Zenodo versions of an existing record (usually safe to skip).
