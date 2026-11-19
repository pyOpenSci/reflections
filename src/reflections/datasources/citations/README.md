# citations

Download citation counts and Zenodo impact stats for pyOpenSci packages.

## Example usage

```python
import reflections

impact_list = reflections.datasources.citations.get_all_citations()
```

Returns a list of dicts, one per package, with these keys:
- `package_name`
- `zenodo_doi`, `joss_doi`: bare DOIs (e.g. `10.21105/joss.10581`), or None if
    the package doesn't have one.
- `stats`: dict of stats (see below).
- `error`: None, or an error message if a lookup failed. Any stats collected
    before the failure are kept.

`stats` only includes the keys for DOIs the package has:
- `zenodo_views`, `zenodo_downloads`: views and downloads across *all versions*
    of the Zenodo record.
- `zenodo_citations`, `zenodo_fwci`: from the OpenAlex record for the Zenodo
    DOI.
- `joss_citations`, `joss_fwci`: from the OpenAlex record for the JOSS DOI.

Citations and FWCI are None if OpenAlex hasn't indexed the DOI. FWCI can also
be None for an indexed work.
